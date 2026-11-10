#!/usr/bin/env python3
"""Converge the Polaris roles and namespace-scoped grants of the data products.

  bootstrap-product-authorization.py [--product FILE ...] [--dry-run]   apply (default: every file)
  bootstrap-product-authorization.py --roles-only                       principal roles only
  bootstrap-product-authorization.py --remove --product FILE [--dry-run]

Each product group has one principal role and, per shared catalog where its
level is not "none", one catalog role: catalog-level NAMESPACE_LIST and
CATALOG_READ_PROPERTIES, and the level's privileges on the product namespace
(BR-2). Missing grants are added first; grants the files do not describe are
then revoked and reported (BR-7). This also migrates the default product from
its former catalog-wide grants. It never creates catalogs or namespaces.
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

CATALOG_GRANTS = ("CATALOG_READ_PROPERTIES", "NAMESPACE_LIST")
READ = (
    # StarRocks loads namespace metadata when it opens a database (LOAD_NAMESPACE_METADATA).
    "NAMESPACE_READ_PROPERTIES",
    "TABLE_LIST",
    "TABLE_READ_PROPERTIES",
    "TABLE_READ_DATA",
    "VIEW_LIST",
    "VIEW_READ_PROPERTIES",
)
WRITE = READ + ("TABLE_CREATE", "TABLE_WRITE_PROPERTIES", "TABLE_WRITE_DATA")
MANAGE = WRITE + ("TABLE_DROP", "TABLE_FULL_METADATA", "VIEW_CREATE", "VIEW_DROP", "VIEW_FULL_METADATA")
NAMESPACE_GRANTS = {"none": (), "read": READ, "write": WRITE, "manage": MANAGE}

Grant = tuple  # ("catalog", privilege) or ("namespace", namespace, privilege)


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


def grant_key(item: dict) -> Grant | None:
    """A comparable key for a Polaris grant; None for grant types this tool never manages."""
    privilege = item.get("privilege")
    if item.get("type") == "catalog":
        return ("catalog", privilege)
    if item.get("type") == "namespace":
        return ("namespace", ".".join(item.get("namespace") or []), privilege)
    return None


def grant_body(key: Grant) -> dict:
    if key[0] == "catalog":
        return {"type": "catalog", "privilege": key[1]}
    return {"type": "namespace", "namespace": key[1].split("."), "privilege": key[2]}


def desired_grants(product, role: str, env_key: str) -> set[Grant]:
    """BR-2: the grants of one product role in one environment's catalog role."""
    level = product.access[role][env_key]
    if level == "none":
        return set()
    namespace = product.environment(env_key).namespace
    return {("catalog", privilege) for privilege in CATALOG_GRANTS} | {
        ("namespace", namespace, privilege) for privilege in NAMESPACE_GRANTS[level]
    }


def plan_grants(current: set[Grant | None], desired: set[Grant]) -> tuple[list[Grant], list[Grant]]:
    """Additions first, then revocations of managed extras (unknown grant types are left alone)."""
    known = {key for key in current if key is not None}
    return sorted(desired - known), sorted(known - desired)


class Converger:
    def __init__(self, client: Client, dry_run: bool) -> None:
        self.client = client
        self.dry_run = dry_run
        self.added = 0
        self.revoked = 0

    def log(self, text: str) -> None:
        print(f"  polaris: {'would ' if self.dry_run else ''}{text}")

    def principal_roles(self) -> set[str]:
        status, body = self.client.call("GET", "/api/management/v1/principal-roles")
        checked(status, (200,), "List principal roles")
        return {item.get("name") for item in result_items(body, "roles", "principalRoles")}

    def ensure_principal_role(self, name: str, existing: set[str]) -> None:
        if name in existing:
            return
        self.log(f"create principal role {name}")
        if not self.dry_run:
            status, _ = self.client.call("POST", "/api/management/v1/principal-roles", {"principalRole": {"name": name, "properties": {}}})
            checked(status, (201, 409), f"Create principal role {name}")

    def catalog_roles(self, catalog: str) -> set[str]:
        status, body = self.client.call("GET", f"/api/management/v1/catalogs/{quote(catalog)}/catalog-roles")
        checked(status, (200,), f"List catalog roles for {catalog}")
        return {item.get("name") for item in result_items(body, "roles", "catalogRoles")}

    def current_grants(self, catalog: str, role: str) -> set[Grant | None]:
        status, body = self.client.call("GET", f"/api/management/v1/catalogs/{quote(catalog)}/catalog-roles/{quote(role)}/grants")
        checked(status, (200,), f"Read grants for {role}")
        return {grant_key(item) for item in (body or {}).get("grants", []) if isinstance(item, dict)}

    def revoke(self, catalog: str, role: str, key: Grant) -> None:
        self.revoked += 1
        self.log(f"revoke {' '.join(key)} from {role}")
        if not self.dry_run:
            status, _ = self.client.call("POST", f"/api/management/v1/catalogs/{quote(catalog)}/catalog-roles/{quote(role)}/grants", {"grant": grant_body(key)})
            checked(status, (200, 201, 204), f"Revoke {key[-1]} from {role}")

    def converge_role(self, catalog: str, principal_role: str, desired: set[Grant], existing: set[str]) -> list[Grant]:
        """Create, grant, and bind one catalog role; returns the revocations still to apply."""
        role = data_products.catalog_role(principal_role, catalog)
        path = f"/api/management/v1/catalogs/{quote(catalog)}/catalog-roles/{quote(role)}"
        if not desired:
            return []
        if role not in existing:
            self.log(f"create catalog role {role}")
            if not self.dry_run:
                status, _ = self.client.call("POST", f"/api/management/v1/catalogs/{quote(catalog)}/catalog-roles", {"catalogRole": {"name": role, "properties": {}}})
                checked(status, (201, 409), f"Create catalog role {role}")
        current = self.current_grants(catalog, role) if role in existing or not self.dry_run else set()
        additions, revocations = plan_grants(current, desired)
        for key in additions:
            self.added += 1
            self.log(f"grant {' '.join(key)} to {role}")
            if not self.dry_run:
                status, _ = self.client.call("PUT", f"{path}/grants", grant_body(key))
                checked(status, (200, 201, 204, 409), f"Grant {key[-1]} to {role}")
        self.bind(catalog, principal_role, role)
        return revocations

    def bind(self, catalog: str, principal_role: str, role: str) -> None:
        base = f"/api/management/v1/principal-roles/{quote(principal_role)}/catalog-roles/{quote(catalog)}"
        status, assignments = self.client.call("GET", base)
        if status == 200 and role in {item.get("name") for item in result_items(assignments, "roles", "catalogRoles")}:
            return
        self.log(f"bind {role} to {principal_role}")
        if not self.dry_run:
            status, _ = self.client.call("PUT", base, {"catalogRole": {"name": role}})
            checked(status, (201, 409), f"Bind {role} to {principal_role}")

    def drop_role(self, catalog: str, principal_role: str, existing: set[str]) -> None:
        """Empty, unbind, and delete a catalog role whose level is now "none" (or whose product is removed)."""
        role = data_products.catalog_role(principal_role, catalog)
        if role not in existing:
            return
        for key in sorted(k for k in self.current_grants(catalog, role) if k is not None):
            self.revoke(catalog, role, key)
        self.log(f"delete catalog role {role}")
        if not self.dry_run:
            status, _ = self.client.call("DELETE", f"/api/management/v1/principal-roles/{quote(principal_role)}/catalog-roles/{quote(catalog)}/{quote(role)}")
            checked(status, (204, 404), f"Unbind {role}")
            status, _ = self.client.call("DELETE", f"/api/management/v1/catalogs/{quote(catalog)}/catalog-roles/{quote(role)}")
            checked(status, (204, 404), f"Delete catalog role {role}")


