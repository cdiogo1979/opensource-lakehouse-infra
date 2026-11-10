#!/usr/bin/python3
"""Create RustFS IAM identities through its SigV4 authenticated admin API."""

import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
import uuid

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

ENDPOINT = os.environ.get("RUSTFS_ENDPOINT", "http://object-store:9000")
REGION = os.environ.get("AWS_REGION", "us-east-1")
BUCKET = "lake"
PREFIX_A = "warehouse/databaseA.db"
PREFIX_B = "warehouse/databaseB.db"
STARROCKS_SECRET = "rustfs-starrocks-secret-key"
STARROCKS_POLICY = "lakehouse-starrocks"
ROLE_BUCKETS = ("lake", "lake-dev", "lake-uat")
SAFE_ERROR_CODES = {
    "AccessDenied",
    "InvalidAccessKeyId",
    "SignatureDoesNotMatch",
    "NoSuchCannedPolicy",
    "NoSuchPolicy",
    "NoSuchUser",
    "InvalidRequest",
    "InternalError",
    "ServiceUnavailable",
}


def secret(name: str) -> str:
    path = f"/run/secrets/{name}"
    try:
        value = open(path, encoding="utf-8").read().strip()
    except OSError:
        raise RuntimeError(f"Required RustFS credential file is unavailable: {name}")
    if not value:
        raise RuntimeError(f"Required RustFS credential file is empty: {name}")
    return value


def request(method: str, path: str, query: dict[str, str] | None = None,
            body: bytes = b"", access: str | None = None,
            key: str | None = None) -> tuple[int, bytes]:
    query_string = urllib.parse.urlencode(query or {})
    url = f"{ENDPOINT}{path}" + (f"?{query_string}" if query_string else "")
    headers = {
        "host": urllib.parse.urlsplit(ENDPOINT).netloc,
        "x-amz-content-sha256": hashlib.sha256(body).hexdigest(),
    }
    if body:
        headers["content-type"] = "application/json"
    credentials = Credentials(access or secret("rustfs-root-access-key"),
                              key or secret("rustfs-root-secret-key"))
    signed = AWSRequest(method=method, url=url, data=body or None, headers=headers)
    SigV4Auth(credentials, "s3", REGION).add_auth(signed)
    outgoing = urllib.request.Request(url, data=body or None,
                                     headers=dict(signed.headers), method=method)
    try:
        with urllib.request.urlopen(outgoing, timeout=15) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"RustFS request failed ({method} {path}): {type(error).__name__}")


def policy(statements: list[dict]) -> bytes:
    return json.dumps({"Version": "2012-10-17", "Statement": statements},
                      separators=(",", ":")).encode()


def response_error_code(body: bytes) -> str:
    """Return an allowlisted provider code and never expose response text."""
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        try:
            payload = ElementTree.fromstring(body)
            code = payload.findtext("Code")
            return code if code in SAFE_ERROR_CODES else "unknown"
        except ElementTree.ParseError:
            return "unknown"
    code = payload.get("Code") or payload.get("code")
    return code if isinstance(code, str) and code in SAFE_ERROR_CODES else "unknown"


def missing_canned_policy(status: int, body: bytes) -> bool:
    """Recognize the pinned RustFS release's XML response for an absent policy."""
    if status == 404 or response_error_code(body) in {"NoSuchCannedPolicy", "NoSuchPolicy"}:
        return True
    if status != 500 or response_error_code(body) != "InternalError":
        return False
    try:
        payload = ElementTree.fromstring(body)
    except ElementTree.ParseError:
        return False
    return (payload.findtext("Message") or "").strip().lower() == "policy does not exist"


