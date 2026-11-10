"""Keycloak objects of one data product: groups, Polaris client roles, and the writer user.

Used by ``bootstrap-realm.py`` (every product file, before the bootstrap users)
and by ``product-identity.py`` (one product: apply, remove, or list members).
``api`` is any object with ``request(method, path, payload=None, *, query=None)``
returning ``(status, body)``, such as ``bootstrap-realm.KeycloakAdmin``.
"""

from __future__ import annotations

import getpass
import json
import os
import sys
import tempfile
import urllib.parse
from pathlib import Path
from typing import Callable

REALM = "lakehouse"
POLARIS_CLIENT_ID = "polaris"
PLATFORM_ADMIN_GROUP = "role-platform-admin"
STARROCKS_SERVICE_CLIENT_ID = "srv-starrocks"
STARROCKS_SERVICE_USER = "service-account-srv-starrocks"
ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_USERS_FILE = Path(__file__).with_name("bootstrap-users.json")
EMAIL_DOMAIN = "lakehouse.local"

Log = Callable[[str], None]


class KeycloakProductError(Exception):
    """Safe operator-facing failure; response bodies and passwords are omitted."""


# ---- platform-admin sign-in for the operator scripts (CR-4) ----

ADMIN_PASSWORD_ENV = "LAKEHOUSE_ADMIN_PASSWORD"
DEFAULT_ADMIN_USER = "platform-admin"


def add_admin_arguments(parser) -> None:
    parser.add_argument("--admin-user", default=DEFAULT_ADMIN_USER, help="platform administrator in the lakehouse realm (default: platform-admin)")
    parser.add_argument("--admin-password-file", type=Path,
                        help=f"first line is the admin's password; otherwise ${ADMIN_PASSWORD_ENV}, otherwise a hidden prompt")


def admin_password(args) -> str:
    """The platform administrator's password: file, then environment, then a hidden prompt; never an argument."""
    if args.admin_password_file is not None:
        path = Path(args.admin_password_file)
        if path.is_symlink() or not path.is_file():
            raise KeycloakProductError("The admin password file is unavailable.")
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines or not lines[0]:
            raise KeycloakProductError("The admin password file is empty.")
        return lines[0]
    if os.environ.get(ADMIN_PASSWORD_ENV):
        return os.environ[ADMIN_PASSWORD_ENV]
    if not sys.stdin.isatty():
        raise KeycloakProductError(f"No admin password: pass --admin-password-file or set {ADMIN_PASSWORD_ENV}.")
    return getpass.getpass(f"Keycloak password for {args.admin_user}: ")


def require_platform_admin(api, username: str) -> None:
    """Refuse unless the signed-in user is a direct member of role-platform-admin."""
    status, _ = api.request("GET", f"/admin/realms/{REALM}/users", query={"username": username, "exact": "true"})
    if status in (401, 403):
        raise KeycloakProductError(f"User {username!r} has no admin rights in the lakehouse realm; sign in as a member of {PLATFORM_ADMIN_GROUP}.")
    user = find_user(api, username)
    if user is None:
        raise KeycloakProductError(f"User {username!r} was not found in the lakehouse realm.")
    status, groups = api.request("GET", f"/admin/realms/{REALM}/users/{user['id']}/groups")
    checked(status, (200,), "Admin group lookup")
    if not any(group.get("name") == PLATFORM_ADMIN_GROUP for group in groups or []):
        raise KeycloakProductError(f"User {username!r} is not a member of {PLATFORM_ADMIN_GROUP}; refusing to continue.")


def platform_admin_session(realm_module, base_url: str, args):
    """Sign in to the lakehouse realm as the given platform administrator and check membership."""
    api = realm_module.KeycloakAdmin(base_url, args.admin_user, admin_password(args), login_realm=REALM)
    api.login()
    require_platform_admin(api, args.admin_user)
    return api


def checked(status: int, expected: tuple[int, ...], action: str) -> None:
    if status not in expected:
        raise KeycloakProductError(f"{action} failed with HTTP {status}.")


