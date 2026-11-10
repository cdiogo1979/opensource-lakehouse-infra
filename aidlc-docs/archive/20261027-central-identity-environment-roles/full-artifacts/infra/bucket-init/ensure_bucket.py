#!/usr/bin/env python3
"""Wait for RustFS and ensure approved environment buckets exist without changing their data."""

import os
import time
from urllib.error import URLError
from urllib.request import urlopen

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


ENDPOINT = os.environ.get("S3_ENDPOINT", "http://object-store:9000")
BUCKETS = ("lake", "lake-dev", "lake-uat")


def wait_for_rustfs() -> None:
    for attempt in range(30):
        try:
            with urlopen(f"{ENDPOINT}/health/ready", timeout=3) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError):
            pass
        if attempt < 29:
            time.sleep(2)
    raise RuntimeError("RustFS did not become ready within 60 seconds.")


def ensure_bucket(bucket: str) -> None:
    client = boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=os.environ["RUSTFS_ACCESS_KEY"],
        aws_secret_access_key=os.environ["RUSTFS_SECRET_KEY"],
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        config=Config(s3={"addressing_style": "path"}),
    )

    try:
        client.head_bucket(Bucket=bucket)
        print(f"Bucket {bucket!r} already exists; preserving its objects.")
        return
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "")
        status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if code not in {"404", "NoSuchBucket"} and status != 404:
            raise

    try:
        client.create_bucket(Bucket=bucket)
        print(f"Bucket {bucket!r} created.")
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "")
        if code == "BucketAlreadyOwnedByYou":
            print(f"Bucket {bucket!r} already exists; preserving its objects.")
            return
        raise


if __name__ == "__main__":
    wait_for_rustfs()
    for bucket in BUCKETS:
        ensure_bucket(bucket)