def canonical_policy(document: dict) -> dict | None:
    """Normalize order-insensitive IAM policy arrays for exact drift checks."""
    statements = document.get("Statement")
    if not isinstance(statements, list):
        return None
    normalized = []
    for statement in statements:
        if not isinstance(statement, dict):
            return None
        item = dict(statement)
        for key in ("Action", "Resource"):
            values = item.get(key)
            if isinstance(values, list):
                item[key] = sorted(values)
        condition = item.get("Condition")
        if isinstance(condition, dict):
            condition = dict(condition)
            for operator, fields in condition.items():
                if isinstance(fields, dict):
                    fields = dict(fields)
                    for name, values in fields.items():
                        if isinstance(values, list):
                            fields[name] = sorted(values)
                    condition[operator] = fields
            item["Condition"] = condition
        normalized.append(item)
    return {"Version": document.get("Version"),
            "Statement": sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True))}


def bucket_statements(prefixes: list[str], read_write: bool) -> list[dict]:
    allowed_prefixes = [p for prefix in prefixes for p in (prefix, f"{prefix}/", f"{prefix}/*")]
    bucket_actions = ["s3:ListBucket"]
    if read_write:
        bucket_actions.append("s3:ListBucketMultipartUploads")
    statements = [{
        "Effect": "Allow", "Action": bucket_actions,
        "Resource": [f"arn:aws:s3:::{BUCKET}"],
        "Condition": {"StringLike": {"s3:prefix": allowed_prefixes}},
    }, {
        "Effect": "Allow", "Action": ["s3:GetBucketLocation"],
        "Resource": [f"arn:aws:s3:::{BUCKET}"],
    }]
    object_actions = ["s3:GetObject"]
    if read_write:
        object_actions += ["s3:PutObject", "s3:DeleteObject",
                           "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"]
    statements.append({
        "Effect": "Allow", "Action": object_actions,
        "Resource": [f"arn:aws:s3:::{BUCKET}/{p}/*" for p in prefixes],
    })
    return statements


def lake_bucket_statements() -> list[dict]:
    """Grant the ETL writer list and object access across all approved environments."""
    return [{
        "Effect": "Allow",
        "Action": ["s3:ListBucket", "s3:ListBucketMultipartUploads", "s3:GetBucketLocation"],
        "Resource": [f"arn:aws:s3:::{bucket}" for bucket in ROLE_BUCKETS],
    }, {
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject",
                   "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"],
        "Resource": [f"arn:aws:s3:::{bucket}/*" for bucket in ROLE_BUCKETS],
    }]


def environment_role_statements(role: str) -> list[dict]:
    """Build the approved least-privilege object policy for a human role."""
    if role == "developer-user":
        read_buckets = ROLE_BUCKETS
        write_buckets = ("lake-dev",)
    elif role == "analyst-user":
        read_buckets = ("lake",)
        write_buckets = ()
    else:
        raise RuntimeError("Unsupported human RustFS role")

    statements = [{
        "Effect": "Allow",
        "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
        "Resource": [f"arn:aws:s3:::{bucket}" for bucket in read_buckets],
    }, {
        "Effect": "Allow",
        "Action": ["s3:GetObject"],
        "Resource": [f"arn:aws:s3:::{bucket}/*" for bucket in read_buckets],
    }]
    for bucket in write_buckets:
        statements.extend(({
            "Effect": "Allow",
            "Action": ["s3:ListBucketMultipartUploads"],
            "Resource": [f"arn:aws:s3:::{bucket}"],
        }, {
            "Effect": "Allow",
            "Action": ["s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload",
                       "s3:ListMultipartUploadParts"],
            "Resource": [f"arn:aws:s3:::{bucket}/*"],
        }))
    return statements


def ensure_exact_policy(name: str, document: bytes) -> None:
    """Create an absent role policy; stop safely if an existing policy drifts."""
    code, current = request("GET", "/rustfs/admin/v3/info-canned-policy", {"name": name})
    if missing_canned_policy(code, current):
        code, _ = request("PUT", "/rustfs/admin/v3/add-canned-policy", {"name": name}, document)
        if code not in (200, 201, 204):
            raise RuntimeError(f"RustFS policy creation failed for {name} (HTTP {code})")
        print(f"RustFS policy {name}: created")
        return
    if code != 200:
        raise RuntimeError(f"RustFS policy inspection failed for {name} (HTTP {code})")
    try:
        response = json.loads(current)
        actual = response.get("policy", response)
    except (json.JSONDecodeError, AttributeError):
        raise RuntimeError(f"RustFS policy {name} returned an unrecognized document")
    if not isinstance(actual, dict) or canonical_policy(actual) != canonical_policy(json.loads(document)):
        raise RuntimeError(f"Existing RustFS policy {name} differs from the approved policy; manual review required")
    print(f"RustFS policy {name}: already-present and exact")


