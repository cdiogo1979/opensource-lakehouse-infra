#!/usr/bin/env python3
"""Render the Jenkins configuration-as-code file with every data product's groups.

Jenkins' matrix authorization has no wildcard group entries, so the static
template (infra/jenkins/casc/jenkins.yaml: platform admin and break-glass) is
extended with one entry per product role listed in apps.jenkins, in product and
role order. The output is deterministic: an unchanged product set renders the
same bytes, so the caller restarts Jenkins only when the file changed (BR-6).

  render_jenkins.py [--output FILE] [--check] [--exclude NAME]

--exclude leaves out one product (a removal renders before its file is deleted).

Exit codes: 0 unchanged, 3 written (changed), 2 invalid product files (the
existing output is left untouched), 1 other failures.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_products  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "infra" / "jenkins" / "casc" / "jenkins.yaml"
OUTPUT = ROOT / ".runtime" / "container-mounts" / "jenkins-casc.yaml"
HEADER = "# Rendered by infra/products/render_jenkins.py from infra/jenkins/casc/jenkins.yaml\n# and the data product files. Do not edit; edit the template or a product file.\n"


def product_entries(products: list) -> list[dict]:
    return [
        {"group": {"name": product.groups[role], "permissions": list(permissions)}}
        for product in products
        for role, permissions in product.jenkins.items()
    ]


def render(template_text: str, products: list) -> str:
    document = yaml.safe_load(template_text)
    entries = document["jenkins"]["authorizationStrategy"]["globalMatrix"]["entries"]
    static = {entry["group"]["name"] for entry in entries}
    clash = static & {entry["group"]["name"] for entry in product_entries(products)}
    if clash:
        raise data_products.ProductError(f"Product groups collide with static Jenkins entries: {', '.join(sorted(clash))}")
    entries.extend(product_entries(products))
    return HEADER + yaml.safe_dump(document, sort_keys=False, default_flow_style=False, width=1000)


def write_if_changed(path: Path, text: str) -> bool:
    if path.is_file() and not path.is_symlink() and path.read_text(encoding="utf-8") == text:
        return False
    if path.is_file() and not path.is_symlink():
        # Rewrite in place: Jenkins bind-mounts this file, and a file bind mount
        # keeps the old inode, so an atomic replace would never reach the container.
        with path.open("r+", encoding="utf-8") as stream:
            stream.write(text)
            stream.truncate()
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(text)
    os.chmod(temporary, 0o644)
    os.replace(temporary, path)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true", help="report whether the output would change, without writing")
    parser.add_argument("--exclude", help="leave out this product")
    args = parser.parse_args(argv)
    try:
        products = [p for p in data_products.load_all() if p.name != args.exclude]
        text = render(TEMPLATE.read_text(encoding="utf-8"), products)
    except data_products.ProductError as error:
        print(f"Jenkins configuration not rendered (the running Jenkins keeps its file): {error}", file=sys.stderr)
        return 2
    except (OSError, yaml.YAMLError, KeyError, TypeError) as error:
        print(f"Jenkins configuration render failed ({type(error).__name__}).", file=sys.stderr)
        return 1
    current = args.output.read_text(encoding="utf-8") if args.output.is_file() else None
    if current == text:
        print("Jenkins configuration unchanged.")
        return 0
    if args.check:
        print("Jenkins configuration would change.")
        return 3
    write_if_changed(args.output, text)
    print(f"Jenkins configuration rendered to {args.output.relative_to(ROOT) if args.output.is_relative_to(ROOT) else args.output}.")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
