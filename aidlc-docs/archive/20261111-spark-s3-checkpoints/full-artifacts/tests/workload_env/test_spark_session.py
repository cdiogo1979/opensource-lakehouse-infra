"""The platform Spark session module, lakehouse_spark (spark-session BR-S1 to BR-S6; P1, P2; s3-checkpoints R14 to R18, P3, P4).

PySpark is replaced by a fake builder, so these tests run on the host. A real session
is started live in both images (Build and Test).
"""

import json
import os
import re
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings, strategies as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra/workload-python/python"))
import lakehouse_spark as ls  # noqa: E402

SETTINGS = settings(derandomize=True, print_blob=True, max_examples=200)
AIRFLOW_ENV = {"LAKEHOUSE_TOKEN_PROVIDER": "airflow", **{name: f"value-{i}" for i, name in enumerate(ls.AIRFLOW_SETTINGS)}}


class FakeBuilder:
    def __init__(self):
        self.settings, self.name = {}, None

    def appName(self, name):
        self.name = name
        return self

    def config(self, key, value):
        self.settings[key] = value
        return self

    def getOrCreate(self):
        return ("session", self.name, dict(self.settings))


def fake_pyspark(active=None):
    sql = types.ModuleType("pyspark.sql")
    builder = FakeBuilder()
    sql.SparkSession = types.SimpleNamespace(builder=builder, getActiveSession=lambda: active)
    return {"pyspark": types.ModuleType("pyspark"), "pyspark.sql": sql}, builder


def test_an_airflow_run_gets_every_platform_setting_and_no_token_request():
    modules, _ = fake_pyspark()
    with patch.dict(os.environ, AIRFLOW_ENV, clear=True), patch.dict(sys.modules, modules), patch.object(ls, "request_user_token") as request:
        _, name, applied = ls.create_spark_session("uat-load_sales", catalog="lakehouse_uat")
    request.assert_not_called()
    assert name == "uat-load_sales" and applied == {**ls.catalog_settings("lakehouse_uat"), **ls.checkpoint_settings({})}
    assert applied["spark.sql.defaultCatalog"] == "lakehouse_uat"


def test_incomplete_airflow_settings_name_what_is_missing_and_never_fall_back():
    env = dict(AIRFLOW_ENV, JUPYTERHUB_API_TOKEN="t")
    del env["LAKEHOUSE_RUN_CAPABILITY"]
    with pytest.raises(RuntimeError, match="LAKEHOUSE_RUN_CAPABILITY missing"):
        ls.select_token_source(env)


def test_no_token_source_and_unknown_providers_are_errors():
    with pytest.raises(RuntimeError, match="No token source"):
        ls.select_token_source({})
    with pytest.raises(RuntimeError, match="Unsupported"):
        ls.select_token_source({"LAKEHOUSE_TOKEN_PROVIDER": "static", "JUPYTERHUB_API_TOKEN": "t"})
    with pytest.raises(RuntimeError, match="JupyterHub server token"):
        ls.select_token_source({"LAKEHOUSE_TOKEN_PROVIDER": "jupyter"})


def test_the_default_catalog_comes_from_the_argument_then_the_environment_then_lakehouse():
    for env, argument, expected in (({}, None, "lakehouse"), ({"LAKEHOUSE_POLARIS_CATALOG": "lakehouse_dev"}, None, "lakehouse_dev"),
                                    ({"LAKEHOUSE_POLARIS_CATALOG": "lakehouse_dev"}, "lakehouse_uat", "lakehouse_uat")):
        modules, _ = fake_pyspark()
        with patch.dict(os.environ, {**AIRFLOW_ENV, **env}, clear=True), patch.dict(sys.modules, modules):
            assert ls.create_spark_session("x", catalog=argument)[2]["spark.sql.defaultCatalog"] == expected


@pytest.mark.parametrize("name", ["", "x" * 101, "bad\nname", None])
def test_application_names_must_be_short_and_printable(name):
    with pytest.raises(ValueError):
        ls.create_spark_session(name)


def test_spark_defaults_keep_only_extensions_and_the_same_redaction():
    lines = [line for line in (ROOT / "infra/jupyter/singleuser/spark-defaults.conf").read_text().splitlines() if line.strip()]
    defaults = dict(line.split("=", 1) for line in lines)
    platform = ls.catalog_settings("lakehouse")
    assert defaults == {key: platform[key] for key in ("spark.sql.extensions", "spark.redaction.regex", "spark.sql.redaction.options.regex")}


# --- Properties ----------------------------------------------------------------------


