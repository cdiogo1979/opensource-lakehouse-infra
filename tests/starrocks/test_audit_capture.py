"""StarRocks audit capture (audit_capture.py): staging table, loader user, vendored plugin (AC-1 to AC-12)."""

import hashlib
import io
import os
import stat
import zipfile
from datetime import datetime, timezone

import pytest
from hypothesis import given, settings, strategies as st

from starrocks_strategies import ROOT, load

capture = load("audit_capture", "infra/starrocks/audit_capture.py")
LOCK = capture.parse_lock((ROOT / "infra/starrocks/plugins/auditloader.lock").read_text(encoding="utf-8"))
VENDORED = (ROOT / "infra/starrocks/plugins" / LOCK.file).read_bytes()
PASSWORD = "Q" * 32


class FakeRunner:
    """Records statements; answers SHOW/DESCRIBE/SELECT from simple state."""

    def __init__(self, plugin=None, user_plugin=None, columns=None, newest=None, fail_install=False):
        self.plugin, self.user_plugin, self.newest, self.fail_install = plugin, user_plugin, newest, fail_install
        self.columns = columns if columns is not None else [(name, kind.split(" NOT NULL")[0].split(" NULL")[0]) for name, kind in capture.STAGING_COLUMNS]
        self.executed = []

    def query(self, sql, operation):
        if sql.startswith("SHOW PLUGINS"):
            return [] if self.plugin is None else [{"Name": "AuditLoader", "Status": self.plugin}]
        if sql.startswith("SHOW ALL AUTHENTICATION"):
            return [{"UserIdentity": "'root'@'%'", "AuthPlugin": "MYSQL_NATIVE_PASSWORD"}] + (
                [] if self.user_plugin is None else [{"UserIdentity": "'srv-auditloader'@'%'", "AuthPlugin": self.user_plugin}]
            )
        if sql.startswith("DESCRIBE"):
            return [{"Field": name, "Type": kind} for name, kind in self.columns]
        if sql.startswith("SELECT max"):
            return [{"newest": self.newest or "NULL"}]
        raise AssertionError(sql)

    def execute(self, sql, operation):
        self.executed.append(sql)
        if sql.startswith("INSTALL PLUGIN"):
            self.plugin = None if self.fail_install else "INSTALLED"
        if sql.startswith("UNINSTALL PLUGIN"):
            self.plugin = None


@pytest.fixture
def paths(tmp_path):
    return {"password_file": tmp_path / "credentials" / "srv-auditloader-password", "runtime_dir": tmp_path / "starrocks-audit"}


# --- Vendored package and lock (AC-5) --------------------------------------------------


def test_the_vendored_package_matches_its_lock():
    assert LOCK.version == "5.0.0" and LOCK.license == "Apache-2.0"
    assert hashlib.sha256(VENDORED).hexdigest() == LOCK.sha256
    with zipfile.ZipFile(io.BytesIO(VENDORED)) as package:
        properties = package.read("plugin.properties").decode()
    assert "name=AuditLoader" in properties and "version=5.0.0" in properties


def test_a_changed_package_is_refused():
    with pytest.raises(capture.AuditCaptureError, match="does not match its locked SHA-256"):
        capture.verify_package(VENDORED + b"x", LOCK)


@pytest.mark.parametrize("text", ["", "version: 1\nfile: a.zip\n", "version: 1\nfile: ../a.zip\nsource_url: u\nsha256: " + "a" * 64 + "\nlicense: x\n"])
def test_invalid_locks_are_refused(text):
    with pytest.raises(capture.AuditCaptureError):
        capture.parse_lock(text)


# --- Staging table (AC-1, AC-2) --------------------------------------------------------


def test_staging_ddl():
    database, table = capture.staging_ddl()
    assert database == "CREATE DATABASE IF NOT EXISTS starrocks_audit_db__;"
    assert table.startswith("CREATE TABLE IF NOT EXISTS starrocks_audit_db__.starrocks_audit_tbl__ (")
    assert "PARTITION BY date_trunc('day', `timestamp`)" in table and '"partition_live_number" = "7"' in table and '"replication_num" = "1"' in table
    assert "DUPLICATE KEY (`queryId`, `timestamp`, `queryType`)" in table and "`ScanStats` JSON NULL" in table
    assert "DROP" not in table and "ALTER" not in table


def test_column_problems_allow_extras_and_report_missing_or_retyped_columns():
    describe = [("queryid", "varchar(64)"), ("timestamp", "datetime")] + [(n, k.replace(" NOT NULL", "").replace(" NULL", "")) for n, k in capture.STAGING_COLUMNS[2:]]
    assert capture.column_problems(describe + [("extra", "int(11)")]) == []
    assert capture.column_problems([row for row in describe if row[0] != "stmt"]) == ["missing column stmt"]
    retyped = [(n, "int(11)" if n == "queryTime" else k) for n, k in describe]
    assert capture.column_problems(retyped) == ["column queryTime is int, expected bigint"]


# --- Loader user (AC-3, AC-4) ----------------------------------------------------------