def attach_policy(user: str, policy_name: str) -> None:
    body = json.dumps({"policies": [policy_name], "user": user},
                      separators=(",", ":")).encode()
    code, _ = request("POST", "/rustfs/admin/v3/idp/builtin/policy/attach", body=body)
    if code not in (200, 201, 204):
        raise RuntimeError(f"RustFS policy attachment failed for identity {user} (HTTP {code})")


def ensure_policy(name: str, document: bytes) -> None:
    code, current = request("GET", "/rustfs/admin/v3/info-canned-policy", {"name": name})
    if missing_canned_policy(code, current):
        code, _ = request("PUT", "/rustfs/admin/v3/add-canned-policy", {"name": name}, document)
        if code not in (200, 201, 204):
            raise RuntimeError(f"RustFS policy creation failed for {name} (HTTP {code})")
        print(f"RustFS policy {name}: created")
        return
    if code != 200:
        raise RuntimeError(
            f"RustFS policy inspection failed for {name} "
            f"(HTTP {code}, {response_error_code(current)})"
        )
    expected = json.loads(document)
    try:
        response = json.loads(current)
    except json.JSONDecodeError:
        raise RuntimeError(f"RustFS policy {name} returned an unrecognized document")
    if name == STARROCKS_POLICY:
        actual = response.get("policy", response)
        if not isinstance(actual, dict) or canonical_policy(actual) != canonical_policy(expected):
            raise RuntimeError(
                f"Existing RustFS policy {name} differs from the approved policy; manual reconciliation required"
            )
        print(f"RustFS policy {name}: already-present and exact")
        return
    if name == "lakehouse-writer":
        actual = response.get("policy", response)
        if isinstance(actual, dict) and canonical_policy(actual) == canonical_policy(expected):
            print(f"RustFS policy {name}: already-present and exact")
            return
        # RustFS's add-canned-policy endpoint replaces the document for an
        # existing name. Keep the identity and secret intact while widening
        # only the writer policy to the approved complete-bucket scope.
        code, _ = request("PUT", "/rustfs/admin/v3/add-canned-policy",
                          {"name": name}, document)
        if code not in (200, 201, 204):
            raise RuntimeError(f"RustFS policy update failed for {name} (HTTP {code})")
        code, current = request("GET", "/rustfs/admin/v3/info-canned-policy", {"name": name})
        try:
            updated = json.loads(current).get("policy", json.loads(current))
        except (json.JSONDecodeError, AttributeError):
            raise RuntimeError(f"RustFS policy {name} could not be verified after update")
        if code != 200 or canonical_policy(updated) != canonical_policy(expected):
            raise RuntimeError(f"RustFS policy {name} update did not match the approved policy")
        print(f"RustFS policy {name}: updated and exact")
        return
    rendered = json.dumps(response.get("policy", response), sort_keys=True)
    for statement in expected["Statement"]:
        for action in statement["Action"]:
            if action not in rendered:
                raise RuntimeError(f"Existing RustFS policy {name} differs from the approved policy")
        for resource in statement["Resource"]:
            if resource not in rendered:
                raise RuntimeError(f"Existing RustFS policy {name} differs from the approved policy")
    print(f"RustFS policy {name}: already-present")


