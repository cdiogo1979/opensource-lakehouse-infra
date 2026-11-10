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

Streaming checkpoints use ``s3ckpt://<bucket>/checkpoints/...`` on Hadoop S3A,
with the bucket's checkpoint key mounted at ``/run/secrets/lakehouse-checkpoints/<bucket>``
(one key for an Airflow run, the user's dev keys in Jupyter). Every catalog uses
``ResolvingFileIO``, so table paths keep Polaris-vended credentials while Iceberg's
streaming offsets under ``s3ckpt://`` go through S3A.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

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
CHECKPOINT_KEY_DIR = Path("/run/secrets/lakehouse-checkpoints")
CHECKPOINT_SCHEME = "s3ckpt"
RUSTFS_ENDPOINT = "http://rustfs:9000"
DEFAULT_REGION = "us-east-1"
BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
# Warnings every s3ckpt:// stream logs that need no action: Spark falls back from FileContext
# (S3A binds it only to s3a://), streams disable adaptive execution, and S3A finds no metrics file.
QUIET_LOGGERS = (
    "org.apache.spark.sql.execution.streaming.CheckpointFileManager",
    "org.apache.spark.sql.execution.streaming.ResolveWriteToStream",
    "org.apache.hadoop.metrics2.impl.MetricsConfig",
)


@dataclass(frozen=True)
class CheckpointKey:
    """The RustFS key of one bucket's ``checkpoints/`` prefix; never printed."""

    access_key: str
    secret_key: str = ""

    def __repr__(self) -> str:
        return f"CheckpointKey(access_key={self.access_key!r})"


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
            # s3:// table paths go to S3FileIO with vended credentials; s3ckpt:// checkpoints to S3A.
            prefix + ".io-impl": "org.apache.iceberg.io.ResolvingFileIO",
            prefix + ".header.Polaris-Realm": "lakehouse",
            prefix + ".header.X-Iceberg-Access-Delegation": "vended-credentials",
            # Best-effort scan and commit reports to Polaris: unused here, and the report of a
            # table-creating write arrives before the table exists, which logs a misleading WARN.
            prefix + ".rest-metrics-reporting-enabled": "false",
        })
    return settings


def parse_checkpoint_key(bucket: str, text: str) -> CheckpointKey:
    """The key in a mounted file: a JSON object with exactly ``access_key`` (``ckpt-<bucket>``) and ``secret_key``."""
    try:
        value = json.loads(text)
    except ValueError:
        value = None
    if not isinstance(value, dict) or set(value) != {"access_key", "secret_key"}:
        raise ValueError(f"The checkpoint key file for {bucket} is invalid.")
    access_key, secret_key = value["access_key"], value["secret_key"]
    if access_key != f"ckpt-{bucket}" or not isinstance(secret_key, str) or not secret_key:
        raise ValueError(f"The checkpoint key file for {bucket} is invalid.")
    return CheckpointKey(access_key, secret_key)


def checkpoint_key_files(directory: Path = CHECKPOINT_KEY_DIR) -> dict[str, CheckpointKey]:
    """Bucket -> key for every file mounted in ``directory``; an absent folder means no checkpoint keys."""
    if not directory.is_dir():
        return {}
    keys = {}
    for path in sorted(directory.iterdir()):
        if not BUCKET_PATTERN.fullmatch(path.name) or path.is_symlink() or not path.is_file():
            raise ValueError(f"Unexpected entry {path.name!r} in the checkpoint key folder.")
        keys[path.name] = parse_checkpoint_key(path.name, path.read_text(encoding="utf-8"))
    return keys


def checkpoint_settings(keys: Mapping[str, CheckpointKey], region: str = DEFAULT_REGION) -> dict[str, str]:
    """S3A settings for ``s3ckpt://``: one key per bucket and no global key, so any other bucket fails."""
    settings = {
        f"spark.hadoop.fs.{CHECKPOINT_SCHEME}.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
        "spark.hadoop.fs.s3a.endpoint": RUSTFS_ENDPOINT,
        "spark.hadoop.fs.s3a.endpoint.region": region,
        "spark.hadoop.fs.s3a.path.style.access": "true",
        "spark.hadoop.fs.s3a.connection.ssl.enabled": "false",
        # Keep directory markers: the default deletes parent markers up to ``checkpoints/`` itself,
        # which the key may not delete (logged as AccessDenied on every write).
        "spark.hadoop.fs.s3a.directory.marker.retention": "keep",
        "spark.hadoop.fs.s3a.aws.credentials.provider": "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
    }
    for bucket, key in sorted(keys.items()):
        if not BUCKET_PATTERN.fullmatch(bucket):
            raise ValueError(f"Invalid checkpoint bucket name {bucket!r}.")
        settings[f"spark.hadoop.fs.s3a.bucket.{bucket}.access.key"] = key.access_key
        settings[f"spark.hadoop.fs.s3a.bucket.{bucket}.secret.key"] = key.secret_key
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
    settings.update(checkpoint_settings(checkpoint_key_files(), os.environ.get("AWS_REGION") or DEFAULT_REGION))

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
    session = builder.getOrCreate()
    _quiet_known_warnings(session)
    return session


def _quiet_known_warnings(session) -> None:
    """Log only errors from ``QUIET_LOGGERS``; logging stays as it is when log4j is unavailable."""
    jvm = getattr(session, "_jvm", None)
    if jvm is None:
        return
    try:
        level = jvm.org.apache.logging.log4j.Level.ERROR
        for name in QUIET_LOGGERS:
            jvm.org.apache.logging.log4j.core.config.Configurator.setLevel(name, level)
    except Exception:  # noqa: BLE001 - quieter logs are optional, the session is not
        return
