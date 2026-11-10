#!/usr/bin/env python3
"""Idempotently create the approved default-product RustFS buckets."""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import os
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUCKETS = ("bucket-default", "bucket-default-dev", "bucket-default-uat")


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

    def request(self, method: str, path: str) -> tuple[int, bytes]:
        body = b""
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
            f"{method}\n{path}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
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

        request = urllib.request.Request(
            f"{self.endpoint}{path}", data=body or None, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()
        except (OSError, TimeoutError) as error:
            raise RuntimeError("RustFS S3 request failed; verify the endpoint and service health") from error


def main() -> None:
    endpoint = os.environ.get("RUSTFS_S3_ENDPOINT", "http://127.0.0.1:9000")
    client = S3Client(endpoint, read_secret("rustfs-access-key"), read_secret("rustfs-secret-key"))
    for bucket in BUCKETS:
        status, _ = client.request("HEAD", f"/{bucket}")
        if status == 200:
            print(f"Bucket {bucket} exists; preserving its contents.")
            continue
        if status != 404:
            raise RuntimeError(f"Could not inspect RustFS bucket {bucket}; HTTP {status}")
        status, _ = client.request("PUT", f"/{bucket}")
        if status not in (200, 409):
            raise RuntimeError(f"Could not create RustFS bucket {bucket}; HTTP {status}")
        status, _ = client.request("HEAD", f"/{bucket}")
        if status != 200:
            raise RuntimeError(f"RustFS did not confirm bucket {bucket}; HTTP {status}")
        print(f"Created bucket {bucket}.")


if __name__ == "__main__":
    main()
