#!/usr/bin/env python3
"""Idempotently create the RustFS policies named after the Keycloak product groups.

RustFS maps each value of the OIDC ``groups`` claim to the policy of the same
name, so these four policies define what each product group can do in the
RustFS console. Existing policies are verified, never overwritten.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUCKETS = ("bucket-default", "bucket-default-uat", "bucket-default-dev")
LEVELS = ("read", "read_write", "manage")
ACCESS_MATRIX = {
    "role-default-owner": {
        "bucket-default": "manage",
        "bucket-default-uat": "manage",
        "bucket-default-dev": "manage",
    },
    "role-default-developer": {
        "bucket-default": "read",
        "bucket-default-uat": "read",
        "bucket-default-dev": "read_write",
    },
    "role-default-analyst": {"bucket-default": "read"},
    "role-default-writer": {
        "bucket-default": "read_write",
        "bucket-default-uat": "read_write",
        "bucket-default-dev": "read_write",
    },
}
# The RustFS console reads this bucket and object metadata while rendering;
# without it the bucket list retries GetBucketPolicyStatus indefinitely.
READ_BUCKET_ACTIONS = (
    "s3:GetBucketLocation",
    "s3:GetBucketObjectLockConfiguration",
    "s3:GetBucketPolicyStatus",
    "s3:GetBucketTagging",
    "s3:GetBucketVersioning",
    "s3:ListBucket",
    "s3:ListBucketVersions",
)
READ_OBJECT_ACTIONS = (
    "s3:GetObject",
    "s3:GetObjectLegalHold",
    "s3:GetObjectRetention",
    "s3:GetObjectTagging",
    "s3:GetObjectVersion",
)
# The first approved definitions, which lacked console metadata reads. An
# existing policy exactly equal to one of these is upgraded in place.
PREVIOUS_READ_BUCKET_ACTIONS = ("s3:GetBucketLocation", "s3:ListBucket")
PREVIOUS_READ_OBJECT_ACTIONS = ("s3:GetObject",)
WRITE_BUCKET_ACTIONS = ("s3:ListBucketMultipartUploads",)
WRITE_OBJECT_ACTIONS = (
    "s3:AbortMultipartUpload",
    "s3:DeleteObject",
    "s3:ListMultipartUploadParts",
    "s3:PutObject",
)
ACCESS_LEVEL_ACTIONS = {
    "read": (READ_BUCKET_ACTIONS, READ_OBJECT_ACTIONS),
    "read_write": (
        READ_BUCKET_ACTIONS + WRITE_BUCKET_ACTIONS,
        READ_OBJECT_ACTIONS + WRITE_OBJECT_ACTIONS,
    ),
}
PREVIOUS_ACCESS_LEVEL_ACTIONS = {
    "read": (PREVIOUS_READ_BUCKET_ACTIONS, PREVIOUS_READ_OBJECT_ACTIONS),
    "read_write": (
        PREVIOUS_READ_BUCKET_ACTIONS + WRITE_BUCKET_ACTIONS,
        PREVIOUS_READ_OBJECT_ACTIONS + WRITE_OBJECT_ACTIONS,
    ),
}
LIST_BUCKETS_STATEMENT = {
    "Effect": "Allow",
    "Action": ["s3:ListAllMyBuckets"],
    "Resource": ["arn:aws:s3:::*"],
}
SAFE_ERROR_CODES = {
    "AccessDenied",
    "InvalidAccessKeyId",
    "SignatureDoesNotMatch",
    "NoSuchCannedPolicy",
    "NoSuchPolicy",
    "InvalidRequest",
    "InternalError",
    "ServiceUnavailable",
}


class PolicyBootstrapError(Exception):
    """Safe operator-facing failure; policy documents and credentials are omitted."""


def bucket_statements(bucket: str, level: str, level_actions: dict = ACCESS_LEVEL_ACTIONS) -> list[dict]:
    bucket_arn = f"arn:aws:s3:::{bucket}"
    object_arn = f"{bucket_arn}/*"
    if level == "manage":
        return [{"Effect": "Allow", "Action": ["s3:*"], "Resource": [bucket_arn, object_arn]}]
    bucket_actions, object_actions = level_actions[level]
    return [
        {"Effect": "Allow", "Action": list(bucket_actions), "Resource": [bucket_arn]},
        {"Effect": "Allow", "Action": list(object_actions), "Resource": [object_arn]},
    ]


def access_document(access: dict[str, str], level_actions: dict = ACCESS_LEVEL_ACTIONS) -> dict:
    statements = [dict(LIST_BUCKETS_STATEMENT)]
    for bucket in BUCKETS:
        if bucket in access:
            statements.extend(bucket_statements(bucket, access[bucket], level_actions))
    return {"Version": "2012-10-17", "Statement": statements}


def policy_document(group: str) -> dict:
    return access_document(ACCESS_MATRIX[group])


def previous_policy_document(group: str) -> dict:
    return access_document(ACCESS_MATRIX[group], PREVIOUS_ACCESS_LEVEL_ACTIONS)


def policy_documents() -> dict[str, dict]:
    return {group: policy_document(group) for group in ACCESS_MATRIX}


def effective_access(groups: set[str]) -> dict[str, str]:
    """Per-bucket highest access level across a user's product groups."""
    access: dict[str, str] = {}
    for group in groups:
        for bucket, level in ACCESS_MATRIX[group].items():
            if bucket not in access or LEVELS.index(level) > LEVELS.index(access[bucket]):
                access[bucket] = level
    return access


