#!/usr/bin/env python3
"""StarRocks audit capture: the AuditLoader plugin writes every audit event to a staging table.

Run by ``bootstrap-starrocks.py`` on every start (``--runtime-only``) and before the role
grants in full runs; ``--status`` prints the capture state for ``scripts/lakehouse.sh status``.

- Staging table ``starrocks_audit_db__.starrocks_audit_tbl__``: the StarRocks 4.1 AuditLoader
  columns (plus ``ScanStats``), one partition per day of ``timestamp``, 7 days kept. Created if
  missing; an existing table is checked, never altered.
- Loader user ``srv-auditloader``: native password generated once into
  ``.runtime/credentials/srv-auditloader-password`` (0600), ``INSERT`` on the staging table only.
- Plugin: the vendored package ``plugins/auditloader-<version>.zip`` is verified against
  ``plugins/auditloader.lock``; its ``plugin.conf`` is rendered with the loader's credentials into
  ``.runtime/starrocks-audit/auditloader.zip`` (mounted read-only into the FE at
  ``/opt/lakehouse/starrocks-audit``) and installed, or reinstalled when the package changes.

Product roles read the staging table through ``platform_sources.starrocks_audit`` in their
product files (grants planned by ``bootstrap-starrocks.py``). Functional design: rules AC-1 to
AC-12 of intent ``20261125-starrocks-audit-capture``. No secret is printed or logged.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import secrets
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import starrocks_common as sr  # noqa: E402

DATABASE = "starrocks_audit_db__"
TABLE = "starrocks_audit_tbl__"
QUALIFIED_TABLE = f"{DATABASE}.{TABLE}"
LOADER_USER = "srv-auditloader"
PLUGIN_NAME = "AuditLoader"
RETENTION_DAYS = 7
FE_HTTP = "127.0.0.1:8030"
PLUGIN_DIR = Path(__file__).resolve().parent / "plugins"
LOCK_FILE = PLUGIN_DIR / "auditloader.lock"
RUNTIME_DIR = sr.ROOT / ".runtime" / "starrocks-audit"
PASSWORD_FILE = sr.CREDENTIALS / "srv-auditloader-password"
PACKAGE_NAME = "auditloader.zip"
DIGEST_NAME = "installed.sha256"
FE_PACKAGE_PATH = f"/opt/lakehouse/starrocks-audit/{PACKAGE_NAME}"
ZIP_TIME = (1980, 1, 1, 0, 0, 0)

# AC-1: the StarRocks 4.1 docs DDL plus ScanStats (newer plugins). Readers match columns by name.
STAGING_COLUMNS: tuple[tuple[str, str], ...] = (
    ("queryId", "VARCHAR(64)"),
    ("timestamp", "DATETIME NOT NULL"),
    ("queryType", "VARCHAR(12)"),
    ("clientIp", "VARCHAR(32)"),
    ("user", "VARCHAR(64)"),
    ("authorizedUser", "VARCHAR(64)"),
    ("resourceGroup", "VARCHAR(64)"),
    ("catalog", "VARCHAR(32)"),
    ("db", "VARCHAR(96)"),
    ("state", "VARCHAR(8)"),
    ("errorCode", "VARCHAR(512)"),
    ("errorMessage", "VARCHAR(1048576) NULL"),
    ("queryTime", "BIGINT"),
    ("scanBytes", "BIGINT"),
    ("scanRows", "BIGINT"),
    ("returnRows", "BIGINT"),
    ("cpuCostNs", "BIGINT"),
    ("memCostBytes", "BIGINT"),
    ("stmtId", "INT"),
    ("isQuery", "TINYINT"),
    ("feIp", "VARCHAR(128)"),
    ("stmt", "VARCHAR(1048576)"),
    ("digest", "VARCHAR(32)"),
    ("planCpuCosts", "DOUBLE"),
    ("planMemCosts", "DOUBLE"),
    ("pendingTimeMs", "BIGINT"),
    ("candidateMVs", "VARCHAR(65533) NULL"),
    ("hitMvs", "VARCHAR(65533) NULL"),
    ("QueriedRelations", "ARRAY<VARCHAR(65533)> NULL"),
    ("warehouse", "VARCHAR(128) NULL"),
    ("ScanStats", "JSON NULL"),
)
CONF_KEYS = ("frontend_host_port", "database", "table", "user", "password", "secret_key")
PASSWORD_PATTERN = re.compile(r"^[A-Za-z0-9_-]{24,128}$")


class AuditCaptureError(sr.StarRocksError):
    """The audit capture can't be set up safely; the message never holds a secret."""


