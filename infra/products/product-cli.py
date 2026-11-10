#!/usr/bin/env python3
"""Product model operations for the operator scripts (no network calls).

  product-cli.py init NAME                 write data-products/NAME.yaml from the template
  product-cli.py validate FILE             schema, collisions, locked names (BR-1)
  product-cli.py record (FILE | --all)     write the applied-names state
  product-cli.py resolve NAME              refuse default/unknown; print the product file path
  product-cli.py summarize NAME MEMBERS POLARIS STORAGE [STARROCKS]
                                           print the removal inventory; exit 10 if data exists
  product-cli.py backup NAME               copy the file and state to .runtime/backups/
  product-cli.py forget NAME               delete the file and state (the last removal step)

Exit codes: 0 success, 1 failure, 2 refusal or invalid input, 10 data present.
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_products as dp  # noqa: E402

BACKUPS = dp.ROOT / ".runtime" / "backups"


def display(path: Path) -> str:
    """A path relative to the repository when it is inside it."""
    path = Path(path).resolve()
    return str(path.relative_to(dp.ROOT)) if path.is_relative_to(dp.ROOT) else str(path)


def in_products_dir(path: Path) -> Path:
    path = Path(path).resolve()
    if path.parent != dp.PRODUCTS_DIR.resolve():
        raise dp.ProductError(f"Product files must live in {display(dp.PRODUCTS_DIR)}/; got {display(path)}.")
    return path


def cmd_init(name: str) -> int:
    path = dp.product_file(name)
    if path.exists():
        raise dp.ProductError(f"{display(path)} already exists; edit it and apply it instead.")
    text = dp.render_template(name)
    candidate = dp.parse_product(__import__("yaml").safe_load(text), path.name)
    dp.check_collisions(dp.load_all() + [candidate])
    path.write_text(text, encoding="utf-8")
    print(f"Wrote {display(path)}. Review it, then apply it with:")
    print(f"  scripts/operations/create-data-product.sh {display(path)}")
    return 0


def cmd_validate(file: str) -> int:
    path = in_products_dir(Path(file))
    product = dp.load_product(path)
    dp.check_collisions(dp.load_all())
    dp.check_locked_names(product, dp.read_state(product.name))
    state = "re-apply" if dp.read_state(product.name) else "first apply"
    print(f"Product {product.name}: file valid ({state}).")
    return 0


def cmd_record(args: list[str]) -> int:
    products = dp.load_all() if args == ["--all"] else [dp.load_product(in_products_dir(Path(args[0])))]
    for product in products:
        dp.write_state(product)
    print(f"Applied state recorded for {', '.join(p.name for p in products)}.")
    return 0


def cmd_resolve(name: str) -> int:
    dp.validate_name(name)
    if name == dp.DEFAULT_PRODUCT:
        raise dp.ProductError("The default data product cannot be removed.")
    path = dp.product_file(name)
    if not path.exists() and dp.read_state(name) is None:
        raise dp.ProductError(f"Unknown data product {name!r}: no file and no applied state.")
    print(path)
    return 0


def _read_json(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8") or "{}")
    except (OSError, json.JSONDecodeError) as error:
        raise dp.ProductError(f"An inventory step produced no readable result ({Path(path).name}).") from error


def cmd_summarize(name: str, members: str, polaris: str, storage: str, starrocks: str | None = None) -> int:
    member_map = _read_json(members)
    tables = _read_json(polaris)
    objects = _read_json(storage)
    mvs = _read_json(starrocks) if starrocks else {}
    print(f"Data product {name}:")
    data = 0
    for env in dp.ENVIRONMENTS:
        polaris_count = sum((tables.get(env) or {}).values())
        data += polaris_count + int(objects.get(env, 0)) + int(mvs.get(env, 0))
        print(f"  {env}: {polaris_count} Polaris tables/views, {objects.get(env, 0)} bucket object versions, "
              f"{mvs.get(env, 0) if starrocks else 'n/a'} StarRocks MV-database objects")
    people = sorted({user for users in member_map.values() for user in users})
    print(f"  members who lose access: {', '.join(people) if people else 'none'}")
    return 10 if data else 0


def cmd_backup(name: str) -> int:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = BACKUPS / f"{stamp}-remove-{dp.validate_name(name)}"
    target.mkdir(parents=True, mode=0o700)
    for source in (dp.product_file(name), dp.state_path(name)):
        if source.exists():
            shutil.copy2(source, target / source.name)
    print(target)
    return 0


def cmd_forget(name: str) -> int:
    if dp.validate_name(name) == dp.DEFAULT_PRODUCT:
        raise dp.ProductError("The default data product cannot be removed.")
    for path in (dp.product_file(name), dp.state_path(name)):
        if path.exists():
            path.unlink()
    print(f"Deleted the product file and applied state of {name}.")
    return 0


COMMANDS = {
    "init": (cmd_init, (1,)),
    "validate": (cmd_validate, (1,)),
    "resolve": (cmd_resolve, (1,)),
    "summarize": (cmd_summarize, (4, 5)),
    "backup": (cmd_backup, (1,)),
    "forget": (cmd_forget, (1,)),
}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    command, args = argv[0], argv[1:]
    try:
        if command == "record" and len(args) == 1:
            return cmd_record(args)
        handler, arity = COMMANDS.get(command, (None, ()))
        if handler is None or len(args) not in arity:
            print(__doc__, file=sys.stderr)
            return 2
        return handler(*args)
    except dp.ProductError as error:
        print(f"Refused: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"Failed: {type(error).__name__} on a product file.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
