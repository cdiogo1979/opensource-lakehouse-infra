#!/usr/bin/env python3
"""Create one enabled lakehouse realm user with no groups (FR-9).

The password is the first line of --password-file, or the documented default
(``ChangeM3!``, permanent). It travels only in the request body and is never
printed. Group assignment is done in the Keycloak admin console.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "products")]
import keycloak_products  # noqa: E402

SPEC = importlib.util.spec_from_file_location("bootstrap_realm", HERE / "bootstrap-realm.py")
realm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(realm)

USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{1,62}$")
RESERVED_PREFIXES = ("srv-", "service-account-")
RESERVED_USERNAMES = frozenset({"admin", "jenkins-break-glass"})
NAME_PATTERN = re.compile(r"^[^\x00-\x1f<>]{1,64}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,}$")


class UserError(Exception):
    """A validation failure (exit 2)."""


def validate(username: str, email: str | None, first: str | None, last: str | None) -> None:
    if not USERNAME_PATTERN.fullmatch(username):
        raise UserError("Username must be 2-63 characters of lowercase letters, digits, '.', '_' or '-'.")
    if username.startswith(RESERVED_PREFIXES) or username in RESERVED_USERNAMES:
        raise UserError(f"Username {username!r} is reserved for service or break-glass accounts.")
    if email is not None and not EMAIL_PATTERN.fullmatch(email):
        raise UserError("Email is not a valid address.")
    for label, value in (("first name", first), ("last name", last)):
        if value is not None and not NAME_PATTERN.fullmatch(value):
            raise UserError(f"The {label} must be 1-64 printable characters.")


def read_password(path: Path | None) -> str:
    if path is None:
        return realm.load_bootstrap_identities()["default_password"]
    if path.is_symlink() or not path.is_file():
        raise UserError("The password file is unavailable.")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0]:
        raise UserError("The password file is empty.")
    return lines[0]


def representation(username: str, email: str | None, first: str | None, last: str | None, password: str) -> dict:
    user = {
        "username": username,
        "enabled": True,
        "emailVerified": True,
        "email": email or f"{username}@lakehouse.local",
        "requiredActions": [],
        "groups": [],
        "credentials": [{"type": "password", "value": password, "temporary": False}],
    }
    if first:
        user["firstName"] = first
    if last:
        user["lastName"] = last
    return user


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("username")
    parser.add_argument("--email")
    parser.add_argument("--first-name")
    parser.add_argument("--last-name")
    parser.add_argument("--password-file", type=Path, help="First line is the password (default: ChangeM3!)")
    keycloak_products.add_admin_arguments(parser)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    args = parser.parse_args(argv)
    operation_id = str(uuid.uuid4())
    try:
        validate(args.username, args.email, args.first_name, args.last_name)
        password = read_password(args.password_file)
        api = keycloak_products.platform_admin_session(realm, args.base_url, args)
        if realm.find_user(api, args.username):
            print(f"User {args.username!r} already exists; nothing changed (operation_id={operation_id}).", file=sys.stderr)
            return 1
        status, _ = api.request("POST", f"/admin/realms/{realm.REALM}/users", representation(args.username, args.email, args.first_name, args.last_name, password))
        realm.checked(status, (201,), f"Create user {args.username}")
        source = "the password file" if args.password_file else "the default password"
        print(f"Created user {args.username} with {source}, no groups (operation_id={operation_id}).")
        print("Next: add the user to product groups in the Keycloak admin console (http://keycloak.localhost:8080/admin/lakehouse/console/).")
        print("Polaris and StarRocks follow within five minutes, or now with: python3 infra/polaris/reconcile-keycloak-groups.py && scripts/lakehouse.sh reconcile-starrocks")
        return 0
    except UserError as error:
        print(f"Create user refused: {error}", file=sys.stderr)
        return 2
    except (realm.BootstrapError, keycloak_products.KeycloakProductError) as error:
        print(f"Create user failed (operation_id={operation_id}): {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