def _as_sorted_list(value: object) -> list | None:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return sorted(set(value))
    return None


def canonical_policy(document: object) -> dict | None:
    """Normalize order-insensitive policy fields so equal policies compare equal."""
    if not isinstance(document, dict) or not isinstance(document.get("Statement"), list):
        return None
    statements = []
    for statement in document["Statement"]:
        if not isinstance(statement, dict):
            return None
        item = {key: value for key, value in statement.items() if value not in (None, "", [], {})}
        for key in ("Action", "Resource"):
            if key in item:
                values = _as_sorted_list(item[key])
                if values is None:
                    return None
                item[key] = values
        statements.append(item)
    unique = {json.dumps(item, sort_keys=True): item for item in statements}
    return {
        "Version": document.get("Version"),
        "Statement": [unique[key] for key in sorted(unique)],
    }


def response_error_code(body: bytes) -> str:
    """Return an allowlisted provider error code and never expose response text."""
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        try:
            code = ElementTree.fromstring(body).findtext("Code")
        except ElementTree.ParseError:
            return "unknown"
        return code if code in SAFE_ERROR_CODES else "unknown"
    code = payload.get("Code") or payload.get("code") if isinstance(payload, dict) else None
    return code if isinstance(code, str) and code in SAFE_ERROR_CODES else "unknown"


def missing_canned_policy(status: int, body: bytes) -> bool:
    """Recognize the pinned RustFS responses for an absent policy."""
    if status == 404 or response_error_code(body) in {"NoSuchCannedPolicy", "NoSuchPolicy"}:
        return True
    if status != 500 or response_error_code(body) != "InternalError":
        return False
    try:
        message = ElementTree.fromstring(body).findtext("Message") or ""
    except ElementTree.ParseError:
        return False
    return message.strip().lower() == "policy does not exist"


def read_policy(client, name: str) -> tuple[int, bytes, dict | None]:
    status, current = client.request("GET", "/rustfs/admin/v3/info-canned-policy", {"name": name})
    if status != 200:
        return status, current, None
    try:
        response = json.loads(current)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise PolicyBootstrapError(f"RustFS policy {name} returned an unrecognized document.") from None
    actual = response.get("policy", response) if isinstance(response, dict) else None
    if isinstance(actual, str):
        try:
            actual = json.loads(actual)
        except json.JSONDecodeError:
            actual = None
    return status, current, actual


def put_policy(client, name: str, document: dict, action: str) -> None:
    body = json.dumps(document, separators=(",", ":")).encode()
    status, _ = client.request("PUT", "/rustfs/admin/v3/add-canned-policy", {"name": name}, body)
    if status not in (200, 201, 204):
        raise PolicyBootstrapError(f"RustFS policy {name} could not be {action} (HTTP {status}).")


def ensure_policy(client, name: str, document: dict, previous: dict | None = None) -> str:
    """Create a missing policy, verify an existing one, or upgrade the exact previous definition.

    Any other existing content is refused and never overwritten.
    """
    status, current, actual = read_policy(client, name)
    if missing_canned_policy(status, current):
        put_policy(client, name, document, "created")
        return "created"
    if status != 200:
        raise PolicyBootstrapError(
            f"RustFS policy {name} could not be inspected (HTTP {status}, {response_error_code(current)})."
        )
    canonical = canonical_policy(actual)
    if canonical is not None and canonical == canonical_policy(document):
        return "already-present"
    if canonical is not None and previous is not None and canonical == canonical_policy(previous):
        put_policy(client, name, document, "updated")
        status, _, updated = read_policy(client, name)
        if status != 200 or canonical_policy(updated) != canonical_policy(document):
            raise PolicyBootstrapError(f"RustFS policy {name} could not be verified after update.")
        return "updated"
    raise PolicyBootstrapError(
        f"Existing RustFS policy {name} differs from the approved policy; no changes applied."
    )


def load_s3_client():
    spec = importlib.util.spec_from_file_location(
        "rustfs_bootstrap_buckets", ROOT / "infra/rustfs/bootstrap-buckets.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    buckets = load_s3_client()
    endpoint = os.environ.get("RUSTFS_S3_ENDPOINT", "http://127.0.0.1:9000")
    try:
        client = buckets.S3Client(
            endpoint, buckets.read_secret("rustfs-access-key"), buckets.read_secret("rustfs-secret-key")
        )
        for name, document in policy_documents().items():
            outcome = ensure_policy(client, name, document, previous_policy_document(name))
            print(f"RustFS policy {name}: {outcome}")
    except (PolicyBootstrapError, RuntimeError) as error:
        print(f"RustFS policy bootstrap failed: {error}", file=sys.stderr)
        return 1
    print("RustFS product-group policies verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
