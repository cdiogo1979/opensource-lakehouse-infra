#!/usr/bin/env python3
"""One-time, local reset of the approved default-product Polaris catalogs and buckets."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


ROOT = Path(__file__).resolve().parents[2]
BUCKETS = ("bucket-default", "bucket-default-dev", "bucket-default-uat")
CATALOGS = (
    "lakehouse",
    "lakehouse-dev",
    "lakehouse-uat",
    "lakehouse_dev",
    "lakehouse_uat",
)
DEFAULT_POLARIS_URL = "http://127.0.0.1:8181"
DEFAULT_S3_URL = "http://127.0.0.1:9000"


class ResetError(RuntimeError):
    """Operator-safe failure that does not include request bodies or secrets."""


def local_endpoint(value: str, label: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ResetError(f"{label} must use the local HTTP endpoint (127.0.0.1 or localhost).")
    return value.rstrip("/")


def read_polaris_credentials(path: Path) -> tuple[str, str, str]:
    if path.is_symlink() or not path.is_file():
        raise ResetError("Protected Polaris bootstrap credentials are unavailable.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        realm, entry = next(iter(value.items()))
        client_id, secret = entry["client-id"], entry["client-secret"]
    except (OSError, UnicodeError, json.JSONDecodeError, StopIteration, AttributeError, KeyError, TypeError) as error:
        raise ResetError("Protected Polaris bootstrap credentials have an invalid format.") from error
    if len(value) != 1 or not all(isinstance(item, str) and item for item in (realm, client_id, secret)):
        raise ResetError("Protected Polaris bootstrap credentials have an invalid format.")
    if realm != "lakehouse":
        raise ResetError("Reset is restricted to the lakehouse Polaris realm.")
    return realm, client_id, secret


class Polaris:
    def __init__(self, base: str, realm: str, client_id: str, secret: str) -> None:
        self.base = base
        self.realm = realm
        basic = base64.b64encode(f"{client_id}:{secret}".encode()).decode("ascii")
        form = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": "PRINCIPAL_ROLE:ALL"}).encode()
        request = urllib.request.Request(
            f"{base}/api/catalog/v1/oauth/tokens",
            data=form,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Polaris-Realm": realm,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                self.token = json.loads(response.read())["access_token"]
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as error:
            raise ResetError("Polaris reset authentication failed.") from error

    def call(self, method: str, path: str) -> tuple[int, dict | None]:
        request = urllib.request.Request(
            f"{self.base}{path}",
            headers={"Accept": "application/json", "Authorization": f"Bearer {self.token}", "Polaris-Realm": self.realm},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                body = response.read()
                return response.status, json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            try:
                body = json.loads(error.read())
            except (ValueError, OSError):
                body = None
            return error.code, body if isinstance(body, dict) else None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            raise ResetError(f"Polaris reset request failed ({type(error).__name__}).") from error

    def list_namespaces(self, catalog: str) -> list[str]:
        encoded_catalog = urllib.parse.quote(catalog, safe="")
        status, body = self.call("GET", f"/api/catalog/v1/{encoded_catalog}/namespaces")
        if status != 200 or not isinstance(body, dict) or not isinstance(body.get("namespaces"), list):
            raise ResetError(f"Could not list namespaces in approved Polaris catalog {catalog!r} (HTTP {status}).")
        names: list[str] = []
        for namespace in body["namespaces"]:
            if not isinstance(namespace, list) or len(namespace) != 1 or not isinstance(namespace[0], str) or not namespace[0]:
                raise ResetError(f"Polaris catalog {catalog!r} contains an unsupported namespace; reset stopped safely.")
            names.append(namespace[0])
        return names

    def list_tables(self, catalog: str, namespace: str) -> list[str]:
        catalog_path = urllib.parse.quote(catalog, safe="")
        namespace_path = urllib.parse.quote(namespace, safe="")
        status, body = self.call(
            "GET", f"/api/catalog/v1/{catalog_path}/namespaces/{namespace_path}/tables"
        )
        if status != 200 or not isinstance(body, dict) or not isinstance(body.get("identifiers"), list):
            raise ResetError(f"Could not list tables in approved Polaris namespace {namespace!r} (HTTP {status}).")
        names: list[str] = []
        for identifier in body["identifiers"]:
            name = identifier.get("name") if isinstance(identifier, dict) else None
            if not isinstance(name, str) or not name:
                raise ResetError("Polaris returned an invalid table identifier; reset stopped safely.")
            names.append(name)
        return names

    def inspect_catalog_metadata(self, catalog: str) -> dict[str, list[str]]:
        return {namespace: self.list_tables(catalog, namespace) for namespace in self.list_namespaces(catalog)}

    def inspect_catalog_roles(self, catalog: str) -> dict[str, list[str]]:
        catalog_path = urllib.parse.quote(catalog, safe="")
        status, body = self.call("GET", f"/api/management/v1/catalogs/{catalog_path}/catalog-roles")
        roles = (body or {}).get("roles") or (body or {}).get("catalogRoles") if isinstance(body, dict) else None
        if status != 200 or not isinstance(roles, list):
            raise ResetError(f"Could not inspect roles in approved Polaris catalog {catalog!r} (HTTP {status}).")
        expected_names = {"catalog_admin"}
        expected_names.update(f"role-default-{role}-{catalog}-catalog" for role in ("developer", "analyst", "owner", "writer"))
        assignments: dict[str, list[str]] = {}
        for item in roles:
            name = item.get("name") if isinstance(item, dict) else None
            if not isinstance(name, str) or name not in expected_names:
                raise ResetError(f"Polaris catalog {catalog!r} contains an unapproved catalog role; reset stopped safely.")
            role_path = urllib.parse.quote(name, safe="")
            status, body = self.call(
                "GET", f"/api/management/v1/catalogs/{catalog_path}/catalog-roles/{role_path}/principal-roles"
            )
            assignees = (body or {}).get("roles") or (body or {}).get("principalRoles") if isinstance(body, dict) else None
            if status != 200 or not isinstance(assignees, list):
                raise ResetError(f"Could not inspect assignments for approved catalog role {name!r} (HTTP {status}).")
            principal_names = [entry.get("name") for entry in assignees if isinstance(entry, dict)]
            if len(principal_names) != len(assignees) or not all(isinstance(value, str) and value for value in principal_names):
                raise ResetError("Polaris returned an invalid catalog-role assignment; reset stopped safely.")
            assignments[name] = principal_names
        return assignments

    def clear_catalog_roles(self, catalog: str, assignments: dict[str, list[str]]) -> None:
        catalog_path = urllib.parse.quote(catalog, safe="")
        for role, principal_roles in assignments.items():
            if role == "catalog_admin":
                continue
            role_path = urllib.parse.quote(role, safe="")
            for principal_role in principal_roles:
                principal_path = urllib.parse.quote(principal_role, safe="")
                status, _ = self.call(
                    "DELETE",
                    f"/api/management/v1/principal-roles/{principal_path}/catalog-roles/{catalog_path}/{role_path}",
                )
                if status not in {200, 204, 404}:
                    raise ResetError(f"Could not clear the approved assignment for catalog role {role!r} (HTTP {status}).")
            status, _ = self.call(
                "DELETE", f"/api/management/v1/catalogs/{catalog_path}/catalog-roles/{role_path}"
            )
            if status not in {200, 204, 404}:
                raise ResetError(f"Could not remove approved catalog role {role!r} (HTTP {status}).")
        remaining = self.inspect_catalog_roles(catalog)
        if set(remaining) - {"catalog_admin"}:
            raise ResetError(f"Product catalog roles remain in approved catalog {catalog!r}; reset stopped safely.")

    def clear_catalog_metadata(self, catalog: str, namespace_tables: dict[str, list[str]]) -> None:
        catalog_path = urllib.parse.quote(catalog, safe="")
        for namespace, tables in namespace_tables.items():
            namespace_path = urllib.parse.quote(namespace, safe="")
            for table in tables:
                table_path = urllib.parse.quote(table, safe="")
                status, _ = self.call(
                    "DELETE",
                    f"/api/catalog/v1/{catalog_path}/namespaces/{namespace_path}/tables/{table_path}",
                )
                if status not in {200, 204, 404}:
                    raise ResetError(f"Could not remove table metadata from approved namespace {namespace!r} (HTTP {status}).")
            if self.list_tables(catalog, namespace):
                raise ResetError(f"Tables remain in approved Polaris namespace {namespace!r}; reset stopped safely.")
            status, _ = self.call("DELETE", f"/api/catalog/v1/{catalog_path}/namespaces/{namespace_path}")
            if status not in {200, 204, 404}:
                raise ResetError(f"Could not remove approved Polaris namespace {namespace!r} (HTTP {status}).")
        if self.list_namespaces(catalog):
            raise ResetError(f"Namespaces remain in approved Polaris catalog {catalog!r}; reset stopped safely.")

    def delete_catalog(self, catalog: str) -> None:
        encoded = urllib.parse.quote(catalog, safe="")
        status, body = self.call("DELETE", f"/api/management/v1/catalogs/{encoded}")
        if status not in {200, 202, 204, 404}:
            error = body.get("error", {}) if isinstance(body, dict) else {}
            detail = error.get("message", "") if isinstance(error, dict) else ""
            if isinstance(detail, str) and "not empty" in detail.lower():
                raise ResetError(f"Polaris catalog {catalog!r} still has child metadata; reset stopped safely (HTTP {status}).")
            raise ResetError(f"Could not remove approved Polaris catalog {catalog!r} (HTTP {status}).")
        status, _ = self.call("GET", f"/api/management/v1/catalogs/{encoded}")
        if status != 404:
            raise ResetError(f"Polaris catalog {catalog!r} remains after reset (HTTP {status}).")


def rustfs_client(endpoint: str):
    access_path = ROOT / ".runtime/credentials/rustfs-access-key"
    secret_path = ROOT / ".runtime/credentials/rustfs-secret-key"
    for path in (access_path, secret_path):
        if path.is_symlink() or not path.is_file():
            raise ResetError("Protected RustFS bootstrap credentials are unavailable.")
    access_key = access_path.read_text(encoding="utf-8").strip()
    secret_key = secret_path.read_text(encoding="utf-8").strip()
    if not access_key or not secret_key:
        raise ResetError("Protected RustFS bootstrap credentials are empty.")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        config=Config(s3={"addressing_style": "path"}),
    )


def bucket_exists(client, bucket: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as error:
        status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        raise ResetError(f"Required RustFS bucket {bucket!r} is unavailable (HTTP {status}).") from error


def delete_batches(client, bucket: str, objects: list[dict]) -> int:
    deleted = 0
    for offset in range(0, len(objects), 1000):
        batch = objects[offset : offset + 1000]
        try:
            result = client.delete_objects(Bucket=bucket, Delete={"Objects": batch, "Quiet": True})
        except ClientError as error:
            raise ResetError(f"Could not clear approved RustFS bucket {bucket!r}.") from error
        if result.get("Errors"):
            raise ResetError(f"RustFS reported an object deletion failure in bucket {bucket!r}.")
        deleted += len(batch)
    return deleted


def empty_bucket(client, bucket: str) -> int:
    versioning = client.get_bucket_versioning(Bucket=bucket).get("Status")
    deleted = 0
    if versioning in {"Enabled", "Suspended"}:
        paginator = client.get_paginator("list_object_versions")
        for page in paginator.paginate(Bucket=bucket):
            objects = [
                {"Key": entry["Key"], "VersionId": entry["VersionId"]}
                for entry in page.get("Versions", []) + page.get("DeleteMarkers", [])
            ]
            deleted += delete_batches(client, bucket, objects)
    else:
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket):
            objects = [{"Key": entry["Key"]} for entry in page.get("Contents", [])]
            deleted += delete_batches(client, bucket, objects)
    return deleted


def verify_bucket_empty(client, bucket: str) -> None:
    versioning = client.get_bucket_versioning(Bucket=bucket).get("Status")
    if versioning in {"Enabled", "Suspended"}:
        page = client.list_object_versions(Bucket=bucket, MaxKeys=1)
        if page.get("Versions") or page.get("DeleteMarkers"):
            raise ResetError(f"RustFS bucket {bucket!r} still contains object versions after reset.")
    elif client.list_objects_v2(Bucket=bucket, MaxKeys=1).get("Contents"):
        raise ResetError(f"RustFS bucket {bucket!r} still contains objects after reset.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-reset-default-product",
        action="store_true",
        help="required acknowledgement that this empties all objects and deletes known default-product catalog metadata",
    )
    parser.add_argument("--polaris-url", default=DEFAULT_POLARIS_URL)
    parser.add_argument("--rustfs-url", default=DEFAULT_S3_URL)
    args = parser.parse_args()
    if not args.confirm_reset_default_product:
        parser.error("pass --confirm-reset-default-product to authorize this one-time destructive reset")

    try:
        polaris_url = local_endpoint(args.polaris_url, "Polaris URL")
        rustfs_url = local_endpoint(args.rustfs_url, "RustFS URL")
        realm, client_id, client_secret = read_polaris_credentials(
            ROOT / ".runtime/credentials/polaris-bootstrap-credentials"
        )
        polaris = Polaris(polaris_url, realm, client_id, client_secret)
        rustfs = rustfs_client(rustfs_url)

        # Complete every availability check before deleting any catalog or object.
        for bucket in BUCKETS:
            bucket_exists(rustfs, bucket)
        present_catalogs: list[str] = []
        catalog_metadata: dict[str, dict[str, list[str]]] = {}
        catalog_roles: dict[str, dict[str, list[str]]] = {}
        for catalog in CATALOGS:
            encoded = urllib.parse.quote(catalog, safe="")
            status, _ = polaris.call("GET", f"/api/management/v1/catalogs/{encoded}")
            if status == 200:
                present_catalogs.append(catalog)
                catalog_metadata[catalog] = polaris.inspect_catalog_metadata(catalog)
                catalog_roles[catalog] = polaris.inspect_catalog_roles(catalog)
            elif status != 404:
                raise ResetError(f"Could not inspect approved Polaris catalog {catalog!r} (HTTP {status}).")

        for catalog in present_catalogs:
            polaris.clear_catalog_metadata(catalog, catalog_metadata[catalog])
            polaris.clear_catalog_roles(catalog, catalog_roles[catalog])
            polaris.delete_catalog(catalog)

        for bucket in BUCKETS:
            deleted = empty_bucket(rustfs, bucket)
            verify_bucket_empty(rustfs, bucket)
            print(f"Emptied approved bucket {bucket!r} ({deleted} object versions removed).")
        print(
            "One-time default-product reset completed; buckets remain, and normal bootstrap can recreate catalogs, namespaces, and tables."
        )
        return 0
    except (ResetError, BotoCoreError, ClientError, OSError, UnicodeError) as error:
        message = str(error) if isinstance(error, ResetError) else "A required local reset operation failed."
        print(f"Default-product reset failed: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
