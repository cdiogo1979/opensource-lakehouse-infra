#!/usr/bin/env python3
"""Create, inventory, or remove the RustFS buckets of the data products.

  bootstrap-buckets.py [--product FILE ...] [--dry-run]                  create (default: every file)
  bootstrap-buckets.py --inventory --product FILE                        object counts per bucket
  bootstrap-buckets.py --remove --product FILE [--purge-data] [--dry-run]

Existing buckets and their contents are always preserved, except by a removal
with --purge-data. Object keys and contents are never printed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import xml.etree.ElementTree as ElementTree
import hashlib
import hmac
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra" / "products"))
import data_products  # noqa: E402

S3_NAMESPACE = "{http://s3.amazonaws.com/doc/2006-03-01/}"


def read_secret(name: str) -> str:
    path = ROOT / ".runtime" / "credentials" / name
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"Required protected credential is unavailable: {name}")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError(f"Required protected credential is empty: {name}")
    return value


class S3Client:
    def __init__(self, endpoint: str, access_key: str, secret_key: str) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.access_key = access_key
        self.secret_key = secret_key
        self.host = self.endpoint.removeprefix("http://").removeprefix("https://")
        self.region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

    def request(
        self, method: str, path: str, query: dict[str, str] | None = None, body: bytes = b""
    ) -> tuple[int, bytes]:
        canonical_query = "&".join(
            f"{urllib.parse.quote(key, safe='-_.~')}={urllib.parse.quote(value, safe='-_.~')}"
            for key, value in sorted((query or {}).items())
        )
        now = dt.datetime.now(dt.timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date = now.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(body).hexdigest()
        headers = {
            "host": self.host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        signed_headers = ";".join(sorted(headers))
        canonical_headers = "".join(f"{key}:{headers[key]}\n" for key in sorted(headers))
        canonical_request = (
            f"{method}\n{path}\n{canonical_query}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        )
        scope = f"{date}/{self.region}/s3/aws4_request"
        string_to_sign = (
            f"AWS4-HMAC-SHA256\n{amz_date}\n{scope}\n"
            f"{hashlib.sha256(canonical_request.encode()).hexdigest()}"
        )

        def sign(key: bytes, value: str) -> bytes:
            return hmac.new(key, value.encode(), hashlib.sha256).digest()

        signing_key = sign(("AWS4" + self.secret_key).encode(), date)
        signing_key = sign(signing_key, self.region)
        signing_key = sign(signing_key, "s3")
        signing_key = sign(signing_key, "aws4_request")
        signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
        headers["authorization"] = (
            f"AWS4-HMAC-SHA256 Credential={self.access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        url = f"{self.endpoint}{path}" + (f"?{canonical_query}" if canonical_query else "")
        request = urllib.request.Request(url, data=body or None, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()
        except (OSError, TimeoutError) as error:
            raise RuntimeError("RustFS S3 request failed; verify the endpoint and service health") from error


def _children(body: bytes, tag: str) -> list[ElementTree.Element]:
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as error:
        raise RuntimeError("RustFS returned an unrecognized listing.") from error
    return [item for item in root.iter() if item.tag in (tag, S3_NAMESPACE + tag)]


def _text(element: ElementTree.Element, tag: str) -> str | None:
    for child in element:
        if child.tag in (tag, S3_NAMESPACE + tag):
            return child.text
    return None


def bucket_exists(client: S3Client, bucket: str) -> bool:
    status, _ = client.request("HEAD", f"/{bucket}")
    if status in (200, 404):
        return status == 200
    raise RuntimeError(f"Could not inspect RustFS bucket {bucket}; HTTP {status}")


def object_versions(client: S3Client, bucket: str, limit: int | None = None) -> list[tuple[str, str | None]]:
    """(key, version id) of every object version and delete marker; None for unversioned objects."""
    found: list[tuple[str, str | None]] = []
    query = {"versions": "", "max-keys": "1000"}
    while True:
        status, body = client.request("GET", f"/{bucket}", query)
        if status != 200:
            raise RuntimeError(f"Could not list RustFS bucket {bucket}; HTTP {status}")
        for tag in ("Version", "DeleteMarker"):
            for item in _children(body, tag):
                version = _text(item, "VersionId")
                found.append((_text(item, "Key") or "", None if version in (None, "", "null") else version))
        if limit is not None and len(found) >= limit:
            return found[:limit]
        truncated = (_children(body, "IsTruncated") or [None])[0]
        if truncated is None or truncated.text != "true":
            return found
        next_key = (_children(body, "NextKeyMarker") or [None])[0]
        next_version = (_children(body, "NextVersionIdMarker") or [None])[0]
        query = {"versions": "", "max-keys": "1000", "key-marker": next_key.text if next_key is not None else ""}
        if next_version is not None and next_version.text:
            query["version-id-marker"] = next_version.text


def create_buckets(client: S3Client, product, dry_run: bool) -> int:
    changes = 0
    for bucket in product.buckets():
        if bucket_exists(client, bucket):
            print(f"Bucket {bucket} exists; preserving its contents.")
            continue
        changes += 1
        if dry_run:
            print(f"Would create bucket {bucket}.")
            continue
        status, _ = client.request("PUT", f"/{bucket}")
        if status not in (200, 409):
            raise RuntimeError(f"Could not create RustFS bucket {bucket}; HTTP {status}")
        if not bucket_exists(client, bucket):
            raise RuntimeError(f"RustFS did not confirm bucket {bucket}")
        print(f"Created bucket {bucket}.")
    return changes


def inventory(client: S3Client, product) -> dict[str, int]:
    """Object versions per environment (0 for a missing bucket)."""
    return {
        env.key: len(object_versions(client, env.bucket)) if bucket_exists(client, env.bucket) else 0
        for env in product.environments
    }


def remove_buckets(client: S3Client, product, purge: bool, dry_run: bool) -> int:
    counts = inventory(client, product)
    if any(counts.values()) and not purge:
        raise RuntimeError(f"Buckets of {product.name} still hold objects {counts}; rerun with --purge-data to delete them.")
    changes = 0
    for env in product.environments:
        if not bucket_exists(client, env.bucket):
            continue
        versions = object_versions(client, env.bucket)
        changes += 1 + len(versions)
        if dry_run:
            print(f"Would delete {len(versions)} object versions and bucket {env.bucket}.")
            continue
        for key, version in versions:
            query = {"versionId": version} if version else None
            status, _ = client.request("DELETE", f"/{env.bucket}/{urllib.parse.quote(key, safe='/-_.~')}", query)
            if status not in (200, 204, 404):
                raise RuntimeError(f"Could not delete an object in RustFS bucket {env.bucket}; HTTP {status}")
        status, _ = client.request("DELETE", f"/{env.bucket}")
        if status not in (200, 204, 404):
            raise RuntimeError(f"Could not delete RustFS bucket {env.bucket}; HTTP {status}")
        print(f"Deleted bucket {env.bucket} ({len(versions)} object versions).")
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--product", type=Path, action="append", default=[])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--remove", action="store_true")
    mode.add_argument("--inventory", action="store_true")
    parser.add_argument("--purge-data", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if (args.remove or args.inventory) and len(args.product) != 1:
        parser.error("--remove and --inventory need exactly one --product")
    try:
        products, _ = data_products.resolve_products(args.product, removal=args.remove or args.inventory)
        if args.remove and products[0].protected:
            raise data_products.ProductError("The default data product cannot be removed.")
        endpoint = os.environ.get("RUSTFS_S3_ENDPOINT", "http://127.0.0.1:9000")
        client = S3Client(endpoint, read_secret("rustfs-access-key"), read_secret("rustfs-secret-key"))
        if args.inventory:
            print(json.dumps(inventory(client, products[0]), sort_keys=True))
            return 0
        if args.remove:
            remove_buckets(client, products[0], args.purge_data, args.dry_run)
            return 0
        for product in products:
            create_buckets(client, product, args.dry_run)
        return 0
    except data_products.ProductError as error:
        print(f"RustFS bucket step refused: {error}", file=sys.stderr)
        return 2
    except RuntimeError as error:
        print(f"RustFS bucket step failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