def test_password_is_generated_once_private_and_reused(paths):
    first, created = capture.loader_password(paths["password_file"])
    again, created_again = capture.loader_password(paths["password_file"])
    assert created and not created_again and first == again and capture.PASSWORD_PATTERN.fullmatch(first)
    assert stat.S_IMODE(os.stat(paths["password_file"]).st_mode) == 0o600


def test_loader_user_sql_grants_insert_on_the_staging_table_only():
    create, grant = capture.loader_user_sql(PASSWORD, exists=False)
    assert create == f"CREATE USER 'srv-auditloader'@'%' IDENTIFIED BY '{PASSWORD}';"
    assert grant == "GRANT INSERT ON TABLE starrocks_audit_db__.starrocks_audit_tbl__ TO USER 'srv-auditloader'@'%';"
    assert capture.loader_user_sql(PASSWORD, exists=True)[0].startswith("ALTER USER 'srv-auditloader'@'%' IDENTIFIED BY ")


# --- Plugin conf and package (AC-6, AC-7) ----------------------------------------------


def test_rendered_conf_sets_the_loader_keys_and_keeps_the_rest():
    template = "# comment\nmax_batch_interval_sec=60\nuser=root\npassword=\nfilter=\n"
    conf = capture.parse_conf(capture.render_plugin_conf(template, PASSWORD))
    assert conf == {
        "max_batch_interval_sec": "60",
        "user": "srv-auditloader",
        "password": PASSWORD,
        "filter": "",
        "frontend_host_port": "127.0.0.1:8030",
        "database": "starrocks_audit_db__",
        "table": "starrocks_audit_tbl__",
        "secret_key": "",
    }
    assert capture.render_plugin_conf(template, PASSWORD).startswith("# comment\n")


@pytest.mark.parametrize("password", ["short", "x" * 30 + "\nuser=root", "a b" * 10])
def test_unexpected_passwords_are_refused(password):
    with pytest.raises(capture.AuditCaptureError):
        capture.render_plugin_conf("password=\n", password)


def test_built_package_is_deterministic_and_keeps_the_jar():
    package = capture.build_package(VENDORED, PASSWORD)
    assert package == capture.build_package(VENDORED, PASSWORD)
    assert capture.package_digest(package) != capture.package_digest(capture.build_package(VENDORED, "R" * 32))
    with zipfile.ZipFile(io.BytesIO(VENDORED)) as original, zipfile.ZipFile(io.BytesIO(package)) as built:
        assert sorted(built.namelist()) == sorted(n for n in original.namelist() if not n.endswith("/"))
        assert built.read("auditloader.jar") == original.read("auditloader.jar")
        assert built.read("plugin.properties") == original.read("plugin.properties")
        conf = capture.parse_conf(built.read("plugin.conf").decode())
    assert conf["user"] == "srv-auditloader" and conf["password"] == PASSWORD and conf["database"] == "starrocks_audit_db__"


# --- Install decision and orchestration (AC-8, AC-12) ----------------------------------


@pytest.mark.parametrize(
    "installed, recorded, action",
    [(None, None, "install"), ({"Status": "INSTALLED"}, "d", "keep"), ({"Status": "INSTALLED"}, "old", "reinstall"), ({"Status": "ERROR"}, "d", "reinstall"), ({"Status": "INSTALLED"}, None, "reinstall")],
)
def test_plugin_action(installed, recorded, action):
    assert capture.plugin_action(installed, recorded, "d") == action


def test_first_run_creates_everything_and_second_run_keeps_it(paths, capsys):
    runner = FakeRunner()
    report = capture.ensure_audit_capture(runner, **paths)
    assert report == {"plugin_version": "5.0.0", "table": "ok", "user": "created", "plugin": "installed"}
    assert runner.executed[:2] == capture.staging_ddl()
    assert runner.executed[-1] == 'INSTALL PLUGIN FROM "/opt/lakehouse/starrocks-audit/auditloader.zip";'
    package = paths["runtime_dir"] / "auditloader.zip"
    assert stat.S_IMODE(os.stat(package).st_mode) == 0o600 and stat.S_IMODE(os.stat(paths["runtime_dir"]).st_mode) == 0o700
    runner.user_plugin = "MYSQL_NATIVE_PASSWORD"
    runner.executed.clear()
    assert capture.ensure_audit_capture(runner, **paths)["plugin"] == "kept"
    assert not any(statement.startswith(("INSTALL", "UNINSTALL")) for statement in runner.executed)
    password = paths["password_file"].read_text().strip()
    assert password not in str(report) and password not in capsys.readouterr().out


def test_a_new_password_reinstalls_the_plugin(paths):
    runner = FakeRunner()
    capture.ensure_audit_capture(runner, **paths)
    paths["password_file"].unlink()
    runner.user_plugin, runner.executed = "MYSQL_NATIVE_PASSWORD", []
    report = capture.ensure_audit_capture(runner, **paths)
    assert report["plugin"] == "reinstalled" and report["user"] == "password set"
    assert [s.split()[0] for s in runner.executed if "PLUGIN" in s] == ["UNINSTALL", "INSTALL"]


