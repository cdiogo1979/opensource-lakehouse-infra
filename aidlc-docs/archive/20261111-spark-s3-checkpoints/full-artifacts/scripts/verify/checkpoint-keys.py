#!/usr/bin/env python3
"""Verify every staged checkpoint key against RustFS (s3-checkpoints FR-4, FR-6).

Each key may list, write, read and delete only below ``checkpoints/`` of its own
bucket. Its bucket's other prefixes, every other product bucket (including another
product's, the cross-product misuse case) and the bucket list are refused.
Only status codes are printed; keys and object contents never are.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checks(bucket: str, others: list[str]) -> list[tuple[str, str, str, dict | None, bytes, tuple[int, ...]]]:
    """(label, method, path, query, body, allowed statuses) for one key."""
    probe = "checkpoints/_verify-key/probe"
    cases = [
        ("own checkpoints/ write", "PUT", f"/{bucket}/{probe}", None, b"probe", (200,)),
        ("own checkpoints/ read", "GET", f"/{bucket}/{probe}", None, b"", (200,)),
        ("own checkpoints/ list", "GET", f"/{bucket}", {"list-type": "2", "prefix": "checkpoints/"}, b"", (200,)),
        ("own checkpoints/ delete", "DELETE", f"/{bucket}/{probe}", None, b"", (204,)),
        ("own bucket, other prefix write", "PUT", f"/{bucket}/_verify-outside/probe", None, b"probe", (403,)),
        ("own bucket, whole listing", "GET", f"/{bucket}", {"list-type": "2"}, b"", (403,)),
        ("bucket list", "GET", "/", None, b"", (403,)),
    ]
    for other in others:
        cases.append((f"{other} checkpoints/ write", "PUT", f"/{other}/{probe}", None, b"probe", (403,)))
    return cases


def main() -> int:
    keys_module = _load("rustfs_checkpoint_keys", "infra/rustfs/bootstrap-checkpoint-keys.py")
    buckets_module = _load("rustfs_bootstrap_buckets", "infra/rustfs/bootstrap-buckets.py")
    endpoint = os.environ.get("RUSTFS_S3_ENDPOINT", "http://127.0.0.1:9000")
    every = keys_module.product_buckets(keys_module.data_products.load_all())
    failures = 0
    for bucket in every:
        staged = keys_module.STAGE / bucket
        if staged.is_symlink() or not staged.is_file():
            print(f"FAIL {bucket}: no staged key")
            failures += 1
            continue
        key = json.loads(staged.read_text(encoding="utf-8"))
        client = buckets_module.S3Client(endpoint, key["access_key"], key["secret_key"])
        for label, method, path, query, body, allowed in checks(bucket, [b for b in every if b != bucket]):
            status, _ = client.request(method, path, query, body)
            verdict = "OK  " if status in allowed else "FAIL"
            failures += verdict == "FAIL"
            print(f"{verdict} {bucket}: {label} -> {status}")
    print("Checkpoint keys verified." if not failures else f"{failures} checkpoint key check(s) failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
