"""Contracts for the StarRocks bootstrap, user reconcile, wiring, and safety rules."""

import pytest

from starrocks_strategies import ROOT, bootstrap, reconcile, sr


class FakeRunner:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.executed = []

    def query(self, sql, operation):
        for prefix, rows in self.responses.items():
            if sql.startswith(prefix):
                return rows
        return []

    def execute(self, sql, operation):
        self.executed.append(sql)


def test_opt_out_skips_both_scripts(monkeypatch, capsys):
    monkeypatch.setenv("STARROCKS_ENABLED", "false")
    assert bootstrap.main([]) == 0 and reconcile.main([]) == 0
    out = capsys.readouterr().out
    assert out.count("STARROCKS_ENABLED=false") == 2


def test_enabled_defaults_true_and_is_case_insensitive(monkeypatch, tmp_path):
    monkeypatch.delenv("STARROCKS_ENABLED", raising=False)
    assert sr.starrocks_enabled(tmp_path / "missing.env") is True
    env = tmp_path / ".env"
    env.write_text("STARROCKS_ENABLED=FALSE\n")
    assert sr.starrocks_enabled(env) is False


def test_reconcile_refuses_an_empty_keycloak_answer(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("STARROCKS_ENABLED", "true")
    secret = tmp_path / "admin"
    secret.write_text("x\n")
    monkeypatch.setattr(reconcile, "read_keycloak_memberships", lambda *_: {"service-account-srv-starrocks": {"role-default-writer"}})
    monkeypatch.setattr(sr, "root_runner", lambda *_: pytest.fail("StarRocks must not be touched"))
    assert reconcile.main(["--keycloak-admin-password-file", str(secret)]) == 1
    assert "refusing to change StarRocks users" in capsys.readouterr().err


def test_reconcile_aborts_when_keycloak_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("STARROCKS_ENABLED", "true")
    secret = tmp_path / "admin"
    secret.write_text("x\n")

    def boom(*_):
        raise reconcile.KeycloakError("down")

    monkeypatch.setattr(reconcile, "read_keycloak_memberships", boom)
    monkeypatch.setattr(sr, "root_runner", lambda *_: pytest.fail("StarRocks must not be touched"))
    assert reconcile.main(["--keycloak-admin-password-file", str(secret)]) == 1


def test_root_and_password_users_are_never_managed():
    runner = FakeRunner({
        "SHOW ALL AUTHENTICATION": [
            {"UserIdentity": "'root'@'%'", "AuthPlugin": "MYSQL_NATIVE_PASSWORD"},
            {"UserIdentity": "'legacy'@'%'", "AuthPlugin": "MYSQL_NATIVE_PASSWORD"},
            {"UserIdentity": "'joe-developer'@'%'", "AuthPlugin": "AUTHENTICATION_JWT"},
        ],
        "SHOW GRANTS FOR 'joe-developer'": [{"Grants": "GRANT 'role_default_developer' TO 'joe-developer'@'%'"}],
    })
    users = reconcile.read_starrocks_users(runner)
    assert "root" not in users
    plan = reconcile.plan_users(users, {"legacy": frozenset({"role_default_owner"})})
    assert plan.conflicts == ["legacy"] and plan.drop == ["joe-developer"]
    assert all("legacy" not in sql for sql, _ in reconcile.render_plan(plan))


def test_user_sql_uses_jwt_and_quotes_hyphenated_names():
    plan = reconcile.plan_users({}, {"joe-developer": frozenset({"role_default_developer"})})
    sql = [s for s, _ in reconcile.render_plan(plan)]
    assert sql[0].startswith("CREATE USER IF NOT EXISTS 'joe-developer'@'%' IDENTIFIED WITH authentication_jwt AS '{")
    assert "GRANT `role_default_developer` TO USER 'joe-developer'@'%';" in sql
    assert sql[-1] == "SET DEFAULT ROLE ALL TO 'joe-developer'@'%';"


def test_conflicting_catalog_stops_before_any_change():
    secret = "s"
    good = bootstrap.render_catalog_properties(bootstrap.catalog_definition(sr.ENVIRONMENTS[0], secret))
    bad = bootstrap.render_catalog_properties(bootstrap.catalog_definition(sr.ENVIRONMENTS[1], secret) | {"iceberg.catalog.uri": "http://x"})
    runner = FakeRunner({
        "SHOW CATALOGS": [{"Catalog": "lakehouse"}, {"Catalog": "lakehouse_uat"}],
        "SHOW CREATE CATALOG `lakehouse`": [{"Create Catalog": "CREATE EXTERNAL CATALOG `lakehouse`\n" + good}],
        "SHOW CREATE CATALOG `lakehouse_uat`": [{"Create Catalog": "CREATE EXTERNAL CATALOG `lakehouse_uat`\n" + bad}],
    })
    with pytest.raises(sr.StarRocksError, match="lakehouse_uat"):
        bootstrap.ensure_catalogs(runner, secret, recreate=False, dry_run=False)
    assert runner.executed == []


def test_recreate_catalogs_is_explicit_and_drops_then_creates():
    runner = FakeRunner({"SHOW CATALOGS": [{"Catalog": env.catalog} for env in sr.ENVIRONMENTS]})
    bootstrap.ensure_catalogs(runner, "s", recreate=True, dry_run=False)
    assert [s.split()[0] for s in runner.executed] == ["DROP", "CREATE"] * 3
    assert all("'srv-starrocks:s'" in s for s in runner.executed if s.startswith("CREATE"))


def test_catalog_contract_values():
    props = bootstrap.catalog_definition(sr.ENVIRONMENTS[2], "s")
    assert props["iceberg.catalog.security"] == "oauth2" and props["iceberg.catalog.warehouse"] == "lakehouse_dev"
    assert props["iceberg.catalog.vended-credentials-enabled"] == "true"
    assert props["iceberg.catalog.oauth2.server-uri"].startswith("http://keycloak:8080/realms/lakehouse/")
    assert not any(k.startswith("aws.s3.access_key") or k.startswith("aws.s3.secret_key") for k in props)


def test_unrecognised_grants_are_reported_not_revoked():
    grants, unknown = bootstrap.parse_role_grants("role_default_owner", [{"Catalog": "lakehouse", "Grants": "GRANT USAGE ON RESOURCE x TO ROLE 'role_default_owner'"}])
    assert grants == set() and unknown


def test_wiring_in_lifecycle_bootstrap_reset_and_reconciler():
    lakehouse = (ROOT / "scripts/lakehouse.sh").read_text()
    assert "python3 infra/starrocks/bootstrap-starrocks.py --runtime-only" in lakehouse
    assert 'reconcile-starrocks) require_tools; python3 infra/starrocks/reconcile-starrocks-users.py "${@:2}" ;;' in lakehouse
    assert '${STARROCKS_FILES[@]+"${STARROCKS_FILES[@]}"}' in lakehouse
    product = (ROOT / "scripts/bootstrap-default-product.sh").read_text()
    assert product.index("run-bootstrap-smoke-spark.sh") < product.index("bootstrap-starrocks.py") < product.index("reconcile-starrocks-users.py --transport docker")
    run = (ROOT / "infra/polaris/reconciler/run.sh").read_text()
    assert '"${STARROCKS_ENABLED:-true}" != "false"' in run and "--transport network" in run
    assert "mariadb-client=11.8.9-r0" in (ROOT / "infra/polaris/reconciler/Dockerfile").read_text()
    compose = (ROOT / "docker-compose.yml").read_text()
    assert "starrocks-root-password:/run/secrets/starrocks_root_password:ro" in compose
    login = (ROOT / "scripts/starrocks-login.sh").read_text()
    assert "mysql:9.7.2@sha256:" in login and "--authentication-openid-connect-client-id-token-file" in login
    assert 'password@-' in login and "read -r -s" in login


def test_legacy_starrocks_assets_are_retired():
    for path in ("infra/starrocks/fe", "infra/starrocks/be", "infra/starrocks/kerberos", "infra/starrocks/ldap-access",
                 "infra/starrocks/sql-bootstrap", "infra/starrocks/preflight", "infra/starrocks/conf/hive-site.xml",
                 "infra/starrocks/conf/core-site.xml", "scripts/bootstrap-starrocks-sql.sh"):
        assert not (ROOT / path).exists(), path
    for path in (ROOT / "infra/starrocks").rglob("*"):
        if path.is_file() and path.suffix in (".py", ".conf"):
            assert "write-service-account" not in path.read_text()


def test_reconcile_refuses_before_roles_exist(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("STARROCKS_ENABLED", "true")
    secret = tmp_path / "admin"
    secret.write_text("x\n")
    monkeypatch.setattr(reconcile, "read_keycloak_memberships", lambda *_: {"joe-developer": {"role-default-developer"}})
    runner = FakeRunner({"SHOW ROLES": [{"Name": "root"}, {"Name": "role_default_owner"}]})
    monkeypatch.setattr(sr, "root_runner", lambda *_: runner)
    assert reconcile.main(["--keycloak-admin-password-file", str(secret)]) == 1
    assert runner.executed == [] and "not bootstrapped yet" in capsys.readouterr().err


def test_backend_host_is_read_from_the_ip_column_or_host():
    assert bootstrap._backend_host({"IP": "starrocks-be"}) == "starrocks-be"
    assert bootstrap._backend_host({"Host": "starrocks-be"}) == "starrocks-be"


def test_polaris_read_includes_namespace_properties_for_starrocks():
    source = (ROOT / "infra/polaris/bootstrap-product-authorization.py").read_text()
    read_block = source[source.index("READ = ("):source.index("WRITE = ")]
    assert '"NAMESPACE_READ_PROPERTIES"' in read_block
