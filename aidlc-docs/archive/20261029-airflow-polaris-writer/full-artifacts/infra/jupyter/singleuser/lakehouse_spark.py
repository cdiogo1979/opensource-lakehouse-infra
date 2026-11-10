"""Create identity-bound Spark sessions for the active JupyterHub user."""

from __future__ import annotations

import os

from lakehouse_broker_client import request_user_token


REDACTION_REGEX = r"(?i)secret|password|token|access[.]?key|credential"
CATALOGS = {
    "lakehouse": "lakehouse",
    "lakehouse_uat": "lakehouse_uat",
    "lakehouse_dev": "lakehouse_dev",
}


def create_spark_session(app_name: str = "lakehouse-user"):
    """Start a new Spark session with the exact broker-issued user JWT in memory."""
    from pyspark import SparkContext

    if SparkContext._active_spark_context is not None:
        raise RuntimeError("A Spark context already exists; start a fresh user session first.")

    catalog_name = os.environ.get("LAKEHOUSE_POLARIS_CATALOG", "lakehouse")
    if catalog_name not in CATALOGS:
        raise RuntimeError("The default Polaris catalog is not approved for this user session.")

    broker_token = request_user_token()
    # The JVM provider uses the same active Hub server identity for later
    # renewals. The JWT is intentionally kept out of Spark's public config.
    os.environ["LAKEHOUSE_TOKEN_PROVIDER"] = "jupyter"
    os.environ["LAKEHOUSE_INITIAL_ACCESS_TOKEN"] = broker_token.access_token
    from pyspark.sql import SparkSession

    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.redaction.regex", REDACTION_REGEX)
        .config("spark.sql.redaction.options.regex", REDACTION_REGEX)
        .config("spark.sql.defaultCatalog", catalog_name)
    )
    for catalog, warehouse in CATALOGS.items():
        prefix = f"spark.sql.catalog.{catalog}"
        settings = {
            "": "org.apache.iceberg.spark.SparkCatalog",
            ".type": "rest",
            ".uri": "http://polaris:8181/api/catalog",
            ".io-impl": "org.apache.iceberg.aws.s3.S3FileIO",
            ".rest.auth.type": "local.lakehouse.spark.auth.LakehouseTokenAuthManager",
            ".warehouse": warehouse,
            ".header.Polaris-Realm": "lakehouse",
            ".header.X-Iceberg-Access-Delegation": "vended-credentials",
        }
        for suffix, value in settings.items():
            builder = builder.config(prefix + suffix, value)
    return builder.getOrCreate()
