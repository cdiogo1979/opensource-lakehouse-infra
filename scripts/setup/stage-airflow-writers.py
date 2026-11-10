#!/usr/bin/env python3
"""Stage the per-product writer credentials for the Airflow token broker only.

For every data product with a `repo`, the broker may issue tokens for that
product's writer user. This writes `.runtime/container-mounts/airflow-writers/`:
`writers.json` (product -> username, writer group, password file name; no
secrets) and one password file per writer, copied from `writer_user.password_file`.
Only the broker mounts the directory (read-only). Staged files of products that
no longer have a repo are removed. Prints the fingerprint of the bundle list and
the writer set (``--fingerprint`` prints only that), never a password.

``--fingerprint`` and ``--list`` (the bundle names) stage nothing and accept
``--exclude NAME``, so an operator dry run can preview a product's removal. A
writer password file that does not exist yet (a product not applied) counts as
empty there: the fingerprint still differs, which is all a preview needs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra" / "products"))
import data_products  # noqa: E402

STAGE = ROOT / ".runtime" / "container-mounts" / "airflow-writers"


def writer_set(products: list) -> dict[str, dict]:
    return {
        product.name: {
            "username": product.writer_user.username,
            "group": product.groups["writer"],
            "password_file": f"{product.writer_user.username}-password",
        }
        for product in products
        if product.repo is not None
    }


def read_password(product, preview: bool = False) -> str:
    path = ROOT / product.writer_user.password_file
    if preview and not path.exists():
        return ""
    if path.is_symlink() or not path.is_file():
        raise data_products.ProductError(
            f"The writer password file of {product.name} is unavailable ({product.writer_user.password_file}); apply the product first.")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0]:
        raise data_products.ProductError(f"The writer password file of {product.name} is empty.")
    return lines[0]


def fingerprint(products: list, writers: dict[str, dict], passwords: dict[str, str]) -> str:
    digest = hashlib.sha256()
    digest.update(json.dumps(data_products.bundle_config(products), sort_keys=True).encode())
    digest.update(json.dumps(writers, sort_keys=True).encode())
    for product in sorted(passwords):
        digest.update(hashlib.sha256(passwords[product].encode()).digest())
    return digest.hexdigest()


def write_file(path: Path, content: str) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(content)
    os.chmod(temporary, 0o644)
    os.replace(temporary, path)


def stage(products: list) -> str:
    writers = writer_set(products)
    passwords = {name: read_password(next(p for p in products if p.name == name)) for name in writers}
    STAGE.mkdir(parents=True, exist_ok=True)
    STAGE.chmod(0o755)
    wanted = {"writers.json"} | {entry["password_file"] for entry in writers.values()}
    for stale in STAGE.iterdir():
        if stale.name not in wanted and not stale.name.startswith("."):
            stale.unlink()
    write_file(STAGE / "writers.json", json.dumps(writers, indent=1, sort_keys=True) + "\n")
    for name, entry in writers.items():
        write_file(STAGE / entry["password_file"], passwords[name] + "\n")
    return fingerprint(products, writers, passwords)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fingerprint", action="store_true", help="print only the fingerprint, without staging")
    mode.add_argument("--list", action="store_true", help="print the bundle names, without staging")
    parser.add_argument("--exclude", action="append", default=[], metavar="NAME", help="leave a product out (previews only)")
    args = parser.parse_args(argv)
    if args.exclude and not (args.fingerprint or args.list):
        parser.error("--exclude is for --fingerprint and --list only")
    try:
        products = [p for p in data_products.load_all() if p.name not in args.exclude]
        if args.list:
            print("\n".join(bundle["name"] for bundle in data_products.bundle_config(products)))
            return 0
        if args.fingerprint:
            writers = writer_set(products)
            passwords = {name: read_password(next(p for p in products if p.name == name), preview=True) for name in writers}
            print(fingerprint(products, writers, passwords))
            return 0
        print(stage(products))
        return 0
    except data_products.ProductError as error:
        print(f"Airflow writers not staged: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
