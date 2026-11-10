"""Contracts for the data product model: validation, collisions, locked names, and default."""

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra/products"))

import data_products as dp  # noqa: E402


def document(name="sales"):
    return yaml.safe_load(dp.render_template(name))


def write(directory, data):
    path = directory / f"{data['name']}.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_default_file_reproduces_todays_model():
    product = dp.load_product(ROOT / "data-products/default.yaml")
    assert [(e.catalog, e.namespace, e.bucket, e.mv_database) for e in product.environments] == [
        ("lakehouse", "default_lh", "bucket-default", "default_lh"),
        ("lakehouse_uat", "default_lhuat", "bucket-default-uat", "default_lhuat"),
        ("lakehouse_dev", "default_lhdev", "bucket-default-dev", "default_lhdev"),
    ]
    assert product.group_names() == tuple(f"role-default-{role}" for role in dp.ROLES)
    assert product.access == {
        "owner": {"prod": "manage", "uat": "manage", "dev": "manage"},
        "developer": {"prod": "read", "uat": "read", "dev": "write"},
        "analyst": {"prod": "read", "uat": "none", "dev": "none"},
        "writer": {"prod": "write", "uat": "write", "dev": "write"},
    }
    assert product.materialized_views["writer"] == {"prod": "author", "uat": "author", "dev": "author"}
    # CR-2: developers author MVs in dev, where their data access is write.
    assert product.materialized_views["developer"] == {"prod": "read", "uat": "read", "dev": "author"}
    assert product.jupyterhub == ("developer", "analyst")
    assert product.airflow == {"owner": "User", "developer": "User", "analyst": "User", "writer": "Viewer"}
    assert product.jenkins == {"developer": ("Job/Read", "Job/Build", "Job/Cancel", "Job/Workspace"), "analyst": ("Job/Read",)}
    assert product.writer_user == dp.WriterUser("srv-default-writer", ".runtime/credentials/srv-default-writer-password")
    assert product.protected


def test_template_round_trips_for_a_new_product():
    product = dp.parse_product(document("sales"), "sales.yaml")
    assert product.environment("uat").bucket == "bucket-sales-uat"
    assert product.groups["writer"] == "role-sales-writer"
    assert not product.protected


@pytest.mark.parametrize("name", ["a", "Sales", "1sales", "sales-eu", "x" * 21, "lakehouse", "polaris"])
def test_invalid_or_reserved_names_are_refused(name):
    with pytest.raises(dp.ProductError):
        dp.validate_name(name)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(extra=1),
        lambda d: d["environments"]["prod"].update(catalog="sales_catalog"),
        lambda d: d["environments"]["uat"].update(bucket="Bucket_Sales"),
        lambda d: d["environments"]["dev"].update(bucket="192.168.1.10"),
        lambda d: d["environments"]["dev"].update(namespace="sales_lh"),
        lambda d: d["groups"].update(owner="sales-owners"),
        lambda d: d["groups"].update(owner="role-sales-writer"),
        lambda d: d["groups"].update(analyst="role-other-analyst"),
        lambda d: d["access"]["analyst"].update(uat="admin"),
        lambda d: d["materialized_views"]["writer"].update(dev="write"),
        lambda d: d["apps"].update(jupyterhub=["guest"]),
        lambda d: d["apps"]["airflow"].update(owner="Op"),
        lambda d: d["apps"]["jenkins"].update(developer=["Overall/RunScripts"]),
        lambda d: d["apps"]["jenkins"].update(owner=["Job/Read"]),
        lambda d: d["apps"]["jenkins"].update(analyst=["Overall/Read", "Job/Read"]),
        lambda d: d["apps"]["jenkins"].update(developer=["Overall/Administer"]),
        lambda d: d["apps"]["jenkins"].update(analyst=[]),
        lambda d: d["writer_user"].update(username="writer"),
        lambda d: d["writer_user"].update(password_file="/etc/passwd"),
        lambda d: d["writer_user"].update(password_file=".runtime/credentials/../x"),
        lambda d: d.update(apiVersion="v2"),
    ],
)
def test_invalid_fields_are_refused(mutate):
    data = document()
    mutate(data)
    with pytest.raises(dp.ProductError):
        dp.parse_product(data, "sales.yaml")


