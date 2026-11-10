"""Contracts for per-product RustFS policies and buckets (FR-4, FR-11, BR-4, BR-8)."""

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policies = load("rustfs_product_policies", "infra/rustfs/bootstrap-policies.py")
buckets = load("rustfs_product_buckets", "infra/rustfs/bootstrap-buckets.py")
dp = policies.data_products


def product(name, **access):
    data = yaml.safe_load(dp.render_template(name))
    for role, levels in access.items():
        data["access"][role] = levels
    return dp.parse_product(data, f"{name}.yaml")


def test_default_matrix_is_unchanged():
    assert policies.ACCESS_MATRIX["role-default-developer"] == {
        "bucket-default": "read", "bucket-default-uat": "read", "bucket-default-dev": "read_write",
    }
    assert policies.ACCESS_MATRIX["role-default-analyst"] == {"bucket-default": "read"}
    assert policies.ACCESS_MATRIX["role-platform-admin"] == policies.ACCESS_MATRIX["role-default-owner"]


def test_levels_follow_the_product_file_and_platform_admin_spans_products():
    sales = product("sales", analyst={"prod": "read", "uat": "read", "dev": "none"}, writer={"prod": "none", "uat": "write", "dev": "manage"})
    matrix = policies.product_access_matrix([dp.load_product(ROOT / "data-products/default.yaml"), sales])
    assert matrix["role-sales-analyst"] == {"bucket-sales": "read", "bucket-sales-uat": "read"}
    assert matrix["role-sales-writer"] == {"bucket-sales-uat": "read_write", "bucket-sales-dev": "manage"}
    admin = matrix["role-platform-admin"]
    assert set(admin) == {"bucket-default", "bucket-default-uat", "bucket-default-dev", "bucket-sales", "bucket-sales-uat", "bucket-sales-dev"}
    assert set(admin.values()) == {"manage"}
    document = policies.policy_document("role-sales-writer", matrix)
    resources = {r for statement in document["Statement"] for r in statement["Resource"]}
    assert "arn:aws:s3:::bucket-sales" not in resources and "arn:aws:s3:::bucket-default" not in resources


class FakeAdmin:
    def __init__(self, policies_by_name=None):
        self.policies = dict(policies_by_name or {})
        self.writes = []

    def request(self, method, path, query=None, body=b""):
        name = (query or {}).get("name")
        if method == "GET" and path.endswith("/info-canned-policy"):
            if name not in self.policies:
                return 404, b""
            return 200, json.dumps({"policy": self.policies[name]}).encode()
        if method == "PUT" and path.endswith("/add-canned-policy"):
            self.policies[name] = json.loads(body)
            self.writes.append(("put", name))
            return 200, b""
        if method == "DELETE" and path.endswith("/remove-canned-policy"):
            self.policies.pop(name, None)
            self.writes.append(("delete", name))
            return 200, b""
        raise AssertionError((method, path))


def test_converge_rewrites_a_differing_product_policy_but_dry_run_does_not():
    desired = policies.policy_document("role-default-analyst")
    other = policies.policy_document("role-default-owner")
    admin = FakeAdmin({"role-default-analyst": other})
    assert policies.ensure_policy(admin, "role-default-analyst", desired, converge=True, dry_run=True) == "updated"
    assert admin.writes == []
    assert policies.ensure_policy(admin, "role-default-analyst", desired, converge=True) == "updated"
    assert policies.canonical_policy(admin.policies["role-default-analyst"]) == policies.canonical_policy(desired)
    assert policies.ensure_policy(admin, "role-default-analyst", desired, converge=True) == "already-present"


def test_remove_policy_is_idempotent():
    admin = FakeAdmin({"role-sales-owner": {"Version": "2012-10-17", "Statement": []}})
    assert policies.remove_policy(admin, "role-sales-owner", dry_run=True) == "removed" and admin.writes == []
    assert policies.remove_policy(admin, "role-sales-owner", dry_run=False) == "removed"
    assert policies.remove_policy(admin, "role-sales-owner", dry_run=False) == "absent"


class FakeS3:
    def __init__(self, contents):
        self.contents = {bucket: list(keys) for bucket, keys in contents.items()}
        self.deleted = []

    def request(self, method, path, query=None, body=b""):
        parts = path.strip("/").split("/", 1)
        bucket = parts[0]
        if method == "HEAD":
            return (200 if bucket in self.contents else 404), b""
        if method == "PUT":
            self.contents[bucket] = []
            return 200, b""
        if method == "GET" and query and "versions" in query:
            versions = "".join(f"<Version><Key>{k}</Key><VersionId>null</VersionId></Version>" for k in self.contents[bucket])
            return 200, f"<ListVersionsResult><IsTruncated>false</IsTruncated>{versions}</ListVersionsResult>".encode()
        if method == "DELETE" and len(parts) == 2:
            self.contents[bucket].remove(parts[1])
            self.deleted.append(path)
            return 204, b""
        if method == "DELETE":
            assert not self.contents[bucket], "bucket must be empty before deletion"
            del self.contents[bucket]
            return 204, b""
        raise AssertionError((method, path))


def test_create_inventory_and_remove_buckets():
    sales = product("sales")
    s3 = FakeS3({"bucket-sales": ["lakehouse/sales_lh/t/data/1.parquet"]})
    assert buckets.create_buckets(s3, sales, dry_run=False) == 2
    assert buckets.inventory(s3, sales) == {"prod": 1, "uat": 0, "dev": 0}
    with pytest.raises(RuntimeError, match="--purge-data"):
        buckets.remove_buckets(s3, sales, purge=False, dry_run=False)
    assert set(s3.contents) == set(sales.buckets())
    buckets.remove_buckets(s3, sales, purge=True, dry_run=True)
    assert set(s3.contents) == set(sales.buckets())
    buckets.remove_buckets(s3, sales, purge=True, dry_run=False)
    assert s3.contents == {}
    assert buckets.remove_buckets(s3, sales, purge=False, dry_run=False) == 0


def test_removal_refuses_the_default_product(capsys, monkeypatch):
    monkeypatch.setattr(buckets, "read_secret", lambda name: pytest.fail("secrets read before the default guard"))
    assert policies.main(["--remove", "--product", str(ROOT / "data-products/default.yaml")]) == 2
    assert buckets.main(["--remove", "--product", str(ROOT / "data-products/default.yaml")]) == 2
    assert "cannot be removed" in capsys.readouterr().err