@dataclass(frozen=True)
class PluginLock:
    version: str
    file: str
    source_url: str
    sha256: str
    license: str


# ---- Pure functions ----


def staging_ddl() -> list[str]:
    """The statements that create the staging database and table if they are missing (AC-1)."""
    columns = ",\n  ".join(f"`{name}` {kind}" for name, kind in STAGING_COLUMNS)
    return [
        f"CREATE DATABASE IF NOT EXISTS {DATABASE};",
        f"CREATE TABLE IF NOT EXISTS {QUALIFIED_TABLE} (\n  {columns}\n) ENGINE = OLAP\n"
        "DUPLICATE KEY (`queryId`, `timestamp`, `queryType`)\n"
        "COMMENT 'StarRocks audit log (AuditLoader); 7 days'\n"
        "PARTITION BY date_trunc('day', `timestamp`)\n"
        f'PROPERTIES ("replication_num" = "1", "partition_live_number" = "{RETENTION_DAYS}");',
    ]


def normalize_type(kind: str) -> str:
    """A column type as ``DESCRIBE`` reports it, reduced for comparison: lower case, no nullability, no integer widths."""
    text = re.sub(r"\s+", " ", str(kind).strip().lower())
    text = re.sub(r"\s*(not\s+)?null$", "", text)
    text = re.sub(r"^(tinyint|smallint|int|bigint|largeint)\(\d+\)", r"\1", text)
    return text.replace(" ", "")


def column_problems(actual: list[tuple[str, str]]) -> list[str]:
    """Missing or retyped staging columns (AC-2); extra columns are allowed."""
    found = {str(name).lower(): normalize_type(kind) for name, kind in actual}
    problems = []
    for name, kind in STAGING_COLUMNS:
        current = found.get(name.lower())
        expected = normalize_type(kind)
        if current is None:
            problems.append(f"missing column {name}")
        elif current != expected:
            problems.append(f"column {name} is {current}, expected {expected}")
    return problems


def loader_user_sql(password: str, exists: bool) -> list[str]:
    """Create or reset ``srv-auditloader`` and grant it INSERT on the staging table only (AC-4)."""
    identity = sr.user_identity(LOADER_USER)
    verb = "ALTER" if exists else "CREATE"
    return [
        f"{verb} USER {identity} IDENTIFIED BY {sr.quote_literal(password)};",
        f"GRANT INSERT ON TABLE {QUALIFIED_TABLE} TO USER {identity};",
    ]


def parse_lock(text: str) -> PluginLock:
    """The plugin lock (``key: value`` lines; ``#`` comments)."""
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition(":")
        values[key.strip()] = value.strip()
    missing = [key for key in ("version", "file", "source_url", "sha256", "license") if not values.get(key)]
    if missing or not re.fullmatch(r"[0-9a-f]{64}", values.get("sha256", "")) or "/" in values.get("file", "/"):
        raise AuditCaptureError("The AuditLoader lock file is incomplete or invalid.")
    return PluginLock(values["version"], values["file"], values["source_url"], values["sha256"], values["license"])


def verify_package(data: bytes, lock: PluginLock) -> bytes:
    """The vendored package bytes, when their SHA-256 matches the lock (AC-5)."""
    if hashlib.sha256(data).hexdigest() != lock.sha256:
        raise AuditCaptureError(f"The vendored AuditLoader package {lock.file} does not match its locked SHA-256; refusing to install it.")
    return data