def verify_s3_identity(access: str, key: str, user: str) -> None:
    path = f"/{BUCKET}"
    if user == "write-service-account":
        status, _ = request("GET", path, {
            "list-type": "2", "max-keys": "0"
        }, access=access, key=key)
        if status != 200:
            raise RuntimeError(
                f"RustFS credentials for {user} could not list the complete lake bucket (HTTP {status})"
            )
        return
    prefixes = [PREFIX_A, PREFIX_B] if user == "starrocks" else [PREFIX_A]
    for prefix in prefixes:
        status, _ = request("GET", path, {
            "list-type": "2", "prefix": f"{prefix}/", "max-keys": "0"
        }, access=access, key=key)
        if status != 200:
            raise RuntimeError(
                f"RustFS credentials for {user} could not list an approved prefix (HTTP {status})"
            )


def ensure_user(user: str, key_secret: str, policy_name: str) -> None:
    # RustFS IAM uses the account's accessKey value as both its identifier and
    # its S3 access-key ID; keep the requested platform identity names stable.
    access = user
    key = secret(key_secret)
    code, _ = request("GET", "/rustfs/admin/v3/user-info", {"accessKey": user})
    if code == 404:
        payload = json.dumps({"secretKey": key, "status": "enabled"},
                             separators=(",", ":")).encode()
        code, _ = request("PUT", "/rustfs/admin/v3/add-user", {"accessKey": user}, payload)
        if code not in (200, 201, 204):
            raise RuntimeError(f"RustFS user creation failed for {user} (HTTP {code})")
        print(f"RustFS identity {user}: created")
    elif code == 200:
        if (user == "write-service-account"
                and os.environ.get("ROTATE_RUSTFS_WRITER_SECRET", "").lower() == "true"):
            payload = json.dumps({"secretKey": key, "status": "enabled"},
                                 separators=(",", ":")).encode()
            code, _ = request("PUT", "/rustfs/admin/v3/add-user",
                              {"accessKey": user}, payload)
            if code not in (200, 201, 204):
                raise RuntimeError(
                    f"RustFS writer secret rotation failed (HTTP {code}); local credential must be reconciled"
                )
            print("RustFS identity write-service-account: secret rotated")
        else:
            print(f"RustFS identity {user}: already-present")
    else:
        raise RuntimeError(f"RustFS identity inspection failed for {user} (HTTP {code})")
    attach_policy(user, policy_name)
    verify_s3_identity(access, key, user)


