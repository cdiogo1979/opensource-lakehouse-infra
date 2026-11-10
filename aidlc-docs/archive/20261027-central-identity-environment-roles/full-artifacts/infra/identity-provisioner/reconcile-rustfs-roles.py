#!/usr/bin/python3
"""Reconcile approved FreeIPA role membership into RustFS IAM groups."""

from __future__ import annotations

import argparse
import fcntl
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import os
import re
import stat
import sys
import tempfile
import time
import uuid
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
from pathlib import PurePosixPath
from urllib.parse import urlsplit

import ldap
import ldap.dn
import ldap.filter


POLICY_FILE = Path(os.environ.get("RUSTFS_ROLE_POLICY_FILE", "/etc/lakehouse/rustfs-role-policy.json"))
RUNTIME_DIR = Path(os.environ.get("IDENTITY_RUNTIME_DIR", "/run/identity-status"))
STATUS_FILE = RUNTIME_DIR / "rustfs-reconciliation-status.json"
LOCK_FILE = RUNTIME_DIR / "rustfs-reconciliation.lock"
SNAPSHOT_DIR = RUNTIME_DIR / "iam-snapshots"
CA_FILE = os.environ.get("FREEIPA_CA_FILE", "/run/freeipa/ca.crt")
LDAP_PASSWORD_FILE = "/run/secrets/freeipa-rustfs-reader-password"
LDAP_URI = os.environ.get("FREEIPA_LDAP_URI", "ldaps://ipa.lakehouse.local:636")
LDAP_REALM = os.environ.get("KERBEROS_REALM", "LAKEHOUSE.LOCAL")
RUSTFS_ENDPOINT = os.environ.get("RUSTFS_ENDPOINT", "http://rustfs-iam-test:9000").rstrip("/")
READ_RETRY_ATTEMPTS = 2
READ_RETRY_DELAY_SECONDS = 0.25
TRANSIENT_READ_STATUSES = {429, 500, 502, 503, 504}
SAFE_TERMINAL_STATES = {"complete", "no-change", "blocked", "already-running", "partial-failure"}
NONTERMINAL_STATES = {"applying", "verifying", "partial-failure"}
SAFE_ERROR_CODES = {
    "AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch", "NoSuchBucket",
    "NoSuchBucketPolicy", "NoSuchCannedPolicy", "NoSuchPolicy", "NoSuchUser",
    "NoSuchGroup", "NoSuchResource", "NoSuchUpload", "InvalidRequest",
    "InternalError", "ServiceUnavailable",
}
READ_ACTIONS = {"s3:GetBucketLocation", "s3:ListBucket", "s3:GetObject"}
WRITE_BUCKET_ACTIONS = {"s3:ListBucketMultipartUploads"}
WRITE_OBJECT_ACTIONS = {
    "s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"
}


class ReconcileError(Exception):
    def __init__(self, category: str, *, changed: bool = False):
        super().__init__(category)
        self.category = category
        self.changed = changed