def render_plugin_conf(template: str, password: str) -> str:
    """The package's ``plugin.conf`` with the loader settings set and every other line kept (AC-6)."""
    if not PASSWORD_PATTERN.fullmatch(password):
        raise AuditCaptureError("The loader password has an unexpected format.")
    wanted = {
        "frontend_host_port": FE_HTTP,
        "database": DATABASE,
        "table": TABLE,
        "user": LOADER_USER,
        "password": password,
        "secret_key": "",
    }
    lines, seen = [], set()
    for line in template.splitlines():
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
        if key in wanted:
            lines.append(f"{key}={wanted[key]}")
            seen.add(key)
        else:
            lines.append(line)
    lines += [f"{key}={wanted[key]}" for key in CONF_KEYS if key not in seen]
    return "\n".join(lines) + "\n"


def parse_conf(text: str) -> dict[str, str]:
    """``key=value`` pairs of a ``plugin.conf`` (comments and blank lines skipped)."""
    pairs = {}
    for line in text.splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            pairs[key.strip()] = value.strip()
    return pairs


def build_package(vendored: bytes, password: str) -> bytes:
    """The vendored package with its ``plugin.conf`` rendered: same entries, fixed order and times (AC-7)."""
    with zipfile.ZipFile(io.BytesIO(vendored)) as source:
        entries = {info.filename: source.read(info) for info in source.infolist() if not info.is_dir()}
    if "plugin.conf" not in entries or "plugin.properties" not in entries:
        raise AuditCaptureError("The AuditLoader package has no plugin.conf or plugin.properties.")
    entries["plugin.conf"] = render_plugin_conf(entries["plugin.conf"].decode("utf-8"), password).encode("utf-8")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            target.writestr(info, entries[name])
    return output.getvalue()


def package_digest(package: bytes) -> str:
    return hashlib.sha256(package).hexdigest()


def plugin_action(installed: dict[str, str] | None, recorded_digest: str | None, digest: str) -> str:
    """``install``, ``reinstall`` or ``keep`` (AC-8)."""
    if installed is None:
        return "install"
    if (installed.get("Status") or "").strip().upper() != "INSTALLED" or recorded_digest != digest:
        return "reinstall"
    return "keep"


# ---- Files ----


