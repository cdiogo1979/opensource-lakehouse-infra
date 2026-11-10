#!/usr/bin/env python3
"""Verify RustFS temporary S3 credentials enforce a single environment prefix."""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENDPOINT = "http://127.0.0.1:9000"
REGION = "us-east-1"
STS_NAMESPACE = {"s": "https://sts.amazonaws.com/doc/2011-06-15/"}


def protected_secret(name: str) -> str:
    path = ROOT / ".runtime" / "credentials" / name
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"Required protected credential is unavailable: {name}")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError(f"Required protected credential is empty: {name}")
    return value


class SignedS3:
    def __init__(self, access_key: str, secret_key: str, session_token: str = "") -> None:
        self.access_key = access_key
        self.secret_key = secret_key
        self.session_token = session_token

    def request(self, method: str, path: str, body: bytes = b"", content_type: str = "") -> int:
        now = dt.datetime.now(dt.timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date = now.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(body).hexdigest()
        headers = {
            "host": "127.0.0.1:9000",
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        if content_type:
            headers["content-type"] = content_type
        if self.session_token:
            headers["x-amz-security-token"] = self.session_token
        signed_headers = ";".join(sorted(headers))
        canonical_headers = "".join(f"{name}:{headers[name].strip()}\n" for name in sorted(headers))
        canonical_request = (
            f"{method}\n{path}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        )
        scope = f"{date}/{REGION}/s3/aws4_request"
        string_to_sign = (
            f"AWS4-HMAC-SHA256\n{amz_date}\n{scope}\n"
            f"{hashlib.sha256(canonical_request.encode()).hexdigest()}"
        )

        def sign(key: bytes, value: str) -> bytes:
            return hmac.new(key, value.encode(), hashlib.sha256).digest()

        signing_key = sign(("AWS4" + self.secret_key).encode(), date)
        signing_key = sign(signing_key, REGION)
        signing_key = sign(signing_key, "s3")
        signing_key = sign(signing_key, "aws4_request")
        signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
        headers["authorization"] = (
            f"AWS4-HMAC-SHA256 Credential={self.access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        request = urllib.request.Request(
            f"{ENDPOINT}{path}", data=body or None, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                response.read()
                return response.status
        except urllib.error.HTTPError as error:
            error.read()
            return error.code
        except (OSError, TimeoutError) as error:
            raise RuntimeError("RustFS S3 request failed; verify the service health") from error


def assume_scoped_session(root_client: SignedS3, probe_key: str) -> SignedS3:
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
                "Resource": ["arn:aws:s3:::bucket-default-dev"],
            },
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                "Resource": [f"arn:aws:s3:::bucket-default-dev/{probe_key}"],
            },
        ],
    }
    body = urllib.parse.urlencode(
        {
            "Action": "AssumeRole",
            "Version": "2011-06-15",
            "DurationSeconds": "900",
            "RoleArn": "arn:aws:iam::000000000000:role/lakehouse-default-dev",
            "RoleSessionName": "lakehouse-u3-verify",
            "Policy": json.dumps(policy, separators=(",", ":")),
        }
    ).encode()
    # STS is the root POST endpoint; the request signer includes its form body.
    response_xml = request_sts(root_client, body)
    credentials = ET.fromstring(response_xml).find(".//s:Credentials", STS_NAMESPACE)
    if credentials is None:
        raise RuntimeError("RustFS STS response did not include temporary credentials")
    value = lambda tag: credentials.findtext(f"s:{tag}", default="", namespaces=STS_NAMESPACE)
    access_key, secret_key, session_token = (
        value("AccessKeyId"), value("SecretAccessKey"), value("SessionToken")
    )
    if not all((access_key, secret_key, session_token)):
        raise RuntimeError("RustFS STS response contained incomplete temporary credentials")
    return SignedS3(access_key, secret_key, session_token)


def request_sts(client: SignedS3, body: bytes) -> bytes:
    now = dt.datetime.now(dt.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date = now.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(body).hexdigest()
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "host": "127.0.0.1:9000",
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
    }
    signed_headers = ";".join(sorted(headers))
    canonical_headers = "".join(f"{name}:{headers[name].strip()}\n" for name in sorted(headers))
    canonical_request = f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    scope = f"{date}/{REGION}/s3/aws4_request"
    string_to_sign = (
        f"AWS4-HMAC-SHA256\n{amz_date}\n{scope}\n"
        f"{hashlib.sha256(canonical_request.encode()).hexdigest()}"
    )

    def sign(key: bytes, value: str) -> bytes:
        return hmac.new(key, value.encode(), hashlib.sha256).digest()

    signing_key = sign(("AWS4" + client.secret_key).encode(), date)
    signing_key = sign(signing_key, REGION)
    signing_key = sign(signing_key, "s3")
    signing_key = sign(signing_key, "aws4_request")
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
    headers["authorization"] = (
        f"AWS4-HMAC-SHA256 Credential={client.access_key}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    request = urllib.request.Request(f"{ENDPOINT}/", data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        error.read()
        raise RuntimeError(f"RustFS AssumeRole failed with HTTP {error.code}") from error
    except (OSError, TimeoutError) as error:
        raise RuntimeError("RustFS STS request failed; verify the service health") from error


def main() -> None:
    root = SignedS3(
        protected_secret("rustfs-access-key"), protected_secret("rustfs-secret-key")
    )
    object_key = f"default_lhdev/.bootstrap-sts-probe-{secrets.token_hex(8)}.txt"
    session = assume_scoped_session(root, object_key)
    encoded_key = urllib.parse.quote(object_key, safe="/")
    dev_bucket_list = session.request("GET", "/bucket-default-dev")
    prod_bucket_list = session.request("GET", "/bucket-default")
    dev_write = session.request("PUT", f"/bucket-default-dev/{encoded_key}", b"temporary probe", "text/plain")
    prod_write = session.request("PUT", f"/bucket-default/{encoded_key}", b"must be denied", "text/plain")
    if dev_bucket_list != 200 or prod_bucket_list != 403 or dev_write not in (200, 201) or prod_write != 403:
        raise RuntimeError(
            "RustFS STS scope check failed "
            f"(dev-list={dev_bucket_list}, prod-list={prod_bucket_list}, "
            f"dev-write={dev_write}, prod-write={prod_write})"
        )
    cleanup = session.request("DELETE", f"/bucket-default-dev/{encoded_key}")
    if cleanup not in (200, 204):
        raise RuntimeError(f"RustFS STS probe cleanup failed with HTTP {cleanup}")
    print("RustFS STS passed: temporary credentials were limited to the requested dev probe path.")
    print("The dev probe object was removed; production list/write were denied.")


if __name__ == "__main__":
    main()
