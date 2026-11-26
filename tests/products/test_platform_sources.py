"""The optional platform_sources block of product files (AC-13, AC-14, AC-16)."""

import sys
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings, strategies as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra/products"))

import data_products as dp  # noqa: E402

AUDIT_READ = {"owner": "read", "developer": "read", "analyst": "none", "writer": "read"}


def document(**extra):
    data = yaml.safe_load(dp.render_template("sales"))
    data.update(extra)
    return data


def test_absent_block_means_none_for_every_role():
    product = dp.parse_product(document(), "sales.yaml")
    assert product.platform_sources == {}
    assert all(product.platform_source_level("starrocks_audit", role) == "none" for role in dp.ROLES)
    assert dp.load_product(ROOT / "data-products/default.yaml").platform_sources == {}


def test_the_audit_product_reads_the_staging_table_except_analysts():
    product = dp.load_product(ROOT / "data-products/audit.yaml")
    assert product.platform_sources == {"starrocks_audit": AUDIT_READ}
    assert product.access["analyst"] == {"prod": "none", "uat": "none", "dev": "none"}


def test_the_template_documents_the_block_commented_out():
    text = dp.render_template("sales")
    assert "# platform_sources:\n#   starrocks_audit: {owner: none, developer: none, analyst: none, writer: none}" in text


@pytest.mark.parametrize(
    "block, message",
    [
        ({"rustfs_audit": AUDIT_READ}, "unknown keys: rustfs_audit"),
        ({"starrocks_audit": {**AUDIT_READ, "guest": "read"}}, "unknown keys: guest"),
        ({"starrocks_audit": {k: v for k, v in AUDIT_READ.items() if k != "writer"}}, "missing keys: writer"),
        ({"starrocks_audit": {**AUDIT_READ, "owner": "write"}}, "owner must be one of none, read"),
        ({"starrocks_audit": "read"}, "must be a mapping"),
        ([], "must be a mapping"),
    ],
)
def test_invalid_blocks_are_refused(block, message):
    with pytest.raises(dp.ProductError, match=message):
        dp.parse_product(document(platform_sources=block), "sales.yaml")


@settings(max_examples=100, deadline=None)
@given(st.fixed_dictionaries({role: st.sampled_from(dp.PLATFORM_SOURCE_LEVELS) for role in dp.ROLES}))
def test_every_combination_of_allowed_levels_is_accepted_as_written(levels):
    product = dp.parse_product(document(platform_sources={"starrocks_audit": levels}), "sales.yaml")
    assert product.platform_sources == {"starrocks_audit": levels}


@settings(max_examples=100, deadline=None)
@given(st.sampled_from(dp.ROLES), st.text(min_size=1, max_size=8).filter(lambda level: level not in dp.PLATFORM_SOURCE_LEVELS))
def test_any_other_level_is_refused(role, level):
    with pytest.raises(dp.ProductError):
        dp.parse_product(document(platform_sources={"starrocks_audit": {**AUDIT_READ, role: level}}), "sales.yaml")
