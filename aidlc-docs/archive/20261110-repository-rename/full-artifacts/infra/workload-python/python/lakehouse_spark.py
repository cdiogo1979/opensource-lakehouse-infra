"""Start the lakehouse Spark session for workload code, in Airflow runs and Jupyter (BR-S1 to BR-S5).

The platform's only copy of the Polaris catalog, token-source and redaction
settings. Both images put this folder on the workload venv's path
(``lakehouse-platform.pth``), so Airflow run containers import it although their
``PYTHONPATH`` holds only the product bundle::

    from lakehouse_spark import create_spark_session
    spark = create_spark_session("uat-load_sales", catalog="lakehouse_uat")

Spark's ``LakehouseTokenAuthManager`` renews the token through the broker that
issued it: the Airflow run broker, or the user's JupyterHub broker. Tokens stay
in the process environment and never become Spark settings.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from lakehouse_broker_client import request_user_token

CATALOGS = ("lakehouse", "lakehouse_uat", "lakehouse_dev")
CATALOG_URI = "http://polaris:8181/api/catalog"
AUTH_MANAGER = "local.lakehouse.spark.auth.LakehouseTokenAuthManager"
ICEBERG_EXTENSIONS = "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
REDACTION_REGEX = r"(?i)secret|password|token|access[.]?key|credential"
AIRFLOW_SETTINGS = (
    "LAKEHOUSE_INITIAL_ACCESS_TOKEN",
    "LAKEHOUSE_TOKEN_BROKER_URL",
    "LAKEHOUSE_TOKEN_BROKER_CA",
    "LAKEHOUSE_RUN_HANDLE",
    "LAKEHOUSE_RUN_CAPABILITY",
)
HUB_BROKER_URL = "https://jupyterhub:8443/api/v1/token"
HUB_BROKER_CA = "/run/certs/jupyterhub-broker-ca.crt"
MAX_APP_NAME = 100


def catalog_settings(default_catalog: str) -> dict[str, str]:
    """Every Spark setting of a lakehouse session whose default catalog is ``default_catalog``."""
    if default_catalog not in CATALOGS:
        raise ValueError(f"Unknown Polaris catalog {default_catalog!r}; expected one of: {', '.join(CATALOGS)}.")
    settings = {
        "spark.sql.extensions": ICEBERG_EXTENSIONS,
        "spark.sql.defaultCatalog": default_catalog,
        "spark.redaction.regex": REDACTION_REGEX,
        "spark.sql.redaction.options.regex": REDACTION_REGEX,
    }
    for catalog in CATALOGS:
        prefix = f"spark.sql.catalog.{catalog}"
        settings.update({
            prefix: "org.apache.iceberg.spark.SparkCatalog",
            prefix + ".type": "rest",
            prefix + ".uri": CATALOG_URI,
            prefix + ".warehouse": catalog,
            prefix + ".rest.auth.type": AUTH_MANAGER,
            prefix + ".io-impl": "org.apache.iceberg.aws.s3.S3FileIO",
            prefix + ".header.Polaris-Realm": "lakehouse",
            prefix + ".header.X-Iceberg-Access-Delegation": "vended-credentials",
            # Best-effort scan and commit reports to Polaris: unused here, and the report of a
            # table-creating write arrives before the table exists, which logs a misleading WARN.
            prefix + ".rest-metrics-reporting-enabled": "false",
        })
    return settings


def select_token_source(environ: Mapping[str, str]) -> str:
    """``airflow`` or ``jupyter`` for this process; incomplete or missing settings are an error, never a fallback."""
    provider = environ.get("LAKEHOUSE_TOKEN_PROVIDER")
    if provider == "airflow":
        missing = [name for name in AIRFLOW_SETTINGS if not environ.get(name)]
        if missing:
            raise RuntimeError(f"The Airflow run's token settings are incomplete: {', '.join(missing)} missing.")
        return "airflow"
    if provider == "jupyter" or (provider is None and environ.get("JUPYTERHUB_API_TOKEN")):
        if not environ.get("JUPYTERHUB_API_TOKEN"):
            raise RuntimeError("The JupyterHub server token is unavailable.")
        return "jupyter"
    if provider is not None:
        raise RuntimeError("Unsupported Lakehouse token provider.")
    raise RuntimeError("No token source: start Spark from an Airflow run or a JupyterHub server.")


def _seed_jupyter_token() -> None:
    """Put the user's current token from the Hub broker into the process environment for the JVM."""
    broker_token = request_user_token()
    os.environ["LAKEHOUSE_TOKEN_PROVIDER"] = "jupyter"  # nosec B105 - provider selector, not a credential.
    os.environ["LAKEHOUSE_INITIAL_ACCESS_TOKEN"] = broker_token.access_token
    os.environ.setdefault("LAKEHOUSE_TOKEN_BROKER_URL", HUB_BROKER_URL)
    os.environ.setdefault("LAKEHOUSE_TOKEN_BROKER_CA", HUB_BROKER_CA)


def create_spark_session(app_name: str = "lakehouse-user", catalog: str | None = None):
    """The lakehouse Spark session with ``catalog`` as its default catalog.

    ``catalog`` defaults to ``LAKEHOUSE_POLARIS_CATALOG``, else ``lakehouse``. An
    active session is returned when its default catalog matches; with another
    catalog, the kernel has to be restarted.
    """
    if not isinstance(app_name, str) or not 1 <= len(app_name) <= MAX_APP_NAME or not app_name.isprintable():
        raise ValueError(f"The Spark application name must be 1 to {MAX_APP_NAME} printable characters.")
    catalog = catalog or os.environ.get("LAKEHOUSE_POLARIS_CATALOG") or "lakehouse"
    settings = catalog_settings(catalog)

    from pyspark.sql import SparkSession

    active = SparkSession.getActiveSession()
    if active is not None:
        if active.conf.get("spark.sql.defaultCatalog", None) == catalog:
            return active
        raise RuntimeError(f"A Spark session for another catalog is running; restart the kernel to use {catalog}.")

    if select_token_source(os.environ) == "jupyter":
        _seed_jupyter_token()
    builder = SparkSession.builder.appName(app_name)
    for key, value in settings.items():
        builder = builder.config(key, value)
    return builder.getOrCreate()
