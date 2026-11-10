"""Contracts and properties for the repo block, the bundle list, and DAG-ID mapping (FR-1, FR-2, BR-1, BR-2)."""

import json
import sys

import pytest
import yaml
from hypothesis import given, settings, strategies as st

from product_strategies import ROOT, dp, product_names, product_sets, workloads

sys.path.insert(0, str(ROOT / "infra/airflow"))
import importlib.util  # noqa: E402

SPEC = importlib.util.spec_from_file_location("validate_bundle_config", ROOT / "infra/airflow/validate-bundle-config.py")


def document(name="sales", repo=None):
    data = yaml.safe_load(dp.render_template(name))
    if repo is not None:
        data["repo"] = repo
    return data


REPO = {"url": "https://github.com/cdiogo1979/opensource-lakehouse.git", "prod_branch": "main", "uat_branch": "uat"}


def test_default_has_the_workload_repository():
    default = dp.load_product(ROOT / "data-products/default.yaml")
    assert default.repo == dp.Repo(REPO["url"], "main", "uat")
    assert [b["name"] for b in dp.bundle_config([default])] == ["default-main", "default-uat"]


def test_repo_is_optional_and_the_template_leaves_it_commented():
    assert dp.parse_product(document(), "sales.yaml").repo is None
    assert "# repo:" in (ROOT / "infra/products/template.yaml").read_text()


@pytest.mark.parametrize("url", [
    "http://github.com/x/y.git", "https://user:pw@github.com/x/y.git", "https://token@github.com/x/y.git",
    "https://github.com:8443/x/y.git", "https://github.com/x/y.git?ref=main", "https://github.com/x/y.git#frag",
    "ssh://git@github.com/x/y.git", "https://github.com/", "https://github.com/x/y y.git",
])
def test_credentials_and_unsafe_urls_are_refused(url):
    with pytest.raises(dp.ProductError):
        dp.parse_product(document(repo={**REPO, "url": url}), "sales.yaml")


@pytest.mark.parametrize("branch", ["", "-x", "a..b", "a//b", "a@{b", "release/", "x.", "main.lock", "with space"])
def test_invalid_branches_are_refused(branch):
    with pytest.raises(dp.ProductError):
        dp.parse_product(document(repo={**REPO, "uat_branch": branch}), "sales.yaml")


def test_unknown_repo_keys_and_missing_fields_are_refused():
    with pytest.raises(dp.ProductError, match="unknown keys"):
        dp.parse_product(document(repo={**REPO, "token": "x"}), "sales.yaml")
    with pytest.raises(dp.ProductError, match="missing keys"):
        dp.parse_product(document(repo={"url": REPO["url"]}), "sales.yaml")


def load_validator():
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    return module


# P1 — the generated list passes the validator and survives JSON (PBT-02)
@settings(print_blob=True)
@given(product_sets)
def test_p1_generated_bundle_lists_validate_and_round_trip(products):
    bundles = dp.bundle_config(products)
    text = json.dumps(bundles, separators=(",", ":"))
    assert json.loads(text) == bundles
    validator = load_validator()
    validator.validate(json.loads(text), expected=bundles)


# P2 — exactly two bundles per product with a repo, on the right branches (PBT-03)
@settings(print_blob=True)
@given(product_sets)
def test_p2_two_bundles_per_product_with_a_repo(products):
    bundles = {b["name"]: b for b in dp.bundle_config(products)}
    assert len(bundles) == 2 * sum(p.repo is not None for p in products)
    for product in products:
        main, uat = bundles.get(f"{product.name}-main"), bundles.get(f"{product.name}-uat")
        if product.repo is None:
            assert main is None and uat is None
        else:
            assert main["kwargs"]["tracking_ref"] == product.repo.prod_branch
            assert uat["kwargs"]["tracking_ref"] == product.repo.uat_branch
            assert main["kwargs"]["repo_url"] == uat["kwargs"]["repo_url"] == product.repo.url


# P3 — a DAG ID maps back to its product and environment (PBT-03)
@settings(print_blob=True)
@given(product_names, st.sampled_from(["main", "uat"]), workloads)
def test_p3_dag_id_maps_to_product_and_environment(name, env, workload):
    assert dp.product_for_dag_id(f"{name}-{env}-{workload}") == (name, env)


@pytest.mark.parametrize("dag_id", ["main-test_environment", "uat-x", "default-dev-x", "Default-main-x", "default-main-", "x-main-y",
                                    "lakehouse-main-x", None, 7])
def test_dag_ids_without_a_valid_product_prefix_map_to_nothing(dag_id):
    assert dp.product_for_dag_id(dag_id) is None


# P5 (advisory, PBT-04) — generating twice is identical
@settings(print_blob=True)
@given(product_sets)
def test_p5_generation_is_deterministic(products):
    assert dp.bundle_config(products) == dp.bundle_config(list(reversed(products)))
