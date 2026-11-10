#!/usr/bin/env python3
"""Create the approved default-product Polaris roles and catalog grants.

This command is explicit and requires all three catalogs to exist. It never
creates catalogs, namespaces, tables, or storage resources.
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


CATALOGS = ("lakehouse", "lakehouse-dev", "lakehouse-uat")
PRODUCT_ROLES = (
    "role-default-developer",
    "role-default-analyst",
    "role-default-owner",
    "role-default-writer",
)
READ = (
    "CATALOG_READ_PROPERTIES",
    "NAMESPACE_LIST",
    "TABLE_LIST",
    "TABLE_READ_PROPERTIES",
    "TABLE_READ_DATA",
    "VIEW_LIST",
    "VIEW_READ_PROPERTIES",
)
WRITE = READ + (
    "NAMESPACE_CREATE",
    "TABLE_CREATE",
    "TABLE_WRITE_PROPERTIES",
    "TABLE_WRITE_DATA",
)


class PolarisError(Exception):
    """A safe failure that never includes credential-bearing response bodies."""


class Client:
    def __init__(self, base_url: str, realm: str, client_id: str, secret: str) -> None:
        self.base = base_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.secret = secret
        self.token: str | None = None

    def call(self, method: str, path: str, payload: dict | None = None, *, auth: bool = True):
        headers = {"Accept": "application/json", "Polaris-Realm": self.realm}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(f"{self.base}{path}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read()
                return response.status, json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            return error.code, None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            raise PolarisError(f"Polaris request failed ({type(error).__name__}).") from error

    def login(self) -> None:
        basic = base64.b64encode(f"{self.client_id}:{self.secret}".encode()).decode("ascii")
        form = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "scope": "PRINCIPAL_ROLE:ALL",
        }).encode()
        request = urllib.request.Request(
            f"{self.base}/api/catalog/v1/oauth/tokens",
            data=form,
            headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded", "Polaris-Realm": self.realm},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                self.token = json.loads(response.read())["access_token"]
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as error:
            raise PolarisError("Polaris bootstrap authentication failed.") from error


def checked(status: int, accepted: tuple[int, ...], action: str) -> None:
    if status not in accepted:
        raise PolarisError(f"{action} failed with HTTP {status}.")


def read_credentials(path: Path) -> tuple[str, str, str]:
    if path.is_symlink() or not path.is_file():
        raise PolarisError("Protected Polaris bootstrap credentials are unavailable.")
    try:
        credentials = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PolarisError("Protected Polaris bootstrap credential file has an invalid format.") from error
    if not isinstance(credentials, dict) or len(credentials) != 1:
        raise PolarisError("Protected Polaris bootstrap credential file has an invalid format.")
    realm, entry = next(iter(credentials.items()))
    if not isinstance(entry, dict):
        raise PolarisError("Protected Polaris bootstrap credential file has an invalid format.")
    client_id = entry.get("client-id")
    client_secret = entry.get("client-secret")
    if not isinstance(client_id, str) or not client_id or not isinstance(client_secret, str) or not client_secret:
        raise PolarisError("Protected Polaris bootstrap credential file has an invalid format.")
    return realm, client_id, client_secret


def result_items(body: dict | None, *keys: str) -> list[dict]:
    if not isinstance(body, dict):
        raise PolarisError("Polaris returned an unexpected response.")
    for key in keys:
        items = body.get(key)
        if isinstance(items, list):
            return items
    raise PolarisError("Polaris returned an unexpected list response.")


def ensure_principal_roles(client: Client) -> None:
    status, body = client.call("GET", "/api/management/v1/principal-roles")
    checked(status, (200,), "List principal roles")
    roles = {item.get("name") for item in result_items(body, "roles", "principalRoles")}
    for name in PRODUCT_ROLES:
        if name in roles:
            continue
        status, _ = client.call("POST", "/api/management/v1/principal-roles", {"principalRole": {"name": name, "properties": {}}})
        checked(status, (201, 409), f"Create principal role {name}")
    status, body = client.call("GET", "/api/management/v1/principal-roles")
    checked(status, (200,), "Verify principal roles")
    roles = {item.get("name") for item in result_items(body, "roles", "principalRoles")}
    if not set(PRODUCT_ROLES).issubset(roles):
        raise PolarisError("Polaris product principal-role bootstrap did not converge.")


def expected_grants(catalog: str) -> dict[str, tuple[str, ...]]:
    matrix: dict[str, tuple[str, ...]] = {
        "role-default-developer": READ if catalog != "lakehouse-dev" else WRITE,
        "role-default-analyst": READ if catalog == "lakehouse" else (),
        "role-default-owner": ("CATALOG_MANAGE_CONTENT", "CATALOG_MANAGE_ACCESS"),
        "role-default-writer": WRITE,
    }
    return matrix


def ensure_catalog_roles(client: Client, catalog: str) -> None:
    encoded_catalog = urllib.parse.quote(catalog, safe="")
    status, body = client.call("GET", f"/api/management/v1/catalogs/{encoded_catalog}")
    checked(status, (200,), f"Verify required catalog {catalog}")
    status, body = client.call("GET", f"/api/management/v1/catalogs/{encoded_catalog}/catalog-roles")
    checked(status, (200,), f"List catalog roles for {catalog}")
    existing = {item.get("name") for item in result_items(body, "roles", "catalogRoles")}

    for principal_role, privileges in expected_grants(catalog).items():
        role_name = f"{principal_role}-{catalog}-catalog"
        encoded_role = urllib.parse.quote(role_name, safe="")
        if role_name not in existing:
            status, _ = client.call(
                "POST",
                f"/api/management/v1/catalogs/{encoded_catalog}/catalog-roles",
                {"catalogRole": {"name": role_name, "properties": {}}},
            )
            checked(status, (201, 409), f"Create catalog role {role_name}")

        status, current_body = client.call(
            "GET", f"/api/management/v1/catalogs/{encoded_catalog}/catalog-roles/{encoded_role}/grants"
        )
        checked(status, (200,), f"Read grants for {role_name}")
        current = current_body.get("grants", []) if isinstance(current_body, dict) else []
        have = {(item.get("type"), item.get("privilege")) for item in current if isinstance(item, dict)}
        expected = {("catalog", privilege) for privilege in privileges}
        unexpected = have - expected
        if unexpected:
            raise PolarisError(f"Catalog role {role_name!r} has unexpected grants; refusing to report convergence.")
        for privilege in privileges:
            if ("catalog", privilege) in have:
                continue
            status, _ = client.call(
                "PUT",
                f"/api/management/v1/catalogs/{encoded_catalog}/catalog-roles/{encoded_role}/grants",
                {"type": "catalog", "privilege": privilege},
            )
            checked(status, (200, 201, 204, 409), f"Grant {privilege} to {role_name}")

        encoded_principal_role = urllib.parse.quote(principal_role, safe="")
        status, _ = client.call(
            "PUT",
            f"/api/management/v1/principal-roles/{encoded_principal_role}/catalog-roles/{encoded_catalog}",
            {"catalogRole": {"name": role_name}},
        )
        checked(status, (201, 409), f"Bind {role_name} to {principal_role}")
        status, assignments = client.call(
            "GET", f"/api/management/v1/principal-roles/{encoded_principal_role}/catalog-roles/{encoded_catalog}"
        )
        checked(status, (200,), f"Verify {role_name} assignment")
        assigned = {item.get("name") for item in result_items(assignments, "roles", "catalogRoles")}
        if role_name not in assigned:
            raise PolarisError(f"Catalog-role assignment did not converge for {principal_role!r}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credential-file", type=Path, default=Path(".runtime/credentials/polaris-bootstrap-credentials"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8181")
    parser.add_argument("--realm", default="lakehouse")
    parser.add_argument(
        "--roles-only",
        action="store_true",
        help="Create and verify product principal roles without requiring catalogs or creating catalog grants",
    )
    args = parser.parse_args()
    operation_id = str(uuid.uuid4())
    try:
        credential_realm, client_id, secret = read_credentials(args.credential_file)
        if credential_realm != args.realm:
            raise PolarisError("Credential realm does not match the requested realm.")
        client = Client(args.base_url, args.realm, client_id, secret)
        client.login()
        if not args.roles_only:
            for catalog in CATALOGS:
                encoded_catalog = urllib.parse.quote(catalog, safe="")
                status, _ = client.call("GET", f"/api/management/v1/catalogs/{encoded_catalog}")
                checked(status, (200,), f"Preflight required catalog {catalog}")
        ensure_principal_roles(client)
        if args.roles_only:
            print(f"Polaris product principal roles verified (operation_id={operation_id}; roles={len(PRODUCT_ROLES)}).")
        else:
            for catalog in CATALOGS:
                ensure_catalog_roles(client, catalog)
            print(f"Polaris default-product catalog authorization reconciled (operation_id={operation_id}; catalogs={len(CATALOGS)}).")
        return 0
    except PolarisError as error:
        print(f"Polaris authorization bootstrap failed (operation_id={operation_id}): {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
