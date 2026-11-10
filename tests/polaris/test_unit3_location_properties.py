"""Property-based checks for exact approved storage paths."""

import importlib.util
from pathlib import Path

import pytest
from hypothesis import given, strategies as st


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "verify_role_matrix", ROOT / "infra/spark-bootstrap/verify_role_matrix.py"
)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)

CATALOGS = list(verifier.PRODUCT.items())
EXPECTED_PRODUCT = {
    "lakehouse": ("default_lh", "prod", "bucket-default"),
    "lakehouse_uat": ("default_lhuat", "uat", "bucket-default-uat"),
    "lakehouse_dev": ("default_lhdev", "dev", "bucket-default-dev"),
}
SEGMENT_CHAR = st.characters(
    whitelist_categories=("Lu", "Ll", "Lt", "Lm", "Lo", "Nd"),
).filter(lambda character: character not in {"/", "\\"})
TABLES = st.text(SEGMENT_CHAR, min_size=1, max_size=40).filter(
    lambda text: text[0].isalnum() and all(char.isalnum() for char in text)
)


def test_contract_mapping_matches_independent_approved_catalog_mapping():
    assert verifier.PRODUCT == EXPECTED_PRODUCT


@given(st.sampled_from(CATALOGS), TABLES)
def test_approved_catalog_location_round_trips_exactly(catalog_row, table):
    catalog, (namespace, _environment, bucket) = catalog_row
    location = verifier.expected_table_location(catalog, namespace, table)
    assert location == f"s3://{bucket}/{catalog}/{namespace}/{table}"
    assert verifier.location_matches(location, catalog, namespace, table)


@given(st.sampled_from(CATALOGS), TABLES)
def test_duplicate_database_segment_is_rejected(catalog_row, table):
    catalog, (namespace, _environment, bucket) = catalog_row
    duplicate = f"s3://{bucket}/{catalog}/{namespace}/{namespace}/{table}"
    assert not verifier.location_matches(duplicate, catalog, namespace, table)


@given(st.sampled_from(CATALOGS), TABLES)
def test_cross_environment_bucket_is_rejected(catalog_row, table):
    catalog, (namespace, _environment, bucket) = catalog_row
    other_bucket = next(
        candidate
        for _other_catalog, (_other_namespace, _other_environment, candidate) in CATALOGS
        if candidate != bucket
    )
    cross_environment = f"s3://{other_bucket}/{catalog}/{namespace}/{table}"
    assert not verifier.location_matches(cross_environment, catalog, namespace, table)


@pytest.mark.parametrize("segment", ["", ".", "..", "../prod", "a/b", "a\\b", "%2e%2e"])
def test_malformed_or_traversal_segments_are_rejected(segment):
    assert not verifier.valid_path_segment(segment)


def test_non_string_path_segments_are_rejected():
    assert not verifier.valid_path_segment(None)
    with pytest.raises(ValueError):
        verifier.expected_table_location("lakehouse", "default_lh", None)


def test_cross_catalog_namespace_and_unknown_catalog_are_rejected():
    with pytest.raises(ValueError):
        verifier.expected_table_location("lakehouse", "default_lhdev", "table")
    with pytest.raises(ValueError):
        verifier.expected_table_location("unknown", "default_lh", "table")