def verify_environment_role_access() -> None:
    """Probe role boundaries using only unique temporary objects and HEAD requests."""
    fixture_id = secret("rustfs-root-access-key")
    fixture_key = secret("rustfs-root-secret-key")
    role_keys = {
        "developer-user": secret("rustfs-developer-secret-key"),
        "analyst-user": secret("rustfs-analyst-secret-key"),
    }
    nonce = uuid.uuid4().hex
    prefix = f"warehouse/.aidlc-u3-role-probe-{nonce}"
    objects = {bucket: f"{prefix}/reader-probe" for bucket in ROLE_BUCKETS}
    cleanup: set[tuple[str, str]] = set()

    def expect(label: str, actual: int, expected: int | tuple[int, ...]) -> None:
        allowed = expected if isinstance(expected, tuple) else (expected,)
        if actual not in allowed:
            raise RuntimeError(f"RustFS role check failed ({label}, HTTP {actual}, expected {allowed})")

    try:
        for bucket, key in objects.items():
            status, _ = request("PUT", f"/{bucket}/{key}", body=b"temporary-role-probe",
                                access=fixture_id, key=fixture_key)
            expect(f"fixture-create-{bucket}", status, 200)
            cleanup.add((bucket, key))

        for bucket in ROLE_BUCKETS:
            developer_allowed = True
            analyst_allowed = bucket == "lake"
            key = objects[bucket]
            status, _ = request("HEAD", f"/{bucket}/{key}", access="developer-user",
                                key=role_keys["developer-user"])
            expect(f"developer-read-{bucket}", status, 200 if developer_allowed else 403)
            status, _ = request("GET", f"/{bucket}", {
                "list-type": "2", "prefix": prefix, "max-keys": "10"
            }, access="developer-user", key=role_keys["developer-user"])
            expect(f"developer-list-{bucket}", status, 200 if developer_allowed else 403)

            status, _ = request("HEAD", f"/{bucket}/{key}", access="analyst-user",
                                key=role_keys["analyst-user"])
            expect(f"analyst-read-{bucket}", status, 200 if analyst_allowed else 403)
            status, _ = request("GET", f"/{bucket}", {
                "list-type": "2", "prefix": prefix, "max-keys": "10"
            }, access="analyst-user", key=role_keys["analyst-user"])
            expect(f"analyst-list-{bucket}", status, 200 if analyst_allowed else 403)

            write_key = f"{prefix}/write-probe"
            expected_write = 200 if bucket == "lake-dev" else 403
            status, _ = request("PUT", f"/{bucket}/{write_key}", body=b"temporary-role-probe",
                                access="developer-user", key=role_keys["developer-user"])
            expect(f"developer-write-{bucket}", status, expected_write)
            if status == 200:
                cleanup.add((bucket, write_key))

            status, _ = request("PUT", f"/{bucket}/{write_key}", body=b"temporary-role-probe",
                                access="analyst-user", key=role_keys["analyst-user"])
            expect(f"analyst-write-{bucket}", status, 403)

        for bucket, key in objects.items():
            developer_status, _ = request(
                "DELETE", f"/{bucket}/{key}", access="developer-user",
                key=role_keys["developer-user"])
            expect(f"developer-delete-{bucket}", developer_status,
                   (200, 204) if bucket == "lake-dev" else 403)
            analyst_status, _ = request(
                "DELETE", f"/{bucket}/{key}", access="analyst-user",
                key=role_keys["analyst-user"])
            expect(f"analyst-delete-{bucket}", analyst_status, 403)
    finally:
        cleanup_errors = []
        for bucket, key in cleanup:
            status, _ = request("DELETE", f"/{bucket}/{key}", access=fixture_id, key=fixture_key)
            if status not in (200, 204):
                cleanup_errors.append(bucket)
        if cleanup_errors:
            raise RuntimeError("RustFS role probe cleanup failed for a temporary test prefix")
    print("RustFS developer/analyst read, list, write, and delete probes passed; temporary objects removed")


def verify_writer_environment_access() -> None:
    """Verify the existing ETL identity can write disposable keys in each bucket."""
    writer_id = "write-service-account"
    writer_key = secret("rustfs-writer-secret-key")
    nonce = uuid.uuid4().hex
    created: list[tuple[str, str]] = []
    try:
        for bucket in ROLE_BUCKETS:
            key = f"warehouse/.aidlc-u3-writer-probe-{nonce}/probe"
            status, _ = request("PUT", f"/{bucket}/{key}", body=b"temporary-writer-probe",
                                access=writer_id, key=writer_key)
            if status in (200, 201, 204):
                created.append((bucket, key))
            else:
                raise RuntimeError(f"Writer access check failed for {bucket} (HTTP {status})")
            status, _ = request("HEAD", f"/{bucket}/{key}", access=writer_id, key=writer_key)
            if status != 200:
                raise RuntimeError(f"Writer readback failed for {bucket} (HTTP {status})")
    finally:
        cleanup_errors = []
        for bucket, key in created:
            status, _ = request("DELETE", f"/{bucket}/{key}", access=writer_id, key=writer_key)
            if status not in (200, 204):
                cleanup_errors.append(bucket)
        if cleanup_errors:
            raise RuntimeError("Writer probe cleanup failed for a temporary test prefix")
    print("RustFS writer write/readback probes passed for all three buckets; temporary objects removed")


