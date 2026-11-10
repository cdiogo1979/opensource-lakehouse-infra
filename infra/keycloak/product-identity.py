#!/usr/bin/env python3
"""Apply, remove, or list the Keycloak objects of data products (FR-3, FR-11).

  product-identity.py [--product FILE ...] [--dry-run]          apply (default: every file)
  product-identity.py --remove --product FILE [--dry-run]       remove one product
  product-identity.py --inventory --product FILE                list the members of its groups
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "products")]
import data_products  # noqa: E402
import keycloak_products  # noqa: E402

SPEC = importlib.util.spec_from_file_location("bootstrap_realm", HERE / "bootstrap-realm.py")
realm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(realm)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--product", type=Path, action="append", default=[], help="Product file (repeatable; default: every file)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--remove", action="store_true", help="Remove the product's groups, client roles, and writer user")
    mode.add_argument("--inventory", action="store_true", help="Print the members of the product's groups as JSON")
    parser.add_argument("--dry-run", action="store_true")
    keycloak_products.add_admin_arguments(parser)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    args = parser.parse_args(argv)
    if (args.remove or args.inventory) and len(args.product) != 1:
        parser.error("--remove and --inventory need exactly one --product")
    operation_id = str(uuid.uuid4())
    try:
        products, _ = data_products.resolve_products(args.product, removal=args.remove or args.inventory)
        api = keycloak_products.platform_admin_session(realm, args.base_url, args)
        log = lambda line: print(f"  keycloak: {line}")  # noqa: E731
        if args.inventory:
            print(json.dumps(keycloak_products.product_members(api, products[0]), sort_keys=True))
            return 0
        if args.remove:
            if products[0].protected:
                raise data_products.ProductError("The default data product cannot be removed.")
            changes = keycloak_products.remove_product(api, products[0], log=log, dry_run=args.dry_run)
        else:
            changes = sum(keycloak_products.apply_product(api, product, log=log, dry_run=args.dry_run) for product in products)
        verb = "planned" if args.dry_run else "applied"
        print(f"Keycloak product identities {verb} (operation_id={operation_id}; products={len(products)}; changes={changes}).")
        return 0
    except (realm.BootstrapError, keycloak_products.KeycloakProductError, data_products.ProductError) as error:
        print(f"Keycloak product identity step failed (operation_id={operation_id}): {error}", file=sys.stderr)
        return 1 if not isinstance(error, data_products.ProductError) else 2


if __name__ == "__main__":
    raise SystemExit(main())