def quote(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def apply_products(converger: Converger, products: list, roles_only: bool) -> None:
    existing = converger.principal_roles()
    for product in products:
        for group in product.group_names():
            converger.ensure_principal_role(group, existing)
    if roles_only:
        return
    for env_key, catalog in data_products.SHARED_CATALOGS.items():
        status, _ = converger.client.call("GET", f"/api/management/v1/catalogs/{quote(catalog)}")
        checked(status, (200,), f"Preflight required catalog {catalog}")
        roles = converger.catalog_roles(catalog)
        pending: list[tuple[str, Grant]] = []
        for product in products:
            for role in data_products.ROLES:
                group = product.groups[role]
                desired = desired_grants(product, role, env_key)
                if desired:
                    revocations = converger.converge_role(catalog, group, desired, roles)
                    pending += [(data_products.catalog_role(group, catalog), key) for key in revocations]
                else:
                    converger.drop_role(catalog, group, roles)
        # Revocations only after every addition in this catalog (BR-7).
        for role, key in pending:
            converger.revoke(catalog, role, key)


def remove_product(converger: Converger, product) -> None:
    for catalog in data_products.SHARED_CATALOGS.values():
        roles = converger.catalog_roles(catalog)
        for group in product.group_names():
            converger.drop_role(catalog, group, roles)
    existing = converger.principal_roles()
    for group in product.group_names():
        if group in existing:
            converger.log(f"delete principal role {group}")
            if not converger.dry_run:
                status, _ = converger.client.call("DELETE", f"/api/management/v1/principal-roles/{quote(group)}")
                checked(status, (204, 404), f"Delete principal role {group}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--credential-file", type=Path, default=Path(".runtime/credentials/polaris-bootstrap-credentials"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8181")
    parser.add_argument("--realm", default="lakehouse")
    parser.add_argument("--product", type=Path, action="append", default=[])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--roles-only", action="store_true", help="Create and verify product principal roles only")
    mode.add_argument("--remove", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.remove and len(args.product) != 1:
        parser.error("--remove needs exactly one --product")
    operation_id = str(uuid.uuid4())
    try:
        products, _ = data_products.resolve_products(args.product, removal=args.remove)
        if args.remove and products[0].protected:
            raise data_products.ProductError("The default data product cannot be removed.")
        credential_realm, client_id, secret = read_credentials(args.credential_file)
        if credential_realm != args.realm:
            raise PolarisError("Credential realm does not match the requested realm.")
        client = Client(args.base_url, args.realm, client_id, secret)
        client.login()
        converger = Converger(client, args.dry_run)
        if args.remove:
            remove_product(converger, products[0])
        else:
            apply_products(converger, products, args.roles_only)
        state = "planned" if args.dry_run else "reconciled"
        scope = "principal roles" if args.roles_only else "authorization"
        print(f"Polaris product {scope} {state} (operation_id={operation_id}; products={len(products)}; "
              f"grants-added={converger.added}; grants-revoked={converger.revoked}).")
        return 0
    except data_products.ProductError as error:
        print(f"Polaris authorization refused (operation_id={operation_id}): {error}", file=sys.stderr)
        return 2
    except PolarisError as error:
        print(f"Polaris authorization bootstrap failed (operation_id={operation_id}): {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
