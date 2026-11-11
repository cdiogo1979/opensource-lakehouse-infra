#!/usr/bin/env python3
"""Create, rotate, or remove the RustFS checkpoint key of every product environment bucket.

  bootstrap-checkpoint-keys.py [--product FILE ...] [--rotate] [--dry-run]   converge (default: every file)
  bootstrap-checkpoint-keys.py --remove --product FILE [--dry-run]
  bootstrap-checkpoint-keys.py --check-staged                                 every bucket has a staged key
  bootstrap-checkpoint-keys.py --list                                         the buckets, one per line

Each bucket gets the canned policy ``checkpoints-<bucket>`` (its ``checkpoints/``
prefix only) and the user ``ckpt-<bucket>`` with exactly that policy. The key is
stored in ``.runtime/credentials/checkpoint-keys/<bucket>`` (600) and staged for
container mounts in ``.runtime/container-mounts/checkpoint-keys/<bucket>`` (644).
The staged folder also holds ``.buckets.json`` (product -> environment -> bucket,
no secrets), which the Airflow DAG factory reads to mount a run's one key.
Secrets are never printed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra" / "products"))
import data_products  # noqa: E402

STORE = ROOT / ".runtime" / "credentials" / "checkpoint-keys"
STAGE = ROOT / ".runtime" / "container-mounts" / "checkpoint-keys"
INDEX = ".buckets.json"
BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
OBJECT_ACTIONS = ("s3:DeleteObject", "s3:GetObject", "s3:PutObject")


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "infra/rustfs" / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CheckpointKeyError(Exception):
    """A RustFS or file step failed; the message never holds a secret."""


def checked_bucket(bucket: str) -> str:
    if not BUCKET_PATTERN.fullmatch(bucket):
        raise CheckpointKeyError(f"Invalid bucket name {bucket!r}.")
    return bucket


def user_name(bucket: str) -> str:
    return f"ckpt-{checked_bucket(bucket)}"


def policy_name(bucket: str) -> str:
    return f"checkpoints-{checked_bucket(bucket)}"


def checkpoint_policy(bucket: str) -> dict:
    """Listing of ``checkpoints/`` and object read, write and delete below it, in this bucket only (R1)."""
    checked_bucket(bucket)
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{bucket}"],
                "Condition": {"StringLike": {"s3:prefix": ["checkpoints", "checkpoints/*"]}},
            },
            {"Effect": "Allow", "Action": list(OBJECT_ACTIONS), "Resource": [f"arn:aws:s3:::{bucket}/checkpoints/*"]},
        ],
    }


def product_buckets(products) -> list[str]:
    return [checked_bucket(env.bucket) for product in products for env in product.environments]


def _write(path: Path, text: str, mode: int, folder_mode: int) -> None:
    """Write through a temporary file in the same folder, then rename (R8, R9)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(folder_mode)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def read_stored(bucket: str, store: Path = STORE) -> dict | None:
    path = store / bucket
    if path.is_symlink() or not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    if not isinstance(value, dict) or set(value) != {"access_key", "secret_key"} or value["access_key"] != user_name(bucket):
        return None
    return value if isinstance(value["secret_key"], str) and value["secret_key"] else None


def write_key(bucket: str, key: dict, store: Path = STORE, stage: Path = STAGE) -> None:
    text = json.dumps(key, sort_keys=True)
    _write(store / bucket, text, 0o600, 0o700)
    _write(stage / bucket, text, 0o644, 0o755)