@SETTINGS
@given(st.sampled_from(ls.CATALOGS))
def test_p1_every_session_configures_all_three_catalogs_and_holds_no_secret(default):
    applied = ls.catalog_settings(default)
    assert applied["spark.sql.defaultCatalog"] == default
    for catalog in ls.CATALOGS:
        prefix = f"spark.sql.catalog.{catalog}"
        keys = {key for key in applied if key == prefix or key.startswith(prefix + ".")}
        assert len(keys) == 9 and applied[prefix + ".warehouse"] == catalog
        assert applied[prefix + ".rest-metrics-reporting-enabled"] == "false"
        assert applied[prefix + ".rest.auth.type"] == ls.AUTH_MANAGER
    assert not any("token=" in value.lower() or value.startswith("eyJ") for value in applied.values())
    assert set(applied) - {k for k in applied if k.startswith("spark.sql.catalog.")} == {
        "spark.sql.extensions", "spark.sql.defaultCatalog", "spark.redaction.regex", "spark.sql.redaction.options.regex"}


def reference_source(env):
    """The decision table of BR-S3, written independently of the module."""
    provider, hub = env.get("LAKEHOUSE_TOKEN_PROVIDER"), bool(env.get("JUPYTERHUB_API_TOKEN"))
    if provider == "airflow":
        return "airflow" if all(env.get(name) for name in ls.AIRFLOW_SETTINGS) else "error"
    if provider == "jupyter":
        return "jupyter" if hub else "error"
    if provider is None:
        return "jupyter" if hub else "error"
    return "error"


environments = st.fixed_dictionaries(
    {},
    optional={
        "LAKEHOUSE_TOKEN_PROVIDER": st.sampled_from(["airflow", "jupyter", "static", ""]),
        "JUPYTERHUB_API_TOKEN": st.sampled_from(["", "hub-token"]),
        **{name: st.sampled_from(["", "set"]) for name in ls.AIRFLOW_SETTINGS},
    },
)


@SETTINGS
@given(environments)
def test_p2_the_token_source_follows_the_decision_table(env):
    expected = reference_source(env)
    if expected == "error":
        with pytest.raises(RuntimeError):
            ls.select_token_source(env)
    else:
        assert ls.select_token_source(env) == expected


# --- Checkpoint keys (s3-checkpoints R14 to R18) ----------------------------------------


def write_key(folder, bucket, secret="s3cr3t-value", access=None):
    path = folder / bucket
    path.write_text(json.dumps({"access_key": access or f"ckpt-{bucket}", "secret_key": secret}), encoding="utf-8")
    return path


def test_every_catalog_uses_resolving_file_io():
    applied = ls.catalog_settings("lakehouse")
    assert {applied[f"spark.sql.catalog.{c}.io-impl"] for c in ls.CATALOGS} == {"org.apache.iceberg.io.ResolvingFileIO"}


def test_without_mounted_keys_s3a_is_configured_with_no_key_at_all(tmp_path):
    assert ls.checkpoint_key_files(tmp_path / "absent") == {}
    applied = ls.checkpoint_settings({}, "eu-west-1")
    assert applied["spark.hadoop.fs.s3ckpt.impl"] == "org.apache.hadoop.fs.s3a.S3AFileSystem"
    assert applied["spark.hadoop.fs.s3a.aws.credentials.provider"] == "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider"
    assert applied["spark.hadoop.fs.s3a.endpoint.region"] == "eu-west-1"
    assert applied["spark.hadoop.fs.s3a.directory.marker.retention"] == "keep"
    assert not any(key.endswith((".access.key", ".secret.key")) for key in applied)
    assert "spark.hadoop.fs.s3.impl" not in applied and "spark.hadoop.fs.s3a.impl" not in applied


def test_mounted_keys_become_per_bucket_settings_only(tmp_path):
    write_key(tmp_path, "bucket-a-dev", "secret-a")
    write_key(tmp_path, "bucket-b-dev", "secret-b")
    applied = ls.checkpoint_settings(ls.checkpoint_key_files(tmp_path))
    assert applied["spark.hadoop.fs.s3a.bucket.bucket-a-dev.access.key"] == "ckpt-bucket-a-dev"
    assert applied["spark.hadoop.fs.s3a.bucket.bucket-b-dev.secret.key"] == "secret-b"
    assert "spark.hadoop.fs.s3a.access.key" not in applied and "spark.hadoop.fs.s3a.secret.key" not in applied


@pytest.mark.parametrize("content", ["not json", "[]", '{"access_key": "ckpt-bucket-a-dev"}', '{"access_key": "ckpt-other", "secret_key": "x"}',
                                     '{"access_key": "ckpt-bucket-a-dev", "secret_key": ""}', '{"access_key": "ckpt-bucket-a-dev", "secret_key": "x", "extra": 1}'])
