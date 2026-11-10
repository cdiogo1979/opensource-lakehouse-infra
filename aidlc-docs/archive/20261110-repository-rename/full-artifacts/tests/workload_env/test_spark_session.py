"""The platform Spark session module, lakehouse_spark (spark-session BR-S1 to BR-S6; P1, P2).

PySpark is replaced by a fake builder, so these tests run on the host. A real session
is started live in both images (Build and Test).
"""

import os
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
    assert name == "uat-load_sales" and applied == ls.catalog_settings("lakehouse_uat")
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
