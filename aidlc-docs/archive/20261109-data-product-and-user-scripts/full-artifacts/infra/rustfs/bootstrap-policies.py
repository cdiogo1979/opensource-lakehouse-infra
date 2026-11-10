#!/usr/bin/env python3
"""Converge the RustFS policies named after the Keycloak product groups.

RustFS maps each value of the OIDC ``groups`` claim to the policy of the same
name, so these policies define what each product group can do in the RustFS
console. The levels come from the data product files (BR-4): product policies
are rewritten when they differ, and ``role-platform-admin`` manages every
product bucket.

  bootstrap-policies.py [--product FILE ...] [--dry-run]     converge (default: every file)
  bootstrap-policies.py --remove --product FILE [--dry-run]  delete the product's policies
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra" / "products"))
import data_products  # noqa: E402

LEVELS = ("read", "read_write", "manage")
# Product file data levels -> RustFS bucket access; "none" grants no statement.
DATA_LEVEL_ACCESS = {"read": "read", "write": "read_write", "manage": "manage"}
PLATFORM_ADMIN_GROUP = data_products.PLATFORM_ADMIN_GROUP


def product_access_matrix(products: list) -> dict[str, dict[str, str]]:
    """Group -> bucket -> access level for every product, plus the platform administrator."""
    matrix: dict[str, dict[str, str]] = {}
    for product in products:
        for role in data_products.ROLES:
            matrix[product.groups[role]] = {
                env.bucket: DATA_LEVEL_ACCESS[product.access[role][env.key]]
                for env in product.environments
                if product.access[role][env.key] != "none"
            }
    # The platform administrator manages every product bucket.
    matrix[PLATFORM_ADMIN_GROUP] = {bucket: "manage" for product in products for bucket in product.buckets()}
    return matrix


PRODUCTS = data_products.load_all()
BUCKETS = tuple(bucket for product in PRODUCTS for bucket in product.buckets())
ACCESS_MATRIX = product_access_matrix(PRODUCTS)
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
    for bucket in [*BUCKETS, *sorted(set(access) - set(BUCKETS))]:
        if bucket in access:
            statements.extend(bucket_statements(bucket, access[bucket], level_actions))
    return {"Version": "2012-10-17", "Statement": statements}


def policy_document(group: str, matrix: dict | None = None) -> dict:
    return access_document((matrix or ACCESS_MATRIX)[group])


def previous_policy_document(group: str, matrix: dict | None = None) -> dict:
    return access_document((matrix or ACCESS_MATRIX)[group], PREVIOUS_ACCESS_LEVEL_ACTIONS)


def policy_documents(matrix: dict | None = None) -> dict[str, dict]:
    matrix = matrix or ACCESS_MATRIX
    return {group: policy_document(group, matrix) for group in matrix}


def effective_access(groups: set[str], matrix: dict | None = None) -> dict[str, str]:
    """Per-bucket highest access level across a user's product groups."""
    access: dict[str, str] = {}
    for group in groups:
        for bucket, level in (matrix or ACCESS_MATRIX)[group].items():
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


def ensure_policy(client, name: str, document: dict, previous: dict | None = None, *, converge: bool = False, dry_run: bool = False) -> str:
    """Create a missing policy, verify an existing one, or upgrade the exact previous definition.

    Other existing content is refused and never overwritten, unless ``converge``
    is set: product policies are owned by the product files and rewritten to
    match them (BR-4). ``dry_run`` reports the outcome without writing.
    """
    status, current, actual = read_policy(client, name)
    if missing_canned_policy(status, current):
        if not dry_run:
            put_policy(client, name, document, "created")
        return "created"
    if status != 200:
        raise PolicyBootstrapError(
            f"RustFS policy {name} could not be inspected (HTTP {status}, {response_error_code(current)})."
        )
    canonical = canonical_policy(actual)
    if canonical is not None and canonical == canonical_policy(document):
        return "already-present"
    if canonical is not None and (converge or (previous is not None and canonical == canonical_policy(previous))):
        if dry_run:
            return "updated"
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


def remove_policy(client, name: str, dry_run: bool) -> str:
    status, current, _ = read_policy(client, name)
    if missing_canned_policy(status, current):
        return "absent"
    if dry_run:
        return "removed"
    status, body = client.request("DELETE", "/rustfs/admin/v3/remove-canned-policy", {"name": name})
    if status not in (200, 204) and not missing_canned_policy(status, body):
        raise PolicyBootstrapError(f"RustFS policy {name} could not be removed (HTTP {status}).")
    return "removed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--product", type=Path, action="append", default=[])
    parser.add_argument("--remove", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.remove and len(args.product) != 1:
        parser.error("--remove needs exactly one --product")
    buckets = load_s3_client()
    endpoint = os.environ.get("RUSTFS_S3_ENDPOINT", "http://127.0.0.1:9000")
    prefix = "would be " if args.dry_run else ""
    try:
        selected, every = data_products.resolve_products(args.product, removal=args.remove)
        if args.remove and selected[0].protected:
            raise data_products.ProductError("The default data product cannot be removed.")
        client = buckets.S3Client(
            endpoint, buckets.read_secret("rustfs-access-key"), buckets.read_secret("rustfs-secret-key")
        )
        if args.remove:
            removed = selected[0]
            for name in removed.group_names():
                print(f"RustFS policy {name}: {prefix}{remove_policy(client, name, args.dry_run)}")
            remaining = data_products.remaining_products(every, removed)
            matrix = product_access_matrix(remaining)
        else:
            matrix = product_access_matrix(list({p.name: p for p in every + selected}.values()))
            for product in selected:
                for name in product.group_names():
                    outcome = ensure_policy(client, name, policy_document(name, matrix), converge=True, dry_run=args.dry_run)
                    print(f"RustFS policy {name}: {prefix}{outcome}")
        outcome = ensure_policy(client, PLATFORM_ADMIN_GROUP, policy_document(PLATFORM_ADMIN_GROUP, matrix), converge=True, dry_run=args.dry_run)
        print(f"RustFS policy {PLATFORM_ADMIN_GROUP}: {prefix}{outcome}")
    except data_products.ProductError as error:
        print(f"RustFS policy step refused: {error}", file=sys.stderr)
        return 2
    except (PolicyBootstrapError, RuntimeError) as error:
        print(f"RustFS policy bootstrap failed: {error}", file=sys.stderr)
        return 1
    print("RustFS product-group policies converged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