def test_invalid_key_files_stop_the_session_without_showing_their_content(tmp_path, content):
    (tmp_path / "bucket-a-dev").write_text(content, encoding="utf-8")
    with pytest.raises(ValueError) as error:
        ls.checkpoint_key_files(tmp_path)
    assert str(error.value) == "The checkpoint key file for bucket-a-dev is invalid."


def test_symlinks_and_unexpected_entries_are_refused(tmp_path):
    target = write_key(tmp_path / "..", "bucket-a-dev")
    folder = tmp_path / "keys"
    folder.mkdir()
    (folder / "bucket-a-dev").symlink_to(target)
    with pytest.raises(ValueError, match="Unexpected entry"):
        ls.checkpoint_key_files(folder)
    (folder / "bucket-a-dev").unlink()
    (folder / "Not_A_Bucket").write_text("{}")
    with pytest.raises(ValueError, match="Unexpected entry"):
        ls.checkpoint_key_files(folder)


def test_the_key_repr_never_shows_the_secret():
    assert "s3cr3t" not in repr(ls.CheckpointKey("ckpt-bucket-a-dev", "s3cr3t"))


def test_the_session_merges_mounted_keys_and_the_redaction_covers_them(tmp_path):
    write_key(tmp_path, "bucket-a-prod")
    modules, _ = fake_pyspark()
    with patch.dict(os.environ, dict(AIRFLOW_ENV, AWS_REGION="us-east-1"), clear=True), patch.dict(sys.modules, modules), \
            patch.object(ls.checkpoint_key_files, "__defaults__", (tmp_path,)):
        applied = ls.create_spark_session("prod-job", catalog="lakehouse")[2]
    redaction = re.compile(applied["spark.redaction.regex"])
    for key in ("spark.hadoop.fs.s3a.bucket.bucket-a-prod.access.key", "spark.hadoop.fs.s3a.bucket.bucket-a-prod.secret.key"):
        assert key in applied and redaction.search(key)


bucket_names = st.from_regex(r"\A[a-z0-9][a-z0-9-]{1,20}[a-z0-9]\Z")
secrets_text = st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_", min_size=1, max_size=40)


@SETTINGS
@given(st.dictionaries(bucket_names, secrets_text, max_size=5))
def test_p3_settings_hold_one_key_pair_per_bucket_and_no_global_key(buckets):
    keys = {bucket: ls.CheckpointKey(f"ckpt-{bucket}", secret) for bucket, secret in buckets.items()}
    applied = ls.checkpoint_settings(keys)
    pairs = {key for key in applied if key.endswith((".access.key", ".secret.key"))}
    assert pairs == {f"spark.hadoop.fs.s3a.bucket.{b}.{kind}.key" for b in buckets for kind in ("access", "secret")}
    assert all(applied[f"spark.hadoop.fs.s3a.bucket.{b}.secret.key"] == s for b, s in buckets.items())


@SETTINGS
@given(bucket_names, secrets_text, st.dictionaries(st.text(max_size=8), st.one_of(st.text(max_size=8), st.integers()), max_size=3))
def test_p4_valid_key_files_round_trip_and_anything_else_is_refused(bucket, secret, extra):
    valid = {"access_key": f"ckpt-{bucket}", "secret_key": secret}
    assert ls.parse_checkpoint_key(bucket, json.dumps(valid)) == ls.CheckpointKey(f"ckpt-{bucket}", secret)
    altered = {**valid, **extra}
    if altered != valid:
        with pytest.raises(ValueError):
            ls.parse_checkpoint_key(bucket, json.dumps(altered))


def test_known_harmless_stream_warnings_are_lowered_to_errors_and_failures_are_ignored():
    calls = []

    class Configurator:
        @staticmethod
        def setLevel(name, level):
            calls.append((name, level))

    jvm = types.SimpleNamespace(org=types.SimpleNamespace(apache=types.SimpleNamespace(logging=types.SimpleNamespace(
        log4j=types.SimpleNamespace(Level=types.SimpleNamespace(ERROR="ERROR"), core=types.SimpleNamespace(config=types.SimpleNamespace(Configurator=Configurator)))))))
    ls._quiet_known_warnings(types.SimpleNamespace(_jvm=jvm))
    assert calls == [(name, "ERROR") for name in ls.QUIET_LOGGERS]
    ls._quiet_known_warnings(types.SimpleNamespace(_jvm=types.SimpleNamespace()))  # no log4j: ignored
    ls._quiet_known_warnings(("not", "a", "session"))  # no JVM: ignored
