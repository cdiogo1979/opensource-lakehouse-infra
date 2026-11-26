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
        if grant.object == "ALL TABLES IN DATABASE information_schema":
            # The catalog's metadata tables: rows are filtered by the role's own privileges.
            assert grant.privilege == "SELECT", grant
            continue
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


def test_sql_client_metadata_grant_renders_parses_and_is_revoked_with_access():
    grant = bootstrap.Grant("role_default_developer", "SELECT", "lakehouse_uat", "ALL TABLES IN DATABASE information_schema")
    assert bootstrap.render_grant(grant) == (
        "SET CATALOG `lakehouse_uat`;\nGRANT SELECT ON ALL TABLES IN DATABASE `information_schema` TO ROLE `role_default_developer`;"
    )
    rows = [{"Catalog": "lakehouse_uat", "Grants": "GRANT SELECT ON ALL TABLES IN DATABASE information_schema TO ROLE 'role_default_developer'"}]
    assert bootstrap.parse_role_grants("role_default_developer", rows) == ({grant}, [])
    grants = bootstrap.role_grants()
    analyst = {g.catalog for g in grants if g.role == "role_default_analyst" and g.object == grant.object}
    assert analyst == {"lakehouse"}  # analysts read prod only
    assert {g.catalog for g in grants if g.role == "role_default_developer" and g.object == grant.object} == {"lakehouse", "lakehouse_uat", "lakehouse_dev"}
    # A catalog dropped to "none" revokes the grant with USAGE.
    plan = bootstrap.plan_grants({grant}, set(), ("role_default_developer",))
    assert plan.revoke == [grant] and plan.add == []


# --- StarRocks audit log staging table (platform_sources, AC-15) -------------------------

AUDIT = dp.load_product(ROOT / "data-products/audit.yaml")
AUDIT_MODEL = sr.build_model([DEFAULT, SALES, AUDIT])
STAGING = "TABLE starrocks_audit_db__.starrocks_audit_tbl__"


def test_only_declared_reading_roles_select_the_audit_staging_table():
    assert AUDIT_MODEL.audit_readers == ("role_audit_owner", "role_audit_developer", "role_audit_writer")
    readers = {g.role for g in bootstrap.role_grants(AUDIT_MODEL) if g.object == STAGING}
    assert readers == {"role_audit_owner", "role_audit_developer", "role_audit_writer"}
    staging = [g for g in bootstrap.role_grants(AUDIT_MODEL) if "starrocks_audit" in g.object]
    assert all(g.privilege == "SELECT" and g.catalog == sr.INTERNAL_CATALOG for g in staging)
    assert not any("starrocks_audit" in g.object for g in bootstrap.role_grants(MODEL))


def test_audit_table_grant_renders_and_parses_round_trip():
    grant = bootstrap.Grant("role_audit_writer", "SELECT", sr.INTERNAL_CATALOG, STAGING)
    assert bootstrap.render_grant(grant) == (
        "SET CATALOG `default_catalog`;\nGRANT SELECT ON TABLE `starrocks_audit_db__`.`starrocks_audit_tbl__` TO ROLE `role_audit_writer`;"
    )
    rows = [{"Catalog": "default_catalog", "Grants": "GRANT SELECT ON TABLE starrocks_audit_db__.starrocks_audit_tbl__ TO ROLE 'role_audit_writer'"}]
    parsed, unknown = bootstrap.parse_role_grants("role_audit_writer", rows)
    assert unknown == [] and parsed == {grant}


def test_audit_table_grant_is_kept_while_declared_and_revoked_when_removed():
    current = bootstrap.role_grants(AUDIT_MODEL)
    assert bootstrap.plan_grants(current, bootstrap.role_grants(AUDIT_MODEL), AUDIT_MODEL.managed_roles).add == []
    without = sr.build_model([DEFAULT, SALES, dp.parse_product({**yaml.safe_load((ROOT / "data-products/audit.yaml").read_text()), "platform_sources": {}}, "audit.yaml")])
    plan = bootstrap.plan_grants(current, bootstrap.role_grants(without), without.managed_roles)
    assert sorted(g.role for g in plan.revoke if g.object == STAGING) == ["role_audit_developer", "role_audit_owner", "role_audit_writer"]