def verify_scoped_authorization() -> None:
    """Exercise writer/read scopes with temporary hidden objects, then remove them."""
    writer = ("write-service-account", secret("rustfs-writer-secret-key"))
    readers = {
        "user_a": secret("rustfs-user-a-secret-key"),
        "user_b": secret("rustfs-user-b-secret-key"),
    }
    nonce = uuid.uuid4().hex
    paths = {
        "A": f"{PREFIX_A}/.identity-probe-{nonce}",
        "B": f"{PREFIX_B}/.identity-probe-{nonce}",
    }
    writer_id, writer_key = writer
    try:
        for path in paths.values():
            code, _ = request("PUT", f"/{BUCKET}/{path}", body=b"identity-scope-probe",
                              access=writer_id, key=writer_key)
            if code not in (200, 201):
                raise RuntimeError("RustFS writer could not write a scoped probe object")

        for identity, key in readers.items():
            for scope, path in paths.items():
                allowed = scope == "A" or identity == "user_b"
                code, _ = request("GET", f"/{BUCKET}/{path}", access=identity, key=key)
                if (allowed and code != 200) or (not allowed and code != 403):
                    raise RuntimeError(
                        f"RustFS scoped read check failed for {identity} on database{scope} (HTTP {code})"
                    )

        denied_path = f"{BUCKET}/{paths['B']}"
        code, _ = request("PUT", f"/{denied_path}", body=b"out-of-scope-probe",
                          access="user_a", key=readers["user_a"])
        if code != 403:
            raise RuntimeError(f"RustFS denied write check failed for user_a (HTTP {code})")
    finally:
        for path in paths.values():
            code, _ = request("DELETE", f"/{BUCKET}/{path}", access=writer_id, key=writer_key)
            if code not in (200, 204):
                raise RuntimeError("RustFS authorization probe cleanup failed")
    print("RustFS writer/read scope checks passed; temporary probe objects removed")


def main() -> int:
    if sys.argv[1:] == ["--role-identities-only"]:
        roles = (
            ("developer-user", "rustfs-developer-secret-key", "lakehouse-developers"),
            ("analyst-user", "rustfs-analyst-secret-key", "lakehouse-analysts"),
        )
        for identity, secret_name, policy_name in roles:
            ensure_exact_policy(policy_name, policy(environment_role_statements(identity)))
            ensure_user(identity, secret_name, policy_name)
        print("RustFS developer/analyst identities and approved policies: complete")
        return 0
    if sys.argv[1:] == ["--writer-policy-only"]:
        ensure_policy("lakehouse-writer", policy(lake_bucket_statements()))
        print("RustFS writer policy matches the approved three-bucket scope; writer credentials unchanged")
        return 0
    if sys.argv[1:] == ["--verify-role-access"]:
        verify_environment_role_access()
        return 0
    if sys.argv[1:] == ["--verify-writer-access"]:
        verify_writer_environment_access()
        return 0
    if sys.argv[1:]:
        raise RuntimeError("Unsupported RustFS provisioning mode")

    admin_policy = "consoleAdmin"
    ensure_policy(STARROCKS_POLICY, policy(bucket_statements([PREFIX_A, PREFIX_B], True)))
    ensure_user("starrocks", STARROCKS_SECRET, STARROCKS_POLICY)

    ensure_policy("lakehouse-writer", policy(lake_bucket_statements()))
    ensure_policy("lakehouse-metastore", policy(bucket_statements([PREFIX_A, PREFIX_B], True)))
    ensure_policy("lakehouse-user-a", policy(bucket_statements([PREFIX_A], False)))
    ensure_policy("lakehouse-user-b", policy(bucket_statements([PREFIX_A, PREFIX_B], False)))

    identities = [
        ("admin", "rustfs-admin-secret-key", admin_policy),
        ("write-service-account", "rustfs-writer-secret-key", "lakehouse-writer"),
        ("hive-metastore", "rustfs-hive-secret-key", "lakehouse-metastore"),
        ("user_a", "rustfs-user-a-secret-key", "lakehouse-user-a"),
        ("user_b", "rustfs-user-b-secret-key", "lakehouse-user-b"),
    ]
    for identity in identities:
        ensure_user(*identity)
    print("RustFS identities and policies: complete (S3 path enforcement remains an integration gate)")
    if os.environ.get("VERIFY_RUSTFS_AUTHORIZATION", "").lower() == "true":
        verify_scoped_authorization()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
    except Exception:
        print("ERROR: RustFS provider failed (unexpected-error); inspect provider configuration and reconcile before rerunning.",
              file=sys.stderr)
        sys.exit(1)
