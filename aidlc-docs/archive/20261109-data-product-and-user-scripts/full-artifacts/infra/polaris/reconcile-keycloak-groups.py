#!/usr/bin/env python3
"""Reconcile the Keycloak product groups (and the owner-equivalent platform-admin group) into Polaris principal roles.

The product groups come from the data product files; ``role-platform-admin``
members get every product's owner role. A product group missing from Keycloak
(a product being removed) counts as having no members.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "products"))
import data_products  # noqa: E402

REALM = "lakehouse"


def group_principal_roles(products: list) -> dict[str, frozenset[str]]:
    """Keycloak group -> Polaris principal roles; the platform administrator owns every product."""
    mapping = {group: frozenset({group}) for group in data_products.product_groups(products)}
    mapping[data_products.PLATFORM_ADMIN_GROUP] = frozenset(data_products.owner_groups(products))
    return mapping


class ReconcileError(Exception):
    """Redacted operator-facing failure."""


def read_secret_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ReconcileError("A required protected credential file is unavailable.")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0]:
        raise ReconcileError("A required protected credential file is empty.")
    return lines[0]


class HttpClient:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.token: str | None = None

    def call(self, method: str, path: str, payload: object | None = None, *, query: dict | None = None):
        url = f"{self.base}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = {"Accept": "application/json", "Polaris-Realm": REALM}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                body = response.read()
                return response.status, json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            return error.code, None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            raise ReconcileError(f"Provider request failed ({type(error).__name__}).") from error


def checked(status: int, accepted: tuple[int, ...], action: str) -> None:
    if status not in accepted:
        raise ReconcileError(f"{action} failed with HTTP {status}.")


def keycloak_login(api: HttpClient, username: str, password: str) -> None:
    data = urllib.parse.urlencode({"grant_type": "password", "client_id": "admin-cli", "username": username, "password": password}).encode()
    request = urllib.request.Request(
        f"{api.base}/realms/master/protocol/openid-connect/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            api.token = json.loads(response.read())["access_token"]
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as error:
        raise ReconcileError("Keycloak authentication failed.") from error


def polaris_login(api: HttpClient, credential_path: Path) -> None:
    if credential_path.is_symlink() or not credential_path.is_file():
        raise ReconcileError("Protected Polaris bootstrap credentials are unavailable.")
    try:
        credentials = json.loads(credential_path.read_text(encoding="utf-8"))
        entry = credentials.get(REALM) if isinstance(credentials, dict) else None
    except (OSError, UnicodeError, json.JSONDecodeError):
        entry = None
    if not isinstance(entry, dict):
        raise ReconcileError("Protected Polaris bootstrap credentials have an invalid format.")
    client_id = entry.get("client-id")
    client_secret = entry.get("client-secret")
    if not isinstance(client_id, str) or not client_id or not isinstance(client_secret, str) or not client_secret:
        raise ReconcileError("Protected Polaris bootstrap credentials have an invalid format.")
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode("ascii")
    data = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": "PRINCIPAL_ROLE:ALL"}).encode()
    request = urllib.request.Request(
        f"{api.base}/api/catalog/v1/oauth/tokens",
        data=data,
        headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded", "Polaris-Realm": REALM},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            api.token = json.loads(response.read())["access_token"]
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as error:
        raise ReconcileError("Polaris bootstrap authentication failed.") from error


def get_group(api: HttpClient, name: str) -> dict | None:
    status, groups = api.call("GET", f"/admin/realms/{REALM}/groups", query={"search": name, "briefRepresentation": "true"})
    checked(status, (200,), "Keycloak group lookup")
    matches = [group for group in groups or [] if group.get("name") == name]
    if len(matches) > 1:
        raise ReconcileError(f"Expected one Keycloak group {name!r}; found {len(matches)}.")
    return matches[0] if matches else None


def get_members(api: HttpClient, group_id: str) -> list[dict]:
    members: list[dict] = []
    first = 0
    while True:
        status, page = api.call("GET", f"/admin/realms/{REALM}/groups/{group_id}/members", query={"first": first, "max": 500})
        checked(status, (200,), "Keycloak group member lookup")
        page = page or []
        members.extend(page)
        if len(page) < 500:
            return members
        first += len(page)


def ensure_principal(api: HttpClient, user: dict) -> str:
    username = user.get("username")
    if not username or not user.get("id"):
        raise ReconcileError("A Keycloak group member is missing a stable username or subject.")
    encoded = urllib.parse.quote(username, safe="")
    status, principal = api.call("GET", f"/api/management/v1/principals/{encoded}")
    if status == 404:
        status, response = api.call("POST", "/api/management/v1/principals", {"principal": {"name": username, "properties": {}}})
        checked(status, (201, 409), f"Create Polaris principal {username}")
        if status == 201 and isinstance(response, dict):
            principal = response.get("principal") or response
        else:
            status, principal = api.call("GET", f"/api/management/v1/principals/{encoded}")
            checked(status, (200,), f"Read Polaris principal {username}")
    else:
        checked(status, (200,), f"Read Polaris principal {username}")
    principal_name = principal.get("name") if isinstance(principal, dict) else None
    if principal_name != username:
        raise ReconcileError(f"Polaris principal name did not match Keycloak username {username!r}.")
    return username


def reconcile_assignment(api: HttpClient, principal: str, desired: set[str], managed: frozenset[str]) -> None:
    encoded = urllib.parse.quote(principal, safe="")
    status, body = api.call("GET", f"/api/management/v1/principals/{encoded}/principal-roles")
    checked(status, (200,), f"Read Polaris roles for {principal}")
    current = (body.get("roles") or body.get("principalRoles") or []) if isinstance(body, dict) else []
    current_names = {item.get("name") for item in current if isinstance(item, dict)}
    for role in desired - current_names:
        status, _ = api.call(
            "PUT",
            f"/api/management/v1/principals/{encoded}/principal-roles",
            {"principalRole": {"name": role}},
        )
        checked(status, (201, 409), f"Assign {role} to {principal}")
    for role in (current_names & managed) - desired:
        encoded_role = urllib.parse.quote(role, safe="")
        status, _ = api.call("DELETE", f"/api/management/v1/principals/{encoded}/principal-roles/{encoded_role}")
        checked(status, (204, 404), f"Remove stale assignment {role} from {principal}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keycloak-admin-password-file", type=Path, default=Path(".runtime/credentials/keycloak-admin-password"))
    parser.add_argument("--polaris-credential-file", type=Path, default=Path(".runtime/credentials/polaris-bootstrap-credentials"))
    parser.add_argument("--keycloak-url", default="http://127.0.0.1:8080")
    parser.add_argument("--polaris-url", default="http://127.0.0.1:8181")
    args = parser.parse_args()
    operation_id = str(uuid.uuid4())
    try:
        try:
            products = data_products.load_all()
        except data_products.ProductError as error:
            raise ReconcileError(f"The data product files are invalid; nothing changed: {error}") from error
        mapping = group_principal_roles(products)
        managed = data_products.product_groups(products)
        keycloak = HttpClient(args.keycloak_url)
        keycloak_login(keycloak, "admin", read_secret_file(args.keycloak_admin_password_file))
        polaris = HttpClient(args.polaris_url)
        polaris_login(polaris, args.polaris_credential_file)

        membership: dict[str, set[str]] = {}
        users: dict[str, dict] = {}
        groups = {name: get_group(keycloak, name) for name in mapping}
        if groups[data_products.PLATFORM_ADMIN_GROUP] is None:
            raise ReconcileError("The role-platform-admin group is missing; nothing changed.")
        # A product being removed: its groups (and so its principal roles) are gone,
        # so nobody, the platform administrator included, keeps its roles.
        missing = {name for name, group in groups.items() if group is None}
        for name in sorted(missing):
            print(f"Keycloak group {name} is missing; treating it as empty.")
        for group_name, principal_roles in mapping.items():
            group = groups[group_name]
            if group is None:
                continue
            principal_roles = principal_roles - missing
            for user in get_members(keycloak, group["id"]):
                username = user.get("username")
                if not username:
                    raise ReconcileError(f"Group {group_name!r} contains a user without a username.")
                if username in users and users[username].get("id") != user.get("id"):
                    raise ReconcileError(f"Duplicate Keycloak username {username!r} was returned.")
                users[username] = user
                membership.setdefault(username, set()).update(principal_roles)

        # Include existing Polaris principals with a managed role so a member
        # removed from every product group still has stale product access removed.
        status, body = polaris.call("GET", "/api/management/v1/principals")
        checked(status, (200,), "List existing Polaris principals")
        principal_items = body.get("principals", []) if isinstance(body, dict) else []
        for principal in principal_items:
            name = principal.get("name") if isinstance(principal, dict) else None
            if not name:
                raise ReconcileError("Polaris principal list contains an invalid entry.")
            if name in membership:
                continue
            encoded = urllib.parse.quote(name, safe="")
            status, role_body = polaris.call("GET", f"/api/management/v1/principals/{encoded}/principal-roles")
            checked(status, (200,), f"Read Polaris roles for {name}")
            roles = (role_body.get("roles") or role_body.get("principalRoles") or []) if isinstance(role_body, dict) else []
            if any(item.get("name") in managed for item in roles if isinstance(item, dict)):
                membership[name] = set()
                users[name] = {"username": name, "id": None}

        for username, user in users.items():
            if user.get("id"):
                ensure_principal(polaris, user)
            reconcile_assignment(polaris, username, membership[username], managed)
        print(f"Keycloak memberships reconciled to Polaris (operation_id={operation_id}; principals={len(users)}).")
        return 0
    except ReconcileError as error:
        print(f"Identity reconciliation failed (operation_id={operation_id}): {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
