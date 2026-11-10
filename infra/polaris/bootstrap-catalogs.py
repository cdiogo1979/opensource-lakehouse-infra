#!/usr/bin/env python3
"""Create or verify the shared Polaris catalogs and the namespaces of the data products.

  bootstrap-catalogs.py [--product FILE ...] [--dry-run]                    apply (default: every file)
  bootstrap-catalogs.py --inventory --product FILE                          table and view counts
  bootstrap-catalogs.py --remove --product FILE [--purge-data] [--dry-run]  drop the namespaces

The three shared catalogs are created on the default product's buckets. Every
product adds its bucket to each catalog's allowed locations, and its namespace
lives in that bucket (Polaris needs ALLOW_NAMESPACE_CUSTOM_LOCATION for that).
Table names and data are never printed.
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

REGION = "us-east-1"
S3_ENDPOINT = "http://rustfs:9000"


class BootstrapError(Exception):
    """Safe operator-facing failure; never includes response bodies."""


class Polaris:
    def __init__(self, base: str, realm: str, client_id: str, secret: str) -> None:
        self.base = base.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.secret = secret
        self.token: str | None = None

    def login(self) -> None:
        form = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "scope": "PRINCIPAL_ROLE:ALL",
        }).encode()
        basic = base64.b64encode(f"{self.client_id}:{self.secret}".encode()).decode("ascii")
        request = urllib.request.Request(
            f"{self.base}/api/catalog/v1/oauth/tokens",
            data=form,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Polaris-Realm": self.realm,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                self.token = json.loads(response.read())["access_token"]
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as error:
            raise BootstrapError("Polaris bootstrap authentication failed.") from error

    def call(self, method: str, path: str, payload: dict | None = None) -> tuple[int, dict | None]:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Accept": "application/json", "Polaris-Realm": self.realm}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(f"{self.base}{path}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                body = response.read()
                return response.status, json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            return error.code, None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            raise BootstrapError(f"Polaris request failed ({type(error).__name__}).") from error


def read_credentials(path: Path) -> tuple[str, str, str]:
    if path.is_symlink() or not path.is_file():
        raise BootstrapError("Protected Polaris bootstrap credentials are unavailable.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        realm, item = next(iter(data.items()))
        client_id, secret = item["client-id"], item["client-secret"]
    except (OSError, UnicodeError, json.JSONDecodeError, StopIteration, AttributeError, KeyError, TypeError) as error:
        raise BootstrapError("Protected Polaris bootstrap credentials have an invalid format.") from error
    if len(data) != 1 or not all(isinstance(value, str) and value for value in (realm, client_id, secret)):
        raise BootstrapError("Protected Polaris bootstrap credentials have an invalid format.")
    return realm, client_id, secret


def checked(status: int, allowed: tuple[int, ...], action: str) -> None:
    if status not in allowed:
        raise BootstrapError(f"{action} failed with HTTP {status}.")


def encoded(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def desired_allowed_locations(env_key: str, default, products: list) -> list[str]:
    """The catalog's base location (the default product's bucket) first, then each product's."""
    locations = [data_products.allowed_location(default.environment(env_key))]
    for product in products:
        location = data_products.allowed_location(product.environment(env_key))
        if location not in locations:
            locations.append(location)
    return locations


def storage_settings(allowed: list[str]) -> dict:
    return {
        "storageType": "S3",
        "allowedLocations": allowed,
        "endpoint": S3_ENDPOINT,
        "endpointInternal": S3_ENDPOINT,
        "stsEndpoint": S3_ENDPOINT,
        "pathStyleAccess": True,
        "region": REGION,
    }


def ensure_catalog(api: Polaris, name: str, base: str, allowed: list[str], dry_run: bool) -> None:
    """Create a missing catalog, or converge its allowed locations; any other difference is a conflict."""
    status, current = api.call("GET", f"/api/management/v1/catalogs/{encoded(name)}")
    if status == 404:
        print(f"  polaris: {'would create' if dry_run else 'create'} catalog {name}")
        if dry_run:
            return
        payload = {"catalog": {
            "name": name,
            "type": "INTERNAL",
            "readOnly": False,
            "properties": {"default-base-location": base},
            "storageConfigInfo": storage_settings(allowed),
        }}
        status, current = api.call("POST", "/api/management/v1/catalogs", payload)
        checked(status, (201, 409), f"Create Polaris catalog {name}")
        status, current = api.call("GET", f"/api/management/v1/catalogs/{encoded(name)}")
    checked(status, (200,), f"Read Polaris catalog {name}")
    if not isinstance(current, dict):
        raise BootstrapError(f"Catalog {name!r} returned an invalid representation.")
    storage = current.get("storageConfigInfo") or {}
    matches = (
        current.get("name") == name
        and current.get("type") == "INTERNAL"
        and (current.get("properties") or {}).get("default-base-location") == base
        and storage.get("storageType") == "S3"
        and storage.get("endpointInternal") == S3_ENDPOINT
        and storage.get("pathStyleAccess") is True
        and storage.get("region") == REGION
        and base in (storage.get("allowedLocations") or [])
    )
    if not matches:
        raise BootstrapError(f"Existing catalog {name!r} conflicts with the approved storage mapping.")
    if storage.get("allowedLocations") == allowed:
        return
    print(f"  polaris: {'would set' if dry_run else 'set'} allowed locations of {name} to {len(allowed)} product buckets")
    if dry_run:
        return
    status, _ = api.call("PUT", f"/api/management/v1/catalogs/{encoded(name)}", {
        "currentEntityVersion": current.get("entityVersion"),
        "storageConfigInfo": {**storage, "allowedLocations": allowed},
    })
    checked(status, (200,), f"Update allowed locations of {name}")