def quote(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def bootstrap_identities() -> dict:
    return json.loads(BOOTSTRAP_USERS_FILE.read_text(encoding="utf-8"))


def find_group(api, name: str) -> dict | None:
    status, items = api.request("GET", f"/admin/realms/{REALM}/groups", query={"search": name, "briefRepresentation": "true", "exact": "true"})
    checked(status, (200,), "Group lookup")
    matches = [item for item in items or [] if item.get("name") == name]
    if len(matches) > 1:
        raise KeycloakProductError(f"Ambiguous Keycloak group {name!r}.")
    return matches[0] if matches else None


def find_client(api, client_id: str) -> dict:
    status, items = api.request("GET", f"/admin/realms/{REALM}/clients", query={"clientId": client_id})
    checked(status, (200,), f"Client lookup {client_id}")
    matches = [item for item in items or [] if item.get("clientId") == client_id]
    if len(matches) != 1:
        raise KeycloakProductError(f"Expected one Keycloak client {client_id!r}; run the realm bootstrap first.")
    return matches[0]


def find_client_role(api, client_uuid: str, name: str) -> dict | None:
    status, role = api.request("GET", f"/admin/realms/{REALM}/clients/{client_uuid}/roles/{quote(name)}")
    if status == 404:
        return None
    checked(status, (200,), f"Client role lookup {name}")
    return role


def find_user(api, username: str) -> dict | None:
    status, users = api.request("GET", f"/admin/realms/{REALM}/users", query={"username": username, "exact": "true"})
    checked(status, (200,), "User lookup")
    matches = [item for item in users or [] if item.get("username") == username]
    if len(matches) > 1:
        raise KeycloakProductError(f"Expected one Keycloak user named {username!r}; found {len(matches)}.")
    return matches[0] if matches else None


def group_members(api, group_id: str) -> list[str]:
    members: list[str] = []
    first = 0
    while True:
        status, page = api.request("GET", f"/admin/realms/{REALM}/groups/{group_id}/members", query={"first": first, "max": 500, "briefRepresentation": "true"})
        checked(status, (200,), "Group member lookup")
        page = page or []
        members.extend(item.get("username") for item in page if item.get("username"))
        if len(page) < 500:
            return members
        first += len(page)


class Planner:
    """Applies changes, or only reports them with dry_run; every change is logged by name."""

    def __init__(self, api, log: Log, dry_run: bool) -> None:
        self.api = api
        self.log = log
        self.dry_run = dry_run
        self.changes = 0

    def change(self, description: str, method: str, path: str, payload: object | None, expected: tuple[int, ...]) -> None:
        self.changes += 1
        self.log(("would " if self.dry_run else "") + description)
        if not self.dry_run:
            status, _ = self.api.request(method, path, payload)
            checked(status, expected, description)

    def ensure_group(self, name: str) -> dict | None:
        current = find_group(self.api, name)
        if current is None:
            self.change(f"create group {name}", "POST", f"/admin/realms/{REALM}/groups", {"name": name, "attributes": {}}, (201,))
            current = None if self.dry_run else find_group(self.api, name)
            if current is None and not self.dry_run:
                raise KeycloakProductError(f"Created group {name!r} could not be read back.")
        return current

    def ensure_client_role(self, client_uuid: str, name: str) -> dict | None:
        role = find_client_role(self.api, client_uuid, name)
        if role is None:
            self.change(
                f"create Polaris client role {name}", "POST", f"/admin/realms/{REALM}/clients/{client_uuid}/roles",
                {"name": name, "description": "Lakehouse product entitlement"}, (201,),
            )
            role = None if self.dry_run else find_client_role(self.api, client_uuid, name)
        return role

    def map_role(self, group: dict | None, group_name: str, client_uuid: str, role: dict | None, role_name: str) -> None:
        if group is not None and role is not None:
            status, current = self.api.request("GET", f"/admin/realms/{REALM}/groups/{group['id']}/role-mappings/clients/{client_uuid}")
            checked(status, (200,), "Group role lookup")
            if any(item.get("id") == role.get("id") for item in current or []):
                return
        self.change(
            f"map client role {role_name} to group {group_name}", "POST",
            f"/admin/realms/{REALM}/groups/{(group or {}).get('id')}/role-mappings/clients/{client_uuid}", [role], (204,),
        )

    def add_member(self, user: dict | None, username: str, group: dict | None, group_name: str) -> None:
        if user is not None and group is not None:
            status, memberships = self.api.request("GET", f"/admin/realms/{REALM}/users/{user['id']}/groups")
            checked(status, (200,), "User group lookup")
            if any(item.get("id") == group.get("id") for item in memberships or []):
                return
        self.change(
            f"add {username} to group {group_name}", "PUT",
            f"/admin/realms/{REALM}/users/{(user or {}).get('id')}/groups/{(group or {}).get('id')}", None, (204,),
        )


def write_password_file(relative: str, password: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise KeycloakProductError(f"Refusing to write the password file through a symlink: {path.name}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(password + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def writer_representation(product, password: str) -> dict:
    return {
        "username": product.writer_user.username,
        "enabled": True,
        "emailVerified": True,
        "firstName": product.name.capitalize(),
        "lastName": "Writer",
        "email": f"{product.writer_user.username}@{EMAIL_DOMAIN}",
        "requiredActions": [],
        "credentials": [{"type": "password", "value": password, "temporary": False}],
    }


def apply_product(api, product, *, log: Log = print, dry_run: bool = False, create_writer: bool = True) -> int:
    """Create what is missing for one product (BR-5); existing users are never changed."""
    plan = Planner(api, log, dry_run)
    polaris = find_client(api, POLARIS_CLIENT_ID)["id"]
    groups = {name: plan.ensure_group(name) for name in product.group_names()}
    roles = {name: plan.ensure_client_role(polaris, name) for name in product.group_names()}
    for name in product.group_names():
        plan.map_role(groups[name], name, polaris, roles[name], name)

    admin_group = find_group(api, PLATFORM_ADMIN_GROUP)
    if admin_group is None:
        raise KeycloakProductError("The role-platform-admin group is missing; run the realm bootstrap first.")
    owner = product.groups["owner"]
    plan.map_role(admin_group, PLATFORM_ADMIN_GROUP, polaris, roles[owner], owner)

    service = find_client(api, STARROCKS_SERVICE_CLIENT_ID)
    status, service_user = api.request("GET", f"/admin/realms/{REALM}/clients/{service['id']}/service-account-user")
    checked(status, (200,), "StarRocks service account lookup")
    writer_group = product.groups["writer"]
    plan.add_member(service_user, STARROCKS_SERVICE_USER, groups[writer_group], writer_group)

    username = product.writer_user.username
    user = find_user(api, username)
    bootstrap_users = {item["username"] for item in bootstrap_identities()["users"]}
    if user is None and create_writer and username not in bootstrap_users:
        password = bootstrap_identities()["default_password"]
        plan.changes += 1
        log(("would " if dry_run else "") + f"create writer user {username} (password file {product.writer_user.password_file})")
        if not dry_run:
            write_password_file(product.writer_user.password_file, password)
            status, _ = api.request("POST", f"/admin/realms/{REALM}/users", writer_representation(product, password))
            checked(status, (201,), f"Create writer user {username}")
            user = find_user(api, username)
    if user is not None or (dry_run and username not in bootstrap_users):
        plan.add_member(user, username, groups[writer_group], writer_group)
    return plan.changes


def product_members(api, product) -> dict[str, list[str]]:
    """Role -> member usernames, without the StarRocks service account (FD-Q2)."""
    result: dict[str, list[str]] = {}
    for role, name in product.groups.items():
        group = find_group(api, name)
        members = group_members(api, group["id"]) if group else []
        result[role] = sorted(member for member in members if member != STARROCKS_SERVICE_USER)
    return result


def remove_product(api, product, *, log: Log = print, dry_run: bool = False) -> int:
    """Delete the writer user, groups, and client roles; a missing object counts as removed."""
    plan = Planner(api, log, dry_run)
    bootstrap_users = {item["username"] for item in bootstrap_identities()["users"]}
    username = product.writer_user.username
    user = find_user(api, username)
    if user is not None and username not in bootstrap_users:
        plan.change(f"delete writer user {username}", "DELETE", f"/admin/realms/{REALM}/users/{user['id']}", None, (204, 404))
    password_file = ROOT / product.writer_user.password_file
    if password_file.exists() and username not in bootstrap_users:
        plan.changes += 1
        log(("would " if dry_run else "") + f"delete password file {product.writer_user.password_file}")
        if not dry_run:
            password_file.unlink()
    polaris = find_client(api, POLARIS_CLIENT_ID)["id"]
    for name in product.group_names():
        group = find_group(api, name)
        if group is not None:
            plan.change(f"delete group {name}", "DELETE", f"/admin/realms/{REALM}/groups/{group['id']}", None, (204, 404))
        if find_client_role(api, polaris, name) is not None:
            # Deleting the client role also removes it from role-platform-admin.
            plan.change(f"delete Polaris client role {name}", "DELETE", f"/admin/realms/{REALM}/clients/{polaris}/roles/{quote(name)}", None, (204, 404))
    return plan.changes