def test_file_name_must_match_product_name(tmp_path):
    data = document("sales")
    path = tmp_path / "other.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(dp.ProductError, match="must be named sales.yaml"):
        dp.load_product(path)


def test_editable_names_within_the_pattern_are_accepted(tmp_path):
    data = document("sales")
    data["environments"]["prod"]["bucket"] = "sales-prod-data"
    data["groups"] = {role: f"role-sls-{role}" for role in dp.ROLES}
    data["writer_user"]["username"] = "srv-sales-etl"
    product = dp.load_product(write(tmp_path, data))
    assert product.environment("prod").bucket == "sales-prod-data"
    assert product.groups["owner"] == "role-sls-owner"


def test_collisions_across_products_are_refused(tmp_path):
    write(tmp_path, document("default"))
    sales = document("sales")
    sales["environments"]["dev"]["bucket"] = "bucket-default-dev"
    write(tmp_path, sales)
    with pytest.raises(dp.ProductError, match="share the bucket"):
        dp.load_all(tmp_path)


def test_group_token_collision_is_refused(tmp_path):
    write(tmp_path, document("default"))
    sales = document("sales")
    sales["groups"] = {role: f"role-default-{role}" for role in dp.ROLES}
    write(tmp_path, sales)
    with pytest.raises(dp.ProductError, match="group token"):
        dp.load_all(tmp_path)


def test_load_all_puts_default_first(tmp_path):
    for name in ("alpha", "default", "zeta"):
        write(tmp_path, document(name))
    assert [p.name for p in dp.load_all(tmp_path)] == ["default", "alpha", "zeta"]


def test_locked_names_refuse_renames(tmp_path):
    product = dp.parse_product(document("sales"), "sales.yaml")
    dp.write_state(product, tmp_path)
    state = dp.read_state("sales", tmp_path)
    dp.check_locked_names(product, state)  # unchanged is fine
    renamed = document("sales")
    renamed["environments"]["dev"]["namespace"] = "sales_development"
    with pytest.raises(dp.ProductError, match="environments.dev.namespace"):
        dp.check_locked_names(dp.parse_product(renamed, "sales.yaml"), state)
    edited_access = document("sales")
    edited_access["access"]["analyst"]["uat"] = "read"
    dp.check_locked_names(dp.parse_product(edited_access, "sales.yaml"), state)


def test_state_is_private_and_rebuilds_a_product(tmp_path):
    product = dp.parse_product(document("sales"), "sales.yaml")
    path = dp.write_state(product, tmp_path)
    assert path.stat().st_mode & 0o777 == 0o600
    rebuilt = dp.product_from_state(dp.read_state("sales", tmp_path))
    assert rebuilt.buckets() == product.buckets() and rebuilt.groups == product.groups
    assert all(level == "none" for row in rebuilt.access.values() for level in row.values())


def test_operation_lock_is_exclusive(tmp_path):
    with dp.operation_lock(tmp_path):
        with pytest.raises(dp.ProductError, match="Another data product operation"):
            with dp.operation_lock(tmp_path):
                pass
    with dp.operation_lock(tmp_path):
        pass


def test_group_pattern_and_app_helpers():
    products = [dp.parse_product(document("default"), "default.yaml"), dp.parse_product(document("sales"), "sales.yaml")]
    assert dp.GROUP_PATTERN.fullmatch("role-sales-owner") and not dp.GROUP_PATTERN.fullmatch("role-platform-admin-x")
    assert dp.jupyterhub_groups(products) == {
        "role-platform-admin", "role-default-developer", "role-default-analyst", "role-sales-developer", "role-sales-analyst",
    }
    mapping = dp.airflow_group_roles(products)
    assert mapping["role-sales-owner"] == "User" and mapping["role-platform-admin"] == "Admin"
    assert dp.starrocks_role("role-sales-owner") == "role_sales_owner"
    assert dp.catalog_role("role-sales-owner", "lakehouse") == "role-sales-owner-lakehouse-catalog"
    assert dp.namespace_location(products[1].environment("prod")) == "s3://bucket-sales/lakehouse/sales_lh/"