def namespace_properties(api: Polaris, catalog: str, namespace: str) -> dict | None:
    status, body = api.call("GET", f"/api/catalog/v1/{encoded(catalog)}/namespaces/{encoded(namespace)}")
    if status == 404:
        return None
    checked(status, (200,), f"Read namespace {namespace}")
    return (body or {}).get("properties") or {}


def ensure_namespace(api: Polaris, env, base: str, dry_run: bool) -> None:
    """Create the namespace in its product bucket; an existing one elsewhere is a conflict."""
    location = data_products.namespace_location(env)
    derived = f"{base}{env.namespace}/"
    properties = namespace_properties(api, env.catalog, env.namespace)
    if properties is not None:
        actual = properties.get("location")
        if actual not in (None, location, location.rstrip("/")):
            raise BootstrapError(f"Namespace {env.namespace!r} in {env.catalog!r} has another location; no changes applied.")
        return
    print(f"  polaris: {'would create' if dry_run else 'create'} namespace {env.catalog}.{env.namespace}")
    if dry_run:
        return
    # A namespace in the catalog's own bucket uses the derived location, so only
    # other products' namespaces need the custom-location feature.
    payload_properties = {} if location == derived else {"location": location}
    status, _ = api.call("POST", f"/api/catalog/v1/{encoded(env.catalog)}/namespaces", {"namespace": [env.namespace], "properties": payload_properties})
    checked(status, (200, 201, 409), f"Create namespace {env.namespace}")
    if namespace_properties(api, env.catalog, env.namespace) is None:
        raise BootstrapError(f"Namespace {env.namespace!r} was not found in catalog {env.catalog!r} after bootstrap.")


def list_identifiers(api: Polaris, env, kind: str) -> list[str]:
    names: list[str] = []
    query = ""
    while True:
        status, body = api.call("GET", f"/api/catalog/v1/{encoded(env.catalog)}/namespaces/{encoded(env.namespace)}/{kind}{query}")
        if status == 404:
            return names
        checked(status, (200,), f"List {kind} in {env.namespace}")
        names.extend(item.get("name") for item in (body or {}).get("identifiers", []) if item.get("name"))
        token = (body or {}).get("next-page-token")
        if not token:
            return names
        query = "?" + urllib.parse.urlencode({"pageToken": token})


def inventory(api: Polaris, product) -> dict[str, dict[str, int]]:
    return {
        env.key: {"tables": len(list_identifiers(api, env, "tables")), "views": len(list_identifiers(api, env, "views"))}
        for env in product.environments
    }


def remove_namespaces(api: Polaris, product, purge: bool, dry_run: bool) -> None:
    counts = inventory(api, product)
    if any(value for env in counts.values() for value in env.values()) and not purge:
        raise BootstrapError(f"Namespaces of {product.name} still hold tables or views {counts}; rerun with --purge-data.")
    for env in product.environments:
        base = f"/api/catalog/v1/{encoded(env.catalog)}/namespaces/{encoded(env.namespace)}"
        for kind in ("views", "tables"):
            for name in list_identifiers(api, env, kind):
                if dry_run:
                    continue
                # Polaris refuses purge here; the bucket removal deletes the files.
                status, _ = api.call("DELETE", f"{base}/{kind}/{encoded(name)}")
                checked(status, (204, 404), f"Drop a {kind[:-1]} in {env.namespace}")
        if namespace_properties(api, env.catalog, env.namespace) is None:
            continue
        print(f"  polaris: {'would drop' if dry_run else 'drop'} namespace {env.catalog}.{env.namespace}")
        if not dry_run:
            status, _ = api.call("DELETE", base)
            checked(status, (204, 404), f"Drop namespace {env.namespace}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--product", type=Path, action="append", default=[])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--remove", action="store_true")
    mode.add_argument("--inventory", action="store_true")
    parser.add_argument("--purge-data", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--credential-file", type=Path, default=Path(".runtime/credentials/polaris-bootstrap-credentials"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8181")
    args = parser.parse_args(argv)
    if (args.remove or args.inventory) and len(args.product) != 1:
        parser.error("--remove and --inventory need exactly one --product")
    operation_id = str(uuid.uuid4())
    try:
        selected, every = data_products.resolve_products(args.product, removal=args.remove or args.inventory)
        if args.remove and selected[0].protected:
            raise data_products.ProductError("The default data product cannot be removed.")
        default = next(p for p in every if p.protected)
        realm, client_id, secret = read_credentials(args.credential_file)
        if realm != "lakehouse":
            raise BootstrapError("Bootstrap credential realm must be lakehouse.")
        api = Polaris(args.base_url, realm, client_id, secret)
        api.login()
        if args.inventory:
            print(json.dumps(inventory(api, selected[0]), sort_keys=True))
            return 0
        if args.remove:
            remove_namespaces(api, selected[0], args.purge_data, args.dry_run)
            keep = data_products.remaining_products(every, selected[0])
        else:
            keep = list({p.name: p for p in every + selected}.values())
        for env_key, catalog in data_products.SHARED_CATALOGS.items():
            base = data_products.allowed_location(default.environment(env_key))
            ensure_catalog(api, catalog, base, desired_allowed_locations(env_key, default, keep), args.dry_run)
            if not args.remove:
                for product in selected:
                    ensure_namespace(api, product.environment(env_key), base, args.dry_run)
        verb = "removed" if args.remove else "verified"
        print(f"Product catalogs and namespaces {'planned' if args.dry_run else verb} (operation_id={operation_id}; products={len(selected)}).")
        return 0
    except data_products.ProductError as error:
        print(f"Catalog bootstrap refused (operation_id={operation_id}): {error}", file=sys.stderr)
        return 2
    except BootstrapError as error:
        print(f"Catalog bootstrap failed (operation_id={operation_id}): {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