class Keys:
    """The RustFS admin steps for checkpoint keys; ``client`` signs with the root key on the host (R7)."""

    def __init__(self, client, policies, s3_client_class, store: Path = STORE, stage: Path = STAGE):
        self.client, self.policies, self.s3_client_class = client, policies, s3_client_class
        self.store, self.stage = store, stage

    def _admin(self, method: str, path: str, query: dict, body: bytes = b"", ok=(200, 204)) -> int:
        status, _ = self.client.request(method, f"/rustfs/admin/v3/{path}", query, body)
        if status not in ok:
            raise CheckpointKeyError(f"RustFS {path} failed (HTTP {status}).")
        return status

    def user_exists(self, bucket: str) -> bool:
        return self._admin("GET", "user-info", {"accessKey": user_name(bucket)}, ok=(200, 404)) == 200

    def authenticates(self, bucket: str, key: dict) -> bool:
        """A signed listing of ``checkpoints/`` with the stored key succeeds."""
        client = self.s3_client_class(self.client.endpoint, key["access_key"], key["secret_key"])
        status, _ = client.request("GET", f"/{bucket}", {"list-type": "2", "prefix": "checkpoints/", "max-keys": "1"})
        return status == 200

    def set_secret(self, bucket: str) -> dict:
        key = {"access_key": user_name(bucket), "secret_key": secrets.token_urlsafe(40)}
        body = json.dumps({"secretKey": key["secret_key"], "status": "enabled"}).encode()
        self._admin("PUT", "add-user", {"accessKey": key["access_key"]}, body)
        return key

    def ensure(self, bucket: str, *, rotate: bool = False, dry_run: bool = False) -> str:
        """Converge policy, user, attachment and files; ``created``, ``rotated`` or ``unchanged`` (R2 to R4)."""
        self.policies.ensure_policy(self.client, policy_name(bucket), checkpoint_policy(bucket), converge=True, dry_run=dry_run)
        stored = read_stored(bucket, self.store)
        exists = self.user_exists(bucket)
        if not exists:
            outcome = "created"
        elif rotate or stored is None or not self.authenticates(bucket, stored):
            outcome = "rotated"
        else:
            outcome = "unchanged"
        if dry_run:
            return outcome
        if outcome != "unchanged":
            # The secret changes in RustFS first; the files follow only after it succeeded.
            stored = self.set_secret(bucket)
            write_key(bucket, stored, self.store, self.stage)
        self._admin("PUT", "set-user-or-group-policy", {"policyName": policy_name(bucket), "userOrGroup": user_name(bucket), "isGroup": "false"})
        staged = self.stage / bucket
        if outcome == "unchanged" and (staged.is_symlink() or not staged.is_file() or staged.read_text(encoding="utf-8") != json.dumps(stored, sort_keys=True)):
            write_key(bucket, stored, self.store, self.stage)
        return outcome

    def remove(self, bucket: str, *, dry_run: bool = False) -> str:
        """User, then policy, then the files; absent items are not an error (R5)."""
        if dry_run:
            return "removed"
        self._admin("DELETE", "remove-user", {"accessKey": user_name(bucket)}, ok=(200, 204, 404))
        self.policies.remove_policy(self.client, policy_name(bucket), False)
        for path in (self.store / bucket, self.stage / bucket):
            path.unlink(missing_ok=True)
        return "removed"

    def prune_stage(self, buckets: list[str], *, dry_run: bool = False) -> list[str]:
        """Delete staged files of buckets no longer in the product model (R6)."""
        if not self.stage.is_dir():
            return []
        stale = sorted(path.name for path in self.stage.iterdir() if not path.name.startswith(".") and path.name not in buckets)
        if not dry_run:
            for name in stale:
                (self.stage / name).unlink()
        return stale


def write_index(products, stage: Path = STAGE) -> None:
    """Product -> environment -> bucket for the Airflow DAG factory; holds no secret."""
    index = {product.name: {env.key: checked_bucket(env.bucket) for env in product.environments} for product in products}
    _write(stage / INDEX, json.dumps(index, sort_keys=True), 0o644, 0o755)


def missing_staged(buckets: list[str], stage: Path = STAGE) -> list[str]:
    return [bucket for bucket in buckets if (stage / bucket).is_symlink() or not (stage / bucket).is_file()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--product", type=Path, action="append", default=[])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--remove", action="store_true")
    mode.add_argument("--rotate", action="store_true")
    mode.add_argument("--check-staged", action="store_true")
    mode.add_argument("--list", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.remove and len(args.product) != 1:
        parser.error("--remove needs exactly one --product")
    prefix = "would be " if args.dry_run else ""
    policies = _load("rustfs_bootstrap_policies", "bootstrap-policies.py")
    buckets_module = _load("rustfs_bootstrap_buckets", "bootstrap-buckets.py")
    try:
        selected, every = data_products.resolve_products(args.product, removal=args.remove)
        if args.list:
            print("\n".join(product_buckets(selected)))
            return 0
        if args.check_staged:
            missing = missing_staged(product_buckets(every))
            if missing:
                print(f"Checkpoint keys are not staged for: {', '.join(missing)}. Run the product bootstrap "
                      "(scripts/bootstrap-default-product.sh or scripts/operations/create-data-product.sh).", file=sys.stderr)
                return 1
            return 0
        if args.remove and selected[0].protected:
            raise data_products.ProductError("The default data product cannot be removed.")
        endpoint = os.environ.get("RUSTFS_S3_ENDPOINT", "http://127.0.0.1:9000")
        client = buckets_module.S3Client(endpoint, buckets_module.read_secret("rustfs-access-key"), buckets_module.read_secret("rustfs-secret-key"))
        keys = Keys(client, policies, buckets_module.S3Client)
        for bucket in product_buckets(selected):
            outcome = keys.remove(bucket, dry_run=args.dry_run) if args.remove else keys.ensure(bucket, rotate=args.rotate, dry_run=args.dry_run)
            print(f"Checkpoint key {bucket}: {prefix}{outcome}")
        remaining = product_buckets(data_products.remaining_products(every, selected[0]) if args.remove else every)
        if args.remove or not args.product:
            for name in keys.prune_stage(remaining, dry_run=args.dry_run):
                print(f"Staged checkpoint key {name}: {prefix}removed (no longer in the product model)")
        if not args.dry_run:
            write_index(data_products.remaining_products(every, selected[0]) if args.remove else list({p.name: p for p in every + selected}.values()))
        if args.rotate and not args.dry_run:
            print("Restart the Airflow runs and Jupyter servers that use the rotated keys; the old secrets are refused now.")
    except data_products.ProductError as error:
        print(f"Checkpoint key step refused: {error}", file=sys.stderr)
        return 2
    except (CheckpointKeyError, policies.PolicyBootstrapError, RuntimeError) as error:
        print(f"Checkpoint key step failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
