#!/usr/bin/python3
"""Create RustFS IAM identities through its SigV4 authenticated admin API."""

import hashlib
import json
import os
import re
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
    """Expose only a RustFS error code; never echo response bodies or credentials."""
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        try:
            payload = ElementTree.fromstring(body)
            code = payload.findtext("Code")
            message = payload.findtext("Message")
            if message:
                normalized_message = message.strip().lower()
                if normalized_message in ("policy not found", "policy does not exist", "nosuchpolicy"):
                    return f"{code}/policy-not-found" if code else "policy-not-found"
                for name in ("rustfs-root-access-key", "rustfs-root-secret-key"):
                    try:
                        message = message.replace(secret(name), "[redacted]")
                    except RuntimeError:
                        pass
                message = re.sub(r"[\r\n\t]+", " ", message)
                return f"{code}/{message[:100]}" if code else message[:100]
            return code or "unknown"
        except ElementTree.ParseError:
            return "unknown"
    code = payload.get("Code") or payload.get("code")
    return code if isinstance(code, str) else "unknown"


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


def attach_policy(user: str, policy_name: str) -> None:
    body = json.dumps({"policies": [policy_name], "user": user},
                      separators=(",", ":")).encode()
    code, _ = request("POST", "/rustfs/admin/v3/idp/builtin/policy/attach", body=body)
    if code not in (200, 201, 204):
        raise RuntimeError(f"RustFS policy attachment failed for identity {user} (HTTP {code})")


def ensure_policy(name: str, document: bytes) -> None:
    code, current = request("GET", "/rustfs/admin/v3/info-canned-policy", {"name": name})
    if code == 404 or response_error_code(current).endswith("/policy-not-found"):
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
        actual = json.loads(current)
    except json.JSONDecodeError:
        raise RuntimeError(f"RustFS policy {name} returned an unrecognized document")
    rendered = json.dumps(actual, sort_keys=True)
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
    status, _ = request("GET", path, {
        "list-type": "2", "prefix": f"{PREFIX_A}/", "max-keys": "0"
    }, access=access, key=key)
    if status != 200:
        raise RuntimeError(f"RustFS credentials for {user} did not authenticate (HTTP {status})")


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
    admin_policy = "consoleAdmin"
    ensure_policy("lakehouse-writer", policy(bucket_statements([PREFIX_A, PREFIX_B], True)))
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
