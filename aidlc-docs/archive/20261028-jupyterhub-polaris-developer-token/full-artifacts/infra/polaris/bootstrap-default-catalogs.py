#!/usr/bin/env python3
"""Create or verify the three default-product Polaris catalogs and namespaces."""

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


CATALOGS = (
    ("lakehouse", "default_lh", "bucket-default"),
    ("lakehouse_uat", "default_lhuat", "bucket-default-uat"),
    ("lakehouse_dev", "default_lhdev", "bucket-default-dev"),
)
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


def ensure_catalog(api: Polaris, name: str, namespace: str, bucket: str) -> None:
    encoded = urllib.parse.quote(name, safe="")
    status, current = api.call("GET", f"/api/management/v1/catalogs/{encoded}")
    location = f"s3://{bucket}/{name}/"
    storage = {
        "storageType": "S3",
        "allowedLocations": [location],
        "endpoint": S3_ENDPOINT,
        "endpointInternal": S3_ENDPOINT,
        "stsEndpoint": S3_ENDPOINT,
        "pathStyleAccess": True,
        "region": REGION,
    }
    if status == 404:
        payload = {"catalog": {
            "name": name,
            "type": "INTERNAL",
            "readOnly": False,
            "properties": {"default-base-location": location},
            "storageConfigInfo": storage,
        }}
        status, current = api.call("POST", "/api/management/v1/catalogs", payload)
        checked(status, (201, 409), f"Create Polaris catalog {name}")
        status, current = api.call("GET", f"/api/management/v1/catalogs/{encoded}")
    checked(status, (200,), f"Read Polaris catalog {name}")
    if not isinstance(current, dict):
        raise BootstrapError(f"Catalog {name!r} returned an invalid representation.")
    actual_location = (current.get("properties") or {}).get("default-base-location")
    actual_storage = current.get("storageConfigInfo") or {}
    matches = (
        current.get("name") == name
        and current.get("type") == "INTERNAL"
        and actual_location == location
        and actual_storage.get("storageType") == "S3"
        and actual_storage.get("allowedLocations") == [location]
        and actual_storage.get("endpointInternal") == S3_ENDPOINT
        and actual_storage.get("pathStyleAccess") is True
        and actual_storage.get("region") == REGION
    )
    if not matches:
        raise BootstrapError(f"Existing catalog {name!r} conflicts with the approved storage mapping.")


def ensure_namespace(api: Polaris, catalog: str, namespace: str) -> None:
    catalog_path = urllib.parse.quote(catalog, safe="")
    status, body = api.call("GET", f"/api/catalog/v1/{catalog_path}/namespaces")
    checked(status, (200,), f"List namespaces in {catalog}")
    present = [item for item in (body or {}).get("namespaces", []) if item == [namespace]]
    if not present:
        status, _ = api.call(
            "POST",
            f"/api/catalog/v1/{catalog_path}/namespaces",
            {"namespace": [namespace], "properties": {}},
        )
        checked(status, (200, 201, 409), f"Create namespace {namespace}")
    status, body = api.call("GET", f"/api/catalog/v1/{catalog_path}/namespaces")
    checked(status, (200,), f"Verify namespace in {catalog}")
    if [namespace] not in (body or {}).get("namespaces", []):
        raise BootstrapError(f"Namespace {namespace!r} was not found in catalog {catalog!r} after bootstrap.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credential-file", type=Path, default=Path(".runtime/credentials/polaris-bootstrap-credentials"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8181")
    args = parser.parse_args()
    operation_id = str(uuid.uuid4())
    try:
        realm, client_id, secret = read_credentials(args.credential_file)
        if realm != "lakehouse":
            raise BootstrapError("Bootstrap credential realm must be lakehouse.")
        api = Polaris(args.base_url, realm, client_id, secret)
        api.login()
        for catalog, namespace, bucket in CATALOGS:
            ensure_catalog(api, catalog, namespace, bucket)
            ensure_namespace(api, catalog, namespace)
        print(f"Default product catalogs and namespaces verified (operation_id={operation_id}; catalogs={len(CATALOGS)}).")
        return 0
    except BootstrapError as error:
        print(f"Default catalog bootstrap failed (operation_id={operation_id}): {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
