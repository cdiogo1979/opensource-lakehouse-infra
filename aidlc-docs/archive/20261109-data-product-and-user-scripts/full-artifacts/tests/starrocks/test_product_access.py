"""Contracts for StarRocks access across data products (FR-6, BR-3, BR-8)."""

import pytest
import yaml

from starrocks_strategies import ROOT, bootstrap, sr

dp = sr.data_products
DEFAULT = dp.load_product(ROOT / "data-products/default.yaml")
SALES = dp.parse_product(yaml.safe_load(dp.render_template("sales")), "sales.yaml")
MODEL = sr.build_model([DEFAULT, SALES])


def test_every_product_group_maps_to_its_role_and_platform_admin_is_kept():
    assert MODEL.group_roles["role-sales-analyst"] == "role_sales_analyst"
    assert MODEL.group_roles["role-platform-admin"] == "role_platform_admin"
    assert MODEL.managed_roles[-1] == "role_platform_admin" and len(MODEL.managed_roles) == 9
    assert set(MODEL.mv_databases) == {"default_lh", "default_lhuat", "default_lhdev", "sales_lh", "sales_lhuat", "sales_lhdev"}


def test_product_roles_only_reach_their_own_databases():
    grants = bootstrap.role_grants(MODEL)
    for grant in grants:
        if grant.role.startswith("role_sales_") and grant.object != "CATALOG":
            assert grant.object.endswith(("sales_lh", "sales_lhuat", "sales_lhdev")), grant
        if grant.role.startswith("role_default_") and grant.object != "CATALOG":
            assert "sales" not in grant.object, grant
    admin_mvs = {g.object for g in grants if g.role == "role_platform_admin" and g.catalog == sr.INTERNAL_CATALOG}
    assert "DATABASE sales_lhdev" in admin_mvs and "DATABASE default_lh" in admin_mvs


def test_database_scoped_grants_render_and_parse_round_trip():
    grant = bootstrap.Grant("role_sales_writer", "INSERT", "lakehouse", "ALL TABLES IN DATABASE sales_lh")
    sql = bootstrap.render_grant(grant)
    assert sql == "SET CATALOG `lakehouse`;\nGRANT INSERT ON ALL TABLES IN DATABASE `sales_lh` TO ROLE `role_sales_writer`;"
    rows = [{"Catalog": "lakehouse", "Grants": "GRANT INSERT, SELECT ON ALL TABLES IN DATABASE sales_lh TO ROLE 'role_sales_writer'"}]
    parsed, unknown = bootstrap.parse_role_grants("role_sales_writer", rows)
    assert unknown == [] and grant in parsed


def test_all_on_database_covers_the_privileges_starrocks_reports():
    desired = bootstrap.role_grants(MODEL)
    reported = {bootstrap.Grant("role_sales_owner", p, "lakehouse", "DATABASE sales_lh") for p in ("CREATE TABLE", "DROP", "ALTER", "CREATE VIEW")}
    plan = bootstrap.plan_grants(desired | reported, desired, MODEL.managed_roles)
    assert plan.revoke == []


def test_removed_product_roles_stop_being_managed():
    remaining = sr.build_model([DEFAULT])
    stale = bootstrap.Grant("role_platform_admin", "ALL", sr.INTERNAL_CATALOG, "DATABASE sales_lh")
    plan = bootstrap.plan_grants(bootstrap.role_grants(remaining) | {stale}, bootstrap.role_grants(remaining), remaining.managed_roles)
    assert plan.revoke == [stale]


class FakeRunner:
    def __init__(self, mv_tables):
        self.mv_tables = mv_tables
        self.executed = []

    def query(self, sql, operation):
        if sql.startswith("SHOW DATABASES FROM"):
            return [{"Database": name} for name in self.mv_tables]
        if sql.startswith("SHOW TABLES FROM"):
            database = sql.split(".")[-1].strip("`;")
            return [{"Tables_in": t} for t in self.mv_tables[database]]
        if sql.startswith("SHOW ROLES"):
            return [{"Name": role} for role in MODEL.managed_roles]
        return []

    def execute(self, sql, operation):
        self.executed.append(sql)


def test_removal_refuses_while_mvs_exist_then_purges():
    runner = FakeRunner({"sales_lh": ["daily_sales_mv"], "sales_lhuat": [], "sales_lhdev": []})
    assert bootstrap.mv_inventory(runner, SALES) == {"prod": 1, "uat": 0, "dev": 0}
    with pytest.raises(sr.StarRocksError, match="--purge-data"):
        bootstrap.remove_product(runner, SALES, [DEFAULT], purge=False, dry_run=False)
    assert runner.executed == []
    bootstrap.remove_product(runner, SALES, [DEFAULT], purge=True, dry_run=False)
    assert "DROP DATABASE IF EXISTS `default_catalog`.`sales_lh` FORCE;" in runner.executed
    assert "DROP ROLE `role_sales_owner`;" in runner.executed
    assert not any(sql.startswith("DROP ROLE `role_default_") for sql in runner.executed)


def test_removal_refuses_the_default_product(capsys):
    assert bootstrap.main(["--remove", "--product", str(ROOT / "data-products/default.yaml")]) == 2
    assert "cannot be removed" in capsys.readouterr().err


def test_user_reconcile_does_not_require_roles_of_a_product_being_removed(monkeypatch):
    # Build and Test finding: after a removal drops role_sales_*, the scheduled
    # reconcile still saw the product file and refused for "missing" roles.
    from starrocks_strategies import reconcile

    class Runner:
        def query(self, sql, operation):
            return [{"Name": role} for role in sr.MANAGED_ROLES if not role.startswith("role_default_writer")]

    monkeypatch.setattr(reconcile, "MISSING_GROUPS", set())
    assert reconcile.missing_managed_roles(Runner()) == ["role_default_writer"]
    monkeypatch.setattr(reconcile, "MISSING_GROUPS", {"role-default-writer"})
    assert reconcile.missing_managed_roles(Runner()) == []
