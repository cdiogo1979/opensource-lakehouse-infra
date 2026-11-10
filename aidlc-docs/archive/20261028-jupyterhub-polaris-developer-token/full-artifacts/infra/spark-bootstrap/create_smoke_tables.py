"""Create and verify the default product's three Iceberg smoke tables."""

from __future__ import annotations

import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from pyspark.sql import SparkSession


CLIENT_ID = "write-service-account"
CATALOG_URI = "http://polaris:8181/api/catalog"
KEYCLOAK_TOKEN_URI = "http://keycloak:8080/realms/lakehouse/protocol/openid-connect/token"
SECRET_FILE = Path("/run/secrets/keycloak-writer-client-secret")
PRODUCT = (
    ("lakehouse", "default_lh", "prod"),
    ("lakehouse_uat", "default_lhuat", "uat"),
    ("lakehouse_dev", "default_lhdev", "dev"),
)


def sql_name(*parts: str) -> str:
    return ".".join(f"`{part.replace('`', '``')}`" for part in parts)


def writer_token(secret: str) -> str:
    form = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": secret,
    }).encode()
    request = urllib.request.Request(
        KEYCLOAK_TOKEN_URI,
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            token = json.loads(response.read()).get("access_token")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        raise RuntimeError(f"Could not obtain the writer OAuth token ({type(error).__name__}).") from error
    if not isinstance(token, str) or not token:
        raise RuntimeError("Keycloak did not return a writer OAuth token.")
    return token


def main() -> None:
    if SECRET_FILE.is_symlink() or not SECRET_FILE.is_file():
        raise RuntimeError("Protected writer OAuth secret is unavailable.")
    secret = SECRET_FILE.read_text(encoding="utf-8").splitlines()[0]
    if not secret:
        raise RuntimeError("Protected writer OAuth secret is empty.")
    token = writer_token(secret)

    builder = (
        SparkSession.builder.appName("default-product-smoke-table-bootstrap")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.defaultCatalog", "lakehouse")
        .config("spark.redaction.regex", "(?i)secret|password|token|access[.]?key|credential")
        .config("spark.sql.redaction.options.regex", "(?i)secret|password|token|access[.]?key|credential")
    )
    for catalog, _, _ in PRODUCT:
        prefix = f"spark.sql.catalog.{catalog}"
        settings = {
            "": "org.apache.iceberg.spark.SparkCatalog",
            ".type": "rest",
            ".uri": CATALOG_URI,
            ".io-impl": "org.apache.iceberg.aws.s3.S3FileIO",
            ".token": token,
            ".token-refresh-enabled": "false",
            ".warehouse": catalog,
            ".header.Polaris-Realm": "lakehouse",
            ".header.X-Iceberg-Access-Delegation": "vended-credentials",
        }
        for suffix, value in settings.items():
            builder = builder.config(prefix + suffix, value)

    spark = builder.getOrCreate()
    try:
        spark.sparkContext.setLogLevel("WARN")
        for catalog, namespace, environment in PRODUCT:
            table = sql_name(catalog, namespace, "bootstrap_smoke_test")
            spark.sql(
                f"CREATE TABLE IF NOT EXISTS {table} "
                "(id BIGINT, environment STRING) USING iceberg"
            )
            count = spark.sql(f"SELECT count(*) AS row_count FROM {table}").first()["row_count"]
            if count == 0:
                spark.sql(
                    f"INSERT INTO {table} VALUES "
                    f"(1, '{environment}')"
                )
            rows = spark.sql(f"SELECT id, environment FROM {table}").collect()
            if [(row["id"], row["environment"]) for row in rows] != [(1, environment)]:
                raise RuntimeError(f"Smoke-table content is not the expected single row for {environment}.")
            location_rows = spark.sql(f"DESCRIBE TABLE EXTENDED {table}").collect()
            location = next(
                (row["data_type"] for row in location_rows if row["col_name"].strip().lower() == "location"),
                None,
            )
            expected_location = {
                "lakehouse": "s3://bucket-default/lakehouse/default_lh/bootstrap_smoke_test",
                "lakehouse_dev": "s3://bucket-default-dev/lakehouse_dev/default_lhdev/bootstrap_smoke_test",
                "lakehouse_uat": "s3://bucket-default-uat/lakehouse_uat/default_lhuat/bootstrap_smoke_test",
            }[catalog]
            if not location or location.rstrip("/") != expected_location:
                raise RuntimeError(
                    f"Smoke-table location does not match the approved {environment} path "
                    f"s3://<bucket>/{catalog}/{namespace}/bootstrap_smoke_test/."
                )
            print(f"Verified {catalog}.{namespace}.bootstrap_smoke_test ({environment}; exact path).")
        print("Spark verified smoke-table creation, readback, and vended-credential access for all environments.")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
