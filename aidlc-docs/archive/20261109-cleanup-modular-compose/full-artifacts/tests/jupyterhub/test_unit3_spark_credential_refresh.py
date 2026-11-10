"""Contract checks separating user JWT renewal from S3 credential refresh."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_exact_broker_user_jwt_is_used_and_oauth_identity_refresh_is_disabled():
    source = (ROOT / "infra/jupyter/singleuser/lakehouse_spark.py").read_text()
    assert "broker_token = request_user_token()" in source
    assert 'os.environ["LAKEHOUSE_INITIAL_ACCESS_TOKEN"] = broker_token.access_token' in source
    assert '"local.lakehouse.spark.auth.LakehouseTokenAuthManager"' in source
    assert '.config(prefix + ".token", broker_token.access_token)' not in source
    assert "refresh_token" not in source
    assert '"client.refresh-credentials-enabled", "false"' not in source


def test_no_static_s3_or_root_credential_fallback_is_configured_for_spark():
    spark_source = (ROOT / "infra/jupyter/singleuser/lakehouse_spark.py").read_text()
    defaults = (ROOT / "infra/jupyter/singleuser/spark-defaults.conf").read_text()
    combined = (spark_source + defaults).lower()
    assert "rustfs_secret_key" not in combined
    assert "rustfs_access_key" not in combined
    assert "aws_secret_access_key" not in combined
    assert "aws_access_key_id" not in combined


def test_code_documents_distinct_iceberg_vended_credential_refresh_path():
    source = (ROOT / "infra/jupyter/singleuser/lakehouse_spark.py").read_text()
    assert '".header.X-Iceberg-Access-Delegation": "vended-credentials"' in source


def test_spark_error_and_configuration_redaction_covers_identity_credentials():
    source = (ROOT / "infra/jupyter/singleuser/lakehouse_spark.py").read_text()
    defaults = (ROOT / "infra/jupyter/singleuser/spark-defaults.conf").read_text()
    for pattern in (
        "spark.redaction.regex",
        "spark.sql.redaction.options.regex",
        "token",
        "credential",
    ):
        assert pattern in source
        assert pattern in defaults