def test_a_user_with_another_login_is_reported_not_changed(paths):
    runner = FakeRunner(user_plugin="AUTHENTICATION_LDAP_SIMPLE")
    report = capture.ensure_audit_capture(runner, **paths)
    assert report["user"].startswith("conflict") and not any("srv-auditloader" in s for s in runner.executed if "USER" in s.split()[:2])


def test_a_failed_install_raises_and_records_nothing(paths):
    with pytest.raises(capture.AuditCaptureError, match="INSTALLED"):
        capture.ensure_audit_capture(FakeRunner(fail_install=True), **paths)
    assert not (paths["runtime_dir"] / "installed.sha256").exists()


def test_dry_run_changes_nothing(paths):
    runner = FakeRunner()
    report = capture.ensure_audit_capture(runner, dry_run=True, **paths)
    assert runner.executed == [] and not paths["password_file"].exists() and report["plugin_version"] == "5.0.0"


def test_a_tampered_package_stops_before_any_change(paths, tmp_path):
    (tmp_path / LOCK.file).write_bytes(VENDORED + b"tamper")
    lock = tmp_path / "auditloader.lock"
    lock.write_text((ROOT / "infra/starrocks/plugins/auditloader.lock").read_text())
    runner = FakeRunner()
    with pytest.raises(capture.AuditCaptureError):
        capture.ensure_audit_capture(runner, lock_file=lock, **paths)
    assert runner.executed == []


# --- Status (AC-11) --------------------------------------------------------------------


def test_status_line():
    now = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
    assert capture.capture_status(FakeRunner(plugin="INSTALLED", newest="2026-11-25 11:55:10"), now) == "audit capture: plugin INSTALLED; newest row 4 min ago"
    assert capture.capture_status(FakeRunner(), now) == "audit capture: plugin not installed; no rows yet"


def test_bootstrap_runs_capture_and_survives_its_failure():
    text = (ROOT / "infra/starrocks/bootstrap-starrocks.py").read_text()
    order = [text.index(marker) for marker in ("ensure_ldap_login(runner)", "audit_capture.ensure_audit_capture", "if args.runtime_only:", "ensure_roles(runner, args.dry_run)")]
    assert order == sorted(order)
    assert "except sr.StarRocksError as error:\n                print(f\"ERROR: StarRocks audit capture not set up" in text


# --- Properties (PBT-02, PBT-03, PBT-07, PBT-08) ----------------------------------------

passwords = st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-", min_size=24, max_size=64)
conf_keys = st.from_regex(r"[a-z][a-z_]{2,20}", fullmatch=True).filter(lambda key: key not in capture.CONF_KEYS)
templates = st.lists(st.one_of(st.tuples(conf_keys, st.from_regex(r"[A-Za-z0-9_.:,=-]{0,12}", fullmatch=True)), st.just(("#", "comment"))), max_size=8)


@settings(max_examples=100, deadline=None)
@given(templates, passwords)
def test_rendering_round_trip(lines, password):
    template = "\n".join("# comment" if key == "#" else f"{key}={value}" for key, value in lines)
    parsed = capture.parse_conf(capture.render_plugin_conf(template, password))
    assert parsed["password"] == password and parsed["user"] == "srv-auditloader" and parsed["secret_key"] == ""
    for key, value in lines:
        if key != "#":
            assert parsed[key] == dict(line for line in lines if line[0] != "#")[key]


@settings(max_examples=25, deadline=None)
@given(passwords)
def test_package_round_trip_and_determinism(password):
    package = capture.build_package(VENDORED, password)
    with zipfile.ZipFile(io.BytesIO(package)) as built:
        assert capture.parse_conf(built.read("plugin.conf").decode())["password"] == password
    assert capture.build_package(VENDORED, password) == package


@settings(max_examples=100, deadline=None)
@given(st.permutations(list(capture.STAGING_COLUMNS)), st.booleans(), st.data())
def test_column_check_ignores_order_and_case_and_finds_removals(columns, upper, data):
    describe = [((name.upper() if upper else name), kind.replace(" NOT NULL", "").replace(" NULL", "").lower()) for name, kind in columns]
    assert capture.column_problems(describe) == []
    removed = data.draw(st.sampled_from(describe))
    assert capture.column_problems([row for row in describe if row != removed]) == [f"missing column {next(n for n, _ in capture.STAGING_COLUMNS if n.lower() == removed[0].lower())}"]


@settings(max_examples=100, deadline=None)
@given(st.one_of(st.none(), st.fixed_dictionaries({"Status": st.sampled_from(["INSTALLED", "ERROR", "installed", ""])})), st.one_of(st.none(), st.sampled_from(["a", "b"])), st.sampled_from(["a", "b"]))
def test_keep_only_when_installed_and_digests_match(installed, recorded, digest):
    action = capture.plugin_action(installed, recorded, digest)
    assert (action == "keep") == (installed is not None and installed["Status"].upper() == "INSTALLED" and recorded == digest)
