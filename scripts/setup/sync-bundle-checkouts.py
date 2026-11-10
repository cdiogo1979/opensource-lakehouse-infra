#!/usr/bin/env python3
"""Bring existing Airflow bundle checkouts in line with the configured sparse_dirs.

Airflow's GitDagBundle applies ``sparse_dirs`` only when it first clones a
bundle's ``tracking_repo``; an existing checkout keeps its old directory list, so a
newly added directory (such as ``workflows``) would never appear. Run by
``scripts/lakehouse.sh start-airflow`` before Airflow starts. It touches only the
``tracking_repo`` of each configured product bundle, and only when its sparse list
differs. Per-commit ``versions/`` copies are created fresh by Airflow.

  sync-bundle-checkouts.py [--root DIR] [--dry-run]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "infra" / "products"))
import data_products  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BUNDLE_ROOT = ROOT / ".runtime" / "airflow-dag-bundles"


def git(checkout: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(checkout), *args], capture_output=True, text=True, check=False)


def sync(root: Path, bundles: list[str], wanted: list[str], dry_run: bool = False) -> list[str]:
    """The bundles whose tracking checkout was (or, with dry_run, would be) updated."""
    changed = []
    for name in bundles:
        checkout = root / name / "tracking_repo"
        if not (checkout / ".git").exists():
            continue  # not cloned yet: Airflow clones it with the current sparse_dirs
        current = git(checkout, "sparse-checkout", "list")
        if current.returncode == 0 and sorted(current.stdout.split()) == sorted(wanted):  # cone mode lists them sorted
            continue
        changed.append(name)
        if dry_run:
            continue
        result = git(checkout, "sparse-checkout", "set", "--cone", *wanted)
        if result.returncode:
            raise RuntimeError(f"Bundle {name}: git sparse-checkout set failed: {result.stderr.strip()[:200]}")
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=BUNDLE_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        bundles = [bundle["name"] for bundle in data_products.bundle_config(data_products.load_all())]
        changed = sync(args.root, bundles, list(data_products.BUNDLE_KWARGS["sparse_dirs"]), args.dry_run)
    except (data_products.ProductError, RuntimeError, OSError) as error:
        print(f"Bundle checkouts not synchronized: {error}", file=sys.stderr)
        return 1
    verb = "would update" if args.dry_run else "updated"
    print(f"Bundle checkouts: {verb} {', '.join(changed)}." if changed else "Bundle checkouts match the configured directories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
