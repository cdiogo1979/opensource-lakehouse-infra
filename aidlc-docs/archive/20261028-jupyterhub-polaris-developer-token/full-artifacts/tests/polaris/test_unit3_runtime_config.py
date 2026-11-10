"""Focused Polaris runtime-property tests; tests do not touch .runtime."""

import importlib.util
from pathlib import Path
import tempfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "prepare_lakehouse_runtime", ROOT / "scripts/prepare-lakehouse-runtime.py"
)
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


def property_map(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator:
            result[key.strip()] = value.strip()
    return result


def test_polaris_runtime_uses_verified_duration_cache_and_bounded_pool():
    properties = property_map((ROOT / "infra/polaris/oidc.properties").read_text())

    assert properties['polaris.features."STORAGE_CREDENTIAL_DURATION_SECONDS"'] == "3600"
    assert properties['polaris.features."STORAGE_CREDENTIAL_CACHE_DURATION_SECONDS"'] == "600"
    assert properties['polaris.features."STORAGE_CREDENTIAL_DURATION_SECONDS"'] == str(
        runtime.POLARIS_CREDENTIAL_DURATION_SECONDS
    )
    assert properties['polaris.features."STORAGE_CREDENTIAL_CACHE_DURATION_SECONDS"'] == str(
        runtime.POLARIS_CREDENTIAL_CACHE_SECONDS
    )
    assert properties["polaris.storage.max-http-connections"] == "8"
    assert properties["polaris.storage.connection-acquisition-timeout"] == "PT1S"
    assert properties["polaris.storage.connect-timeout"] == "PT1S"
    assert properties["polaris.storage.read-timeout"] == "PT2S"
    assert properties["quarkus.management.host"] == "127.0.0.1"


def test_runtime_generator_preserves_oidc_template_and_emits_no_secret_diagnostic():
    properties = property_map((ROOT / "infra/polaris/oidc.properties").read_text())
    assert properties["quarkus.oidc.token.issuer"].endswith("/realms/lakehouse")
    assert properties["quarkus.oidc.client-id"] == "polaris"
    assert "secret" not in runtime.runtime_ready_message().lower()
    assert "token" not in runtime.runtime_ready_message().lower()


def test_managed_property_merge_preserves_protected_unrelated_values():
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "polaris-application.properties"
        destination.write_text(
            "quarkus.datasource.password=DO_NOT_REPLACE\n"
            "polaris.storage.aws.secret-key=KEEP_EXISTING\n"
        )
        runtime.merge_managed_properties(
            destination,
            (ROOT / "infra/polaris/oidc.properties").read_text(),
        )
        result = property_map(destination.read_text())

    assert result["quarkus.datasource.password"] == "DO_NOT_REPLACE"
    assert result["polaris.storage.aws.secret-key"] == "KEEP_EXISTING"
    assert result['polaris.features."STORAGE_CREDENTIAL_DURATION_SECONDS"'] == "3600"
    assert result['polaris.features."STORAGE_CREDENTIAL_CACHE_DURATION_SECONDS"'] == "600"


def test_cache_must_be_positive_and_strictly_shorter_than_credential_lifetime():
    runtime.validate_credential_timing(900, 600)
    for duration, cache in ((0, 0), (900, 900), (300, 600), (-1, 1), (1, 0)):
        with pytest.raises(ValueError):
            runtime.validate_credential_timing(duration, cache)