def _write_private(path: Path, data: bytes) -> None:
    """Write ``data`` atomically with mode 0600 (folder 0700)."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def loader_password(path: Path = PASSWORD_FILE) -> tuple[str, bool]:
    """The loader password and whether it was created now (AC-3)."""
    if path.is_symlink():
        raise AuditCaptureError(f"Protected file is a symbolic link: {path.name}")
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if not PASSWORD_PATTERN.fullmatch(value):
            raise AuditCaptureError(f"Protected file has an unexpected format: {path.name}")
        os.chmod(path, 0o600)
        return value, False
    value = secrets.token_urlsafe(24)
    _write_private(path, (value + "\n").encode("utf-8"))
    return value, True


def read_digest(path: Path) -> str | None:
    if not path.is_file() or path.is_symlink():
        return None
    value = path.read_text(encoding="utf-8").strip()
    return value if re.fullmatch(r"[0-9a-f]{64}", value) else None


# ---- StarRocks ----


def _plugin_row(runner: sr.SqlRunner) -> dict[str, str] | None:
    for row in runner.query("SHOW PLUGINS;", "list plugins"):
        if (row.get("Name") or "").strip() == PLUGIN_NAME:
            return row
    return None


def _loader_plugin(runner: sr.SqlRunner) -> str | None:
    for row in runner.query("SHOW ALL AUTHENTICATION;", "list users"):
        if (row.get("UserIdentity") or "").split("@", 1)[0].strip().strip("'`\"") == LOADER_USER:
            return (row.get("AuthPlugin") or "").strip().upper()
    return None


def ensure_audit_capture(
    runner: sr.SqlRunner,
    dry_run: bool = False,
    password_file: Path = PASSWORD_FILE,
    runtime_dir: Path = RUNTIME_DIR,
    lock_file: Path = LOCK_FILE,
) -> dict[str, str]:
    """Staging table, loader user and plugin (AC-1 to AC-8); returns a report without secrets."""
    report: dict[str, str] = {}
    lock = parse_lock(lock_file.read_text(encoding="utf-8"))
    vendored = verify_package((lock_file.parent / lock.file).read_bytes(), lock)
    report["plugin_version"] = lock.version
    if dry_run:
        report.update(table="would be created or checked", user="would be created or reset", plugin="would be installed or kept")
        return report

    for statement in staging_ddl():
        runner.execute(statement, "create the audit staging table")
    columns = [(row.get("Field", ""), row.get("Type", "")) for row in runner.query(f"DESCRIBE {QUALIFIED_TABLE};", "describe the audit staging table")]
    problems = column_problems(columns)
    report["table"] = "ok" if not problems else "problems: " + "; ".join(problems)

    password, created = loader_password(password_file)
    plugin = _loader_plugin(runner)
    if plugin is not None and plugin not in ("MYSQL_NATIVE_PASSWORD", ""):
        report["user"] = f"conflict: {LOADER_USER} exists with login {plugin}; not changed"
    else:
        for statement in loader_user_sql(password, exists=plugin is not None):
            runner.execute(statement, "set up the audit loader user")
        report["user"] = "created" if plugin is None else ("password set" if created else "ok")

    package = build_package(vendored, password)
    digest = package_digest(package)
    package_path, digest_path = runtime_dir / PACKAGE_NAME, runtime_dir / DIGEST_NAME
    action = plugin_action(_plugin_row(runner), read_digest(digest_path), digest)
    if action != "keep" or not package_path.is_file():
        _write_private(package_path, package)
    if action == "reinstall":
        runner.execute(f"UNINSTALL PLUGIN {PLUGIN_NAME};", "uninstall the audit loader plugin")
    if action in ("install", "reinstall"):
        runner.execute(f'INSTALL PLUGIN FROM "{FE_PACKAGE_PATH}";', "install the audit loader plugin")
        row = _plugin_row(runner)
        if row is None or (row.get("Status") or "").strip().upper() != "INSTALLED":
            raise AuditCaptureError("The AuditLoader plugin did not reach the INSTALLED state.")
        _write_private(digest_path, (digest + "\n").encode("utf-8"))
    report["plugin"] = {"install": "installed", "reinstall": "reinstalled", "keep": "kept"}[action]
    return report


def capture_status(runner: sr.SqlRunner, now: datetime | None = None) -> str:
    """One status line (AC-11): the plugin state and the newest staging row's age."""
    row = _plugin_row(runner)
    plugin = "not installed" if row is None else (row.get("Status") or "unknown").strip()
    try:
        rows = runner.query(f"SELECT max(`timestamp`) AS newest FROM {QUALIFIED_TABLE};", "read the newest audit row")
    except sr.StarRocksError:
        return f"audit capture: plugin {plugin}; staging table unavailable"
    newest = (rows[0].get("newest") if rows else None) or ""
    if not newest or newest.upper() == "NULL":
        return f"audit capture: plugin {plugin}; no rows yet"
    try:
        then = datetime.strptime(newest[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return f"audit capture: plugin {plugin}; newest row {newest}"
    age = int(((now or datetime.now(timezone.utc)) - then).total_seconds())
    return f"audit capture: plugin {plugin}; newest row {max(age, 0) // 60} min ago"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--status", action="store_true", help="print the capture status line")
    parser.add_argument("--dry-run", action="store_true", help="verify the package and print the plan")
    parser.add_argument("--transport", choices=("docker", "network"), default="docker")
    parser.add_argument("--root-password-file", type=Path, default=sr.CREDENTIALS / "starrocks-root-password")
    args = parser.parse_args(argv)
    try:
        runner = sr.root_runner(args.transport, args.root_password_file)
        if args.status:
            print(capture_status(runner))
            return 0
        report = ensure_audit_capture(runner, dry_run=args.dry_run)
    except sr.StarRocksError as error:
        print(f"ERROR: StarRocks audit capture: {error}", file=sys.stderr)
        return 1
    print("StarRocks audit capture: " + ", ".join(f"{key} {value}" for key, value in sorted(report.items())) + ".")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