def load_admin_client():
    candidates = [
        Path("/usr/local/bin/provision-rustfs-identities"),
        Path(__file__).with_name("provision-rustfs-identities.py"),
    ]
    script = next((candidate for candidate in candidates if candidate.is_file()), None)
    if script is None:
        raise ReconcileError("rustfs-client-unavailable")
    module_name = "provision_rustfs_identities"
    loader = SourceFileLoader(module_name, str(script))
    spec = importlib.util.spec_from_loader(module_name, loader)
    if spec is None or spec.loader is None:
        raise ReconcileError("rustfs-client-unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ENDPOINT = RUSTFS_ENDPOINT
    return module


def atomic_json(path: Path, value: dict, mode: int = 0o600) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        os.chmod(path, mode)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_status(record: dict) -> None:
    allowed = {
        "run_id", "policy_version", "started_at", "finished_at", "elapsed_seconds",
        "state", "counts", "verification", "failure_category",
    }
    atomic_json(STATUS_FILE, {key: value for key, value in record.items() if key in allowed})


def read_json(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, json.JSONDecodeError):
        raise ReconcileError("configuration-unreadable")
    if not isinstance(value, dict):
        raise ReconcileError("configuration-invalid")
    return value


def validate_policy(policy: dict) -> None:
    if set(policy) != {
        "schema_version", "policy_version", "buckets", "roles", "preserved_users", "legacy_writer_policy"
    }:
        raise ReconcileError("configuration-unknown-field")
    if policy.get("schema_version") != 1 or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\.[0-9]+", str(policy.get("policy_version", ""))):
        raise ReconcileError("configuration-invalid-version")
    buckets = policy.get("buckets")
    if buckets != ["lake", "lake-dev", "lake-uat"]:
        raise ReconcileError("configuration-invalid-buckets")
    expected = {
        "lakehouse-developers": ("lakehouse-developers", {"developer-user"}, {"lake", "lake-dev", "lake-uat"}, {"lake-dev"}),
        "lakehouse-analysts": ("lakehouse-analysts", {"analyst-user"}, {"lake"}, set()),
        "lakehouse-writers": ("lakehouse-writers", {"write-service-account"}, set(buckets), set(buckets)),
    }
    roles = policy.get("roles")
    if not isinstance(roles, list) or len(roles) != len(expected):
        raise ReconcileError("configuration-invalid-roles")
    seen_groups: set[str] = set()
    seen_users: set[str] = set()
    for role in roles:
        if not isinstance(role, dict) or set(role) != {"group", "policy", "members", "read_buckets", "write_buckets"}:
            raise ReconcileError("configuration-invalid-role")
        name = role.get("group")
        if name not in expected or name in seen_groups:
            raise ReconcileError("configuration-invalid-role")
        wanted_policy, wanted_members, wanted_read, wanted_write = expected[name]
        members = role.get("members")
        read_buckets = role.get("read_buckets")
        write_buckets = role.get("write_buckets")
        if (role.get("policy") != wanted_policy or not isinstance(members, list)
                or set(members) != wanted_members or len(members) != len(wanted_members)
                or set(members) & seen_users or not isinstance(read_buckets, list)
                or set(read_buckets) != wanted_read or not isinstance(write_buckets, list)
                or set(write_buckets) != wanted_write
                or not set(write_buckets) <= set(read_buckets)):
            raise ReconcileError("configuration-role-scope-invalid")
        seen_groups.add(name)
        seen_users.update(members)
    if seen_groups != set(expected) or seen_users != {"developer-user", "analyst-user", "write-service-account"}:
        raise ReconcileError("configuration-role-coverage-invalid")
    if policy.get("preserved_users") != ["admin", "user_a", "user_b"]:
        raise ReconcileError("configuration-preservation-invalid")
    if policy.get("legacy_writer_policy") != "lakehouse-writer":
        raise ReconcileError("configuration-legacy-binding-invalid")


def make_policy(role: dict) -> dict:
    statements = []
    read_buckets = role["read_buckets"]
    write_buckets = role["write_buckets"]
    bucket_read = sorted(read_buckets)
    object_read = sorted(read_buckets)
    if bucket_read:
        statements.append({
            "Effect": "Allow",
            "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
            "Resource": [f"arn:aws:s3:::{name}" for name in bucket_read],
        })
        statements.append({
            "Effect": "Allow",
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{name}/*" for name in object_read],
        })
    if write_buckets:
        statements.append({
            "Effect": "Allow",
            "Action": ["s3:ListBucketMultipartUploads"],
            "Resource": [f"arn:aws:s3:::{name}" for name in sorted(write_buckets)],
        })
        statements.append({
            "Effect": "Allow",
            "Action": sorted(WRITE_OBJECT_ACTIONS),
            "Resource": [f"arn:aws:s3:::{name}/*" for name in sorted(write_buckets)],
        })
    return {"Version": "2012-10-17", "Statement": statements}


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class DirectoryReader:
    def __init__(self, policy: dict):
        domain = LDAP_REALM.lower().split(".")
        self.base_dn = ",".join(f"dc={label}" for label in domain)
        self.group_base = f"cn=groups,cn=accounts,{self.base_dn}"
        self.user_base = f"cn=users,cn=accounts,{self.base_dn}"
        self.roles = policy["roles"]

    def memberships(self) -> dict[str, set[str]]:
        try:
            password = Path(LDAP_PASSWORD_FILE).read_text(encoding="utf-8").strip()
        except OSError:
            raise ReconcileError("directory-credential-unavailable")
        if not password:
            raise ReconcileError("directory-credential-empty")
        bind_dn = f"uid=rustfs-reconciler,{self.user_base}"
        connection = None
        try:
            ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, CA_FILE)
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)
            connection = ldap.initialize(LDAP_URI)
            connection.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            connection.set_option(ldap.OPT_REFERRALS, 0)
            connection.set_option(ldap.OPT_NETWORK_TIMEOUT, 10)
            connection.set_option(ldap.OPT_TIMEOUT, 15)
            connection.simple_bind_s(bind_dn, password)
            result: dict[str, set[str]] = {}
            roles_by_user: dict[str, set[str]] = {}
            for role in self.roles:
                found = connection.search_s(
                    self.group_base, ldap.SCOPE_SUBTREE,
                    f"(cn={ldap.filter.escape_filter_chars(role['group'])})",
                    ["cn", "member"],
                )
                groups = [attrs for _dn, attrs in found if isinstance(attrs, dict)]
                if len(groups) != 1:
                    raise ReconcileError("directory-role-group-unavailable")
                members = set()
                for member_dn in groups[0].get("member", []):
                    parsed = ldap.dn.str2dn(member_dn.decode() if isinstance(member_dn, bytes) else member_dn)
                    uid = next((value for rdn in parsed for attr, value, _flags in rdn if attr.lower() == "uid"), None)
                    if uid:
                        members.add(uid)
                result[role["group"]] = members
                for member in members:
                    roles_by_user.setdefault(member, set()).add(role["group"])
            if any(len(groups) > 1 for groups in roles_by_user.values()):
                raise ReconcileError("directory-conflicting-role-membership")
            enabled: dict[str, set[str]] = {}
            for role in self.roles:
                current = set()
                for username in result[role["group"]]:
                    matches = connection.search_s(
                        self.user_base, ldap.SCOPE_SUBTREE,
                        f"(&(objectClass=posixAccount)(uid={ldap.filter.escape_filter_chars(username)}))",
                        ["uid", "nsAccountLock"],
                    )
                    users = [attrs for _dn, attrs in matches if isinstance(attrs, dict)]
                    if len(users) != 1:
                        raise ReconcileError("directory-user-unavailable")
                    locked = users[0].get("nsAccountLock", [b"FALSE"])[0]
                    if isinstance(locked, bytes):
                        locked = locked.decode("ascii", "ignore")
                    if str(locked).lower() not in {"true", "yes", "1"}:
                        current.add(username)
                enabled[role["group"]] = current
            return enabled
        except ReconcileError:
            raise
        except ldap.INVALID_CREDENTIALS:
            raise ReconcileError("directory-authentication-failed")
        except ldap.SERVER_DOWN:
            raise ReconcileError("directory-unavailable")
        except ldap.LDAPError:
            raise ReconcileError("directory-query-failed")
        except Exception:
            raise ReconcileError("directory-response-invalid")
        finally:
            if connection is not None:
                try:
                    connection.unbind_s()
                except ldap.LDAPError:
                    pass


class RustFS:
    def __init__(self, client):
        self.client = client

    def request(self, method: str, path: str, query: dict | None = None, body: bytes = b"", access=None, key=None):
        attempts = READ_RETRY_ATTEMPTS if method in {"GET", "HEAD"} else 1
        for attempt in range(attempts):
            try:
                result = self.client.request(method, path, query, body, access, key)
            except Exception:
                if attempt + 1 < attempts:
                    time.sleep(READ_RETRY_DELAY_SECONDS)
                    continue
                raise ReconcileError("rustfs-transport-failed")
            if result[0] in TRANSIENT_READ_STATUSES and attempt + 1 < attempts:
                time.sleep(READ_RETRY_DELAY_SECONDS)
                continue
            return result
        raise ReconcileError("rustfs-transport-failed")

    @staticmethod
    def error_code(body: bytes) -> str:
        try:
            value = json.loads(body)
            code = value.get("Code") or value.get("code") if isinstance(value, dict) else None
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                code = ET.fromstring(body).findtext("Code")
            except ET.ParseError:
                return "unknown"
        return code if isinstance(code, str) and code in SAFE_ERROR_CODES else "unknown"

    def list_bucket_policy(self, bucket: str):
        status, body = self.request("GET", f"/{bucket}", {"policy": ""})
        if status == 404 and self.error_code(body) == "NoSuchBucketPolicy":
            return None
        if status != 200:
            raise ReconcileError("rustfs-bucket-policy-inspection-failed")
        try:
            return json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ReconcileError("rustfs-bucket-policy-invalid")

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.bucket_names()

    def bucket_names(self) -> set[str]:
        status, body = self.request("GET", "/")
        if status != 200:
            if self.error_code(body) in {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
                raise ReconcileError("rustfs-authentication-failed")
            raise ReconcileError("rustfs-bucket-inspection-failed")
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            raise ReconcileError("rustfs-bucket-inventory-invalid")
        buckets_nodes = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "Buckets"]
        if len(buckets_nodes) != 1:
            raise ReconcileError("rustfs-bucket-inventory-invalid")
        names = []
        for bucket_node in buckets_nodes[0]:
            if bucket_node.tag.rsplit("}", 1)[-1] != "Bucket":
                raise ReconcileError("rustfs-bucket-inventory-invalid")
            name_nodes = [node for node in bucket_node if node.tag.rsplit("}", 1)[-1] == "Name"]
            if len(name_nodes) != 1 or not name_nodes[0].text:
                raise ReconcileError("rustfs-bucket-inventory-invalid")
            names.append(name_nodes[0].text)
        if len(names) != len(set(names)):
            raise ReconcileError("rustfs-bucket-inventory-invalid")
        return set(names)

    def ensure_bucket(self, bucket: str) -> bool:
        if self.bucket_exists(bucket):
            return False
        status, _body = self.request("PUT", f"/{bucket}")
        if status not in (200, 201, 204):
            raise ReconcileError("rustfs-bucket-create-failed", changed=True)
        return True

    def user_info(self, username: str) -> dict | None:
        status, body = self.request("GET", "/rustfs/admin/v3/user-info", {"accessKey": username})
        if status == 404 and self.error_code(body) in {"NoSuchUser", "NoSuchResource"}:
            return None
        if status != 200:
            raise ReconcileError("rustfs-user-inspection-failed")
        return self.json_dict(body, "rustfs-user-response-invalid")

    @staticmethod
    def json_dict(body: bytes, error: str) -> dict:
        try:
            value = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ReconcileError(error)
        if not isinstance(value, dict):
            raise ReconcileError(error)
        return value

    def ensure_user(self, username: str, secret_name: str) -> bool:
        current = self.user_info(username)
        if current is not None:
            if str(current.get("status", "enabled")).lower() not in {"enabled", "on", "active"}:
                raise ReconcileError("rustfs-managed-user-disabled")
            return False
        try:
            password = Path("/run/secrets", secret_name).read_text(encoding="utf-8").strip()
        except OSError:
            raise ReconcileError("rustfs-role-credential-unavailable")
        if not password:
            raise ReconcileError("rustfs-role-credential-empty")
        payload = json.dumps({"secretKey": password, "status": "enabled"}, separators=(",", ":")).encode()
        status, _body = self.request("PUT", "/rustfs/admin/v3/add-user", {"accessKey": username}, payload)
        if status not in (200, 201, 204):
            raise ReconcileError("rustfs-user-create-failed", changed=True)
        return True

    def group_info(self, group: str) -> dict | None:
        status, body = self.request("GET", "/rustfs/admin/v3/group", {"group": group})
        code = self.error_code(body)
        if status == 404 and code in {"NoSuchGroup", "NoSuchResource"}:
            return None
        if status != 200:
            raise ReconcileError("rustfs-group-inspection-failed")
        return self.json_dict(body, "rustfs-group-response-invalid")

    def group_members(self, record: dict) -> set[str]:
        candidates = [record.get("members"), record.get("Members"), record.get("users"), record.get("Users")]
        for value in candidates:
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                return set(value)
        raise ReconcileError("rustfs-group-membership-response-invalid")

    def update_members(self, group: str, members: set[str], remove: bool) -> None:
        payload = json.dumps(
            {"group": group, "members": sorted(members), "isRemove": remove, "groupStatus": "enabled"},
            separators=(",", ":"),
        ).encode()
        status, body = self.request("PUT", "/rustfs/admin/v3/update-group-members", body=payload)
        if status not in (200, 201, 204):
            try:
                response_message = ET.fromstring(body).findtext("Message") or ""
            except ET.ParseError:
                response_message = ""
            response_message = re.sub(r"[^A-Za-z0-9 _.-]", "", response_message)[:120]
            print(
                f"RustFS group membership update rejected (HTTP {status}, code {self.error_code(body)}, message {response_message or 'unavailable'})",
                file=sys.stderr,
            )
            raise ReconcileError("rustfs-group-membership-update-failed", changed=True)

    def policy(self, name: str) -> dict | None:
        status, body = self.request("GET", "/rustfs/admin/v3/info-canned-policy", {"name": name})
        code = self.error_code(body)
        if status == 404 and code in {"NoSuchCannedPolicy", "NoSuchPolicy", "NoSuchResource"}:
            return None
        if status == 500 and code == "InternalError":
            try:
                message = (ET.fromstring(body).findtext("Message") or "").strip().lower()
            except ET.ParseError:
                message = ""
            if message == "policy does not exist":
                return None
        if status != 200:
            raise ReconcileError("rustfs-policy-inspection-failed")
        value = self.json_dict(body, "rustfs-policy-response-invalid")
        policy = value.get("policy", value)
        if not isinstance(policy, dict):
            raise ReconcileError("rustfs-policy-document-invalid")
        return policy

    def ensure_policy(self, name: str, document: dict) -> bool:
        current = self.policy(name)
        if current is not None:
            if canonical_json(current) != canonical_json(document):
                raise ReconcileError("rustfs-policy-drift-requires-review")
            return False
        body = json.dumps(document, separators=(",", ":")).encode()
        status, _response = self.request("PUT", "/rustfs/admin/v3/add-canned-policy", {"name": name}, body)
        if status not in (200, 201, 204):
            raise ReconcileError("rustfs-policy-create-failed", changed=True)
        return True

    def policy_entities(self, *, user: str | None = None, group: str | None = None) -> list[str]:
        if (user is None) == (group is None):
            raise ReconcileError("rustfs-policy-binding-query-invalid")
        target = user or group
        query = {"user": user} if user else {"group": group}
        status, body = self.request("GET", "/rustfs/admin/v3/idp/builtin/policy-entities", query)
        if status != 200:
            raise ReconcileError("rustfs-policy-binding-inspection-failed")
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ReconcileError("rustfs-policy-binding-response-invalid")
        mapping_field, identity_field = ("userMappings", "user") if user else ("groupMappings", "group")
        if (not isinstance(payload, dict) or not isinstance(payload.get("timestamp"), str)
                or set(payload) not in ({"timestamp"}, {"timestamp", mapping_field})):
            raise ReconcileError("rustfs-policy-binding-response-invalid")
        mappings = payload.get(mapping_field, [])
        if not isinstance(mappings, list):
            raise ReconcileError("rustfs-policy-binding-response-invalid")
        if any(not isinstance(item, dict) or not isinstance(item.get(identity_field), str)
               or not isinstance(item.get("policies"), list)
               or any(not isinstance(name, str) for name in item["policies"])
               for item in mappings):
            raise ReconcileError("rustfs-policy-binding-response-invalid")
        matches = [item for item in mappings if item[identity_field] == target]
        if len(matches) > 1:
            raise ReconcileError("rustfs-policy-binding-response-invalid")
        return sorted(matches[0]["policies"]) if matches else []

    def set_group_policy(self, group: str, policy: str) -> bool:
        existing = self.policy_entities(group=group)
        if existing == [policy]:
            return False
        if existing:
            raise ReconcileError("rustfs-group-policy-drift-requires-review")
        status, _body = self.request(
            "PUT", "/rustfs/admin/v3/set-user-or-group-policy",
            {"policyName": policy, "userOrGroup": group, "isGroup": "true"},
        )
        if status not in (200, 201, 204):
            raise ReconcileError("rustfs-group-policy-set-failed", changed=True)
        return True

    def detach_user_policy(self, user: str, policy: str) -> bool:
        existing = self.policy_entities(user=user)
        if policy not in existing:
            if existing:
                raise ReconcileError("rustfs-user-policy-drift-requires-review")
            return False
        payload = json.dumps({"policies": [policy], "user": user}, separators=(",", ":")).encode()
        status, _body = self.request("POST", "/rustfs/admin/v3/idp/builtin/policy/detach", body=payload)
        if status not in (200, 201, 204):
            raise ReconcileError("rustfs-user-policy-detach-failed", changed=True)
        return True

    def capture_snapshot(self, run_id: str) -> Path:
        status, body = self.request("GET", "/rustfs/admin/v3/export-iam")
        if status != 200 or not body:
            raise ReconcileError("rustfs-iam-snapshot-unavailable")
        if len(body) > 256 * 1024 * 1024:
            raise ReconcileError("rustfs-iam-snapshot-invalid")
        try:
            with zipfile.ZipFile(BytesIO(body)) as archive:
                entries = archive.infolist()
                if not entries or len(entries) > 10_000:
                    raise ReconcileError("rustfs-iam-snapshot-invalid")
                total_size = 0
                for entry in entries:
                    path = PurePosixPath(entry.filename)
                    mode = entry.external_attr >> 16
                    if (path.is_absolute() or ".." in path.parts or "\\" in entry.filename
                            or stat.S_ISLNK(mode) or entry.flag_bits & 0x1):
                        raise ReconcileError("rustfs-iam-snapshot-invalid")
                    total_size += entry.file_size
                    if entry.file_size > 64 * 1024 * 1024 or total_size > 256 * 1024 * 1024:
                        raise ReconcileError("rustfs-iam-snapshot-invalid")
                if archive.testzip() is not None:
                    raise ReconcileError("rustfs-iam-snapshot-invalid")
        except ReconcileError:
            raise
        except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError):
            raise ReconcileError("rustfs-iam-snapshot-invalid")
        SNAPSHOT_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(SNAPSHOT_DIR, 0o700)
        path = SNAPSHOT_DIR / f"iam-{run_id}.json"
        fd, name = tempfile.mkstemp(prefix=".iam-snapshot.", dir=SNAPSHOT_DIR)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
            os.chmod(path, 0o600)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        return path


class ProbeRunner:
    def __init__(self, rustfs: RustFS, roles: list[dict]):
        self.rustfs = rustfs
        self.roles = roles
        self.credentials = {
            "developer-user": self._read("rustfs-developer-secret-key"),
            "analyst-user": self._read("rustfs-analyst-secret-key"),
            "write-service-account": self._read("rustfs-writer-secret-key"),
        }
        self.refs: list[tuple[str, str]] = []

    @staticmethod
    def _read(filename: str) -> str:
        try:
            value = Path("/run/secrets", filename).read_text(encoding="utf-8").strip()
        except OSError:
            raise ReconcileError("s3-probe-credential-unavailable")
        if not value:
            raise ReconcileError("s3-probe-credential-empty")
        return value

    def s3(self, method: str, path: str, query: dict | None, body: bytes, username: str) -> tuple[int, bytes]:
        return self.rustfs.request(method, path, query, body, username, self.credentials[username])

    @staticmethod
    def require(status: int, allowed: bool, category: str, accepted: set[int] | None = None) -> None:
        expected = (accepted or {200}) if allowed else {403}
        if status not in expected:
            raise ReconcileError(category)

    @staticmethod
    def xml_text(element: ET.Element, name: str) -> str | None:
        for child in element.iter():
            if child.tag.rsplit("}", 1)[-1] == name and child.text:
                return child.text
        return None

    def run(self) -> None:
        writer = "write-service-account"
        nonce = uuid.uuid4().hex
        try:
            for bucket in ("lake", "lake-dev", "lake-uat"):
                key = f".identity-reconcile-probe/{nonce}/{bucket}"
                self.refs.append((bucket, key))
                status, _body = self.s3("PUT", f"/{bucket}/{key}", None, b"reconciliation-probe", writer)
                self.require(status, True, "writer-probe-put-failed")
            reference_keys = tuple(self.refs)
            for role in self.roles:
                user = role["members"][0]
                read_buckets = set(role["read_buckets"])
                write_buckets = set(role["write_buckets"])
                for bucket, key in reference_keys:
                    allowed = bucket in read_buckets
                    status, _body = self.s3("GET", f"/{bucket}", {"list-type": "2", "prefix": key, "max-keys": "1"}, b"", user)
                    self.require(status, allowed, "s3-list-probe-failed")
                    status, _body = self.s3("GET", f"/{bucket}/{key}", None, b"", user)
                    self.require(status, allowed, "s3-read-probe-failed")
                    status, _body = self.s3("GET", f"/{bucket}", {"location": ""}, b"", user)
                    self.require(status, allowed, "s3-location-probe-failed")
                    status, _body = self.s3("GET", f"/{bucket}", {"uploads": ""}, b"", user)
                    self.require(status, bucket in write_buckets, "s3-list-multipart-probe-failed")
                    if bucket in write_buckets:
                        own_key = f".identity-reconcile-probe/{nonce}/{user}/{bucket}"
                        self.refs.append((bucket, own_key))
                        status, _body = self.s3("PUT", f"/{bucket}/{own_key}", None, b"write-probe", user)
                        self.require(status, True, "s3-write-probe-failed")
                        self._multipart(bucket, nonce, user)
                        status, _body = self.s3("DELETE", f"/{bucket}/{own_key}", None, b"", user)
                        self.require(status, True, "s3-delete-probe-failed", {200, 204})
                        self.refs.remove((bucket, own_key))
                    else:
                        status, _body = self.s3("PUT", f"/{bucket}/{key}", None, b"denied-write-probe", user)
                        self.require(status, False, "s3-denied-write-probe-failed")
                        status, _body = self.s3("DELETE", f"/{bucket}/{key}", None, b"", user)
                        self.require(status, False, "s3-denied-delete-probe-failed")
        finally:
            cleanup_failed = False
            for bucket, key in reversed(self.refs):
                status, _body = self.s3("DELETE", f"/{bucket}/{key}", None, b"", writer)
                cleanup_failed |= status not in (200, 204, 404)
            if cleanup_failed:
                raise ReconcileError("s3-probe-cleanup-failed", changed=True)

    def _multipart(self, bucket: str, nonce: str, user: str) -> None:
        key = f".identity-reconcile-probe/{nonce}/{user}/{bucket}-multipart"
        attempted = False
        cleanup_complete = False
        upload_id = None
        try:
            attempted = True
            status, body = self.s3("POST", f"/{bucket}/{key}", {"uploads": ""}, b"", user)
            self.require(status, True, "s3-multipart-initiate-probe-failed")
            try:
                upload_id = self.xml_text(ET.fromstring(body), "UploadId")
            except ET.ParseError:
                upload_id = None
            if not upload_id:
                raise ReconcileError("s3-multipart-response-invalid", changed=True)
            part_query = {"partNumber": "1", "uploadId": upload_id}
            status, _body = self.s3("PUT", f"/{bucket}/{key}", part_query, b"part", user)
            self.require(status, True, "s3-multipart-part-probe-failed")
            status, _body = self.s3("GET", f"/{bucket}/{key}", {"uploadId": upload_id}, b"", user)
            self.require(status, True, "s3-multipart-list-parts-probe-failed")
            status, _body = self.s3("DELETE", f"/{bucket}/{key}", {"uploadId": upload_id}, b"", user)
            self.require(status, True, "s3-multipart-abort-probe-failed", {200, 204})
            cleanup_complete = True
        finally:
            if attempted and not cleanup_complete:
                upload_ids = [upload_id] if upload_id else self._find_probe_uploads(bucket, key, user)
                cleanup_failed = False
                for candidate in upload_ids:
                    status, _body = self.s3(
                        "DELETE", f"/{bucket}/{key}", {"uploadId": candidate}, b"", user
                    )
                    cleanup_failed |= status not in (200, 204, 404)
                if cleanup_failed:
                    raise ReconcileError("s3-multipart-cleanup-failed", changed=True)

    def _find_probe_uploads(self, bucket: str, key: str, user: str) -> list[str]:
        status, body = self.s3(
            "GET", f"/{bucket}", {"uploads": "", "prefix": key}, b"", user
        )
        if status != 200:
            raise ReconcileError("s3-multipart-cleanup-inspection-failed", changed=True)
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            raise ReconcileError("s3-multipart-cleanup-response-invalid", changed=True)
        matches = []
        for element in root.iter():
            if element.tag.rsplit("}", 1)[-1] != "Upload":
                continue
            key_value = self.xml_text(element, "Key")
            upload_id = self.xml_text(element, "UploadId")
            if key_value == key and upload_id:
                matches.append(upload_id)
        return matches


def current_time() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def require_isolated_target() -> None:
    try:
        target = urlsplit(RUSTFS_ENDPOINT)
        port = target.port
    except ValueError:
        raise ReconcileError("isolated-rustfs-target-required")
    if (target.scheme != "http" or target.hostname != "rustfs-iam-test"
            or port != 9000 or target.path or target.query or target.fragment):
        raise ReconcileError("isolated-rustfs-target-required")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile FreeIPA roles to RustFS IAM.")
    parser.add_argument("--reviewed-prior-run", action="store_true", help="confirm an operator inspected an incomplete prior run")
    args = parser.parse_args()
    RUNTIME_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(RUNTIME_DIR, 0o700)
    lock_stream = LOCK_FILE.open("a+")
    try:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("RustFS reconciliation: already-running")
        return 3
    except OSError:
        print("RustFS reconciliation: blocked (lock-unavailable)", file=sys.stderr)
        return 2

    run_id = uuid.uuid4().hex
    start = time.monotonic()
    record = {"run_id": run_id, "started_at": current_time(), "state": "preflight", "counts": {}}
    changed = False
    try:
        policy = read_json(POLICY_FILE)
        validate_policy(policy)
        require_isolated_target()
        record["policy_version"] = policy["policy_version"]
        if STATUS_FILE.exists():
            previous = read_json(STATUS_FILE)
            if previous.get("state") in NONTERMINAL_STATES and not args.reviewed_prior_run:
                raise ReconcileError("prior-run-review-required")
        client = load_admin_client()
        rustfs = RustFS(client)
        memberships = DirectoryReader(policy).memberships()
        for role in policy["roles"]:
            wanted = set(role["members"])
            if memberships[role["group"]] != wanted:
                raise ReconcileError("directory-role-membership-review-required")
        probes = ProbeRunner(rustfs, policy["roles"])

        bucket_states = {name: rustfs.bucket_exists(name) for name in policy["buckets"]}
        if not bucket_states["lake"]:
            raise ReconcileError("production-bucket-missing")
        for bucket in policy["buckets"]:
            if bucket_states[bucket] and rustfs.list_bucket_policy(bucket) is not None:
                raise ReconcileError("bucket-policy-review-required")

        role_policies = {role["policy"]: make_policy(role) for role in policy["roles"]}
        observed_policies = {name: rustfs.policy(name) for name in role_policies}
        for name, expected in role_policies.items():
            if observed_policies[name] is not None and canonical_json(observed_policies[name]) != canonical_json(expected):
                raise ReconcileError("rustfs-policy-drift-requires-review")

        admin = rustfs.user_info("admin")
        if admin is None or str(admin.get("status", "enabled")).lower() not in {"enabled", "on", "active"}:
            raise ReconcileError("admin-preservation-check-failed")
        admin_bindings = rustfs.policy_entities(user="admin")
        if admin_bindings != ["consoleAdmin"]:
            raise ReconcileError("admin-policy-preservation-check-failed")

        managed_users = {
            role["members"][0]: rustfs.user_info(role["members"][0])
            for role in policy["roles"]
        }
        for info in managed_users.values():
            if info is not None and str(info.get("status", "enabled")).lower() not in {"enabled", "on", "active"}:
                raise ReconcileError("rustfs-managed-user-disabled")
        writer_info = managed_users["write-service-account"]
        if writer_info is None:
            raise ReconcileError("writer-preservation-check-failed")
        writer_direct = rustfs.policy_entities(user="write-service-account")
        if writer_direct not in ([], [policy["legacy_writer_policy"]]):
            raise ReconcileError("writer-policy-review-required")
        if writer_direct and rustfs.policy(policy["legacy_writer_policy"]) is None:
            raise ReconcileError("legacy-writer-policy-missing")
        for username in ("developer-user", "analyst-user"):
            if rustfs.policy_entities(user=username):
                raise ReconcileError("managed-user-policy-review-required")

        record["state"] = "planned"
        planned_counts = {"bucket_create": sum(not bucket_states[item] for item in ("lake-dev", "lake-uat")),
                          "user_create": 0, "membership_add": 0, "membership_remove": 0,
                          "policy_create": sum(value is None for value in observed_policies.values()),
                          "binding_set": 0}
        groups_current = {}
        for role in policy["roles"]:
            desired = memberships[role["group"]]
            current = rustfs.group_info(role["group"])
            if current is not None and str(current.get("status", "enabled")).lower() not in {"enabled", "on", "active"}:
                raise ReconcileError("rustfs-role-group-disabled")
            members = set() if current is None else rustfs.group_members(current)
            groups_current[role["group"]] = (current, members)
            planned_counts["membership_add"] += len(desired - members)
            planned_counts["membership_remove"] += len(members - desired)
            if rustfs.policy_entities(group=role["group"]) not in ([], [role["policy"]]):
                raise ReconcileError("rustfs-group-policy-review-required")
            if rustfs.policy_entities(group=role["group"]) != [role["policy"]]:
                planned_counts["binding_set"] += 1
            for user in desired:
                if managed_users.get(user) is None:
                    planned_counts["user_create"] += 1
        record["counts"] = planned_counts

        mutating = any(planned_counts.values()) or writer_direct == [policy["legacy_writer_policy"]]
        if not mutating:
            record["state"] = "verifying"
            probes.run()
            record.update({"state": "no-change", "verification": "readback-and-role-probes-passed"})
            return 0

        write_status({**record, "state": "planned"})
        # Snapshot all managed IAM state before the first change, including membership deltas.
        rustfs.capture_snapshot(run_id)
        record["state"] = "applying"
        write_status(record)
        for bucket in ("lake-dev", "lake-uat"):
            if not bucket_states[bucket]:
                changed |= rustfs.ensure_bucket(bucket)
        for role in policy["roles"]:
            for user in memberships[role["group"]]:
                filename = {
                    "developer-user": "rustfs-developer-secret-key",
                    "analyst-user": "rustfs-analyst-secret-key",
                    "write-service-account": "rustfs-writer-secret-key",
                }[user]
                changed |= rustfs.ensure_user(user, filename)
        for role in policy["roles"]:
            group = role["group"]
            current, members = groups_current[group]
            desired = memberships[group]
            additions = desired - members
            removals = members - desired
            if additions:
                rustfs.update_members(group, additions, False)
                changed = True
            if removals:
                rustfs.update_members(group, removals, True)
                changed = True
            changed |= rustfs.ensure_policy(role["policy"], make_policy(role))
            changed |= rustfs.set_group_policy(group, role["policy"])

        record["state"] = "verifying"
        write_status(record)
        for role in policy["roles"]:
            group_info = rustfs.group_info(role["group"])
            if group_info is None or rustfs.group_members(group_info) != memberships[role["group"]]:
                raise ReconcileError("rustfs-membership-readback-failed", changed=changed)
            if rustfs.policy(role["policy"]) != make_policy(role):
                raise ReconcileError("rustfs-policy-readback-failed", changed=changed)
            if rustfs.policy_entities(group=role["group"]) != [role["policy"]]:
                raise ReconcileError("rustfs-binding-readback-failed", changed=changed)
        probes.run()

        # The legacy writer grant is a known narrower policy on the current user.
        # Remove it only after the new group policy and complete probes are verified.
        if writer_direct == [policy["legacy_writer_policy"]]:
            if not rustfs.detach_user_policy("write-service-account", policy["legacy_writer_policy"]):
                raise ReconcileError("legacy-writer-binding-not-removed", changed=True)
            changed = True
            if rustfs.policy_entities(user="write-service-account"):
                raise ReconcileError("writer-direct-policy-remains", changed=True)

        record.update({"state": "complete", "verification": "readback-and-role-probes-passed"})
        return 0
    except ReconcileError as error:
        record["state"] = "partial-failure" if (changed or error.changed or record.get("state") in {"applying", "verifying"}) else "blocked"
        record["failure_category"] = error.category
        print(f"RustFS reconciliation: {record['state']} ({error.category})", file=sys.stderr)
        return 1 if record["state"] == "partial-failure" else 2
    except Exception:
        record["state"] = "partial-failure" if (changed or record.get("state") in {"applying", "verifying"}) else "blocked"
        record["failure_category"] = "unexpected-error"
        print(f"RustFS reconciliation: {record['state']} (unexpected-error)", file=sys.stderr)
        return 1 if record["state"] == "partial-failure" else 2
    finally:
        record["finished_at"] = current_time()
        record["elapsed_seconds"] = round(time.monotonic() - start, 3)
        if record.get("state") in SAFE_TERMINAL_STATES:
            try:
                write_status(record)
            except Exception:
                print("RustFS reconciliation: status-write-failed", file=sys.stderr)
        try:
            fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        lock_stream.close()


if __name__ == "__main__":
    sys.exit(main())
