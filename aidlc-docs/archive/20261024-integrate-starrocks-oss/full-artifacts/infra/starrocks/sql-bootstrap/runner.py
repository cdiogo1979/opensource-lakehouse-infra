#!/usr/bin/env python3
"""Host-side StarRocks canary and SQL bootstrap.

All SQL is passed to the MySQL-compatible client over stdin. Client output is
captured and only allowlisted status messages are written to the terminal.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / ".runtime"
CREDENTIALS = RUNTIME / "credentials"
STATE = RUNTIME / "state"
LOCK = STATE / "starrocks-sql.lock"
MARKER = STATE / "starrocks-sql-canary.json"
FE_CONTAINER = "iceberg-poc-starrocks-fe"
FE_CONFIG = "/opt/starrocks/fe/conf/fe.conf"
FE_LOG_DIR = "/opt/starrocks/fe/log"
HOST = "127.0.0.1"
PORT = "9030"
CATALOG = "iceberg"
IDENTITIES = {
    "admin": "starrocks-admin-password",
    "user_a": "starrocks-user-a-password",
    "user_b": "starrocks-user-b-password",
    "write_service_account": "starrocks-writer-password",
}
PASSWORD_FILES = {"root": "starrocks-root-password", **IDENTITIES}
PASSWORD_RE = re.compile(r"^[0-9a-f]{64}$")


class SafeFailure(Exception):
    """An error whose message is safe to present to the operator."""


def say(message: str, *, error: bool = False) -> None:
    print(message, file=sys.stderr if error else sys.stdout)


def require_command(command: str) -> str:
    override = os.environ.get("MYSQL_CLI")
    candidate = override if override else command
    resolved = shutil.which(candidate)
    if not resolved:
        raise SafeFailure(
            "Required MySQL-compatible CLI 'mysql' was not found. Install a "
            "MySQL-protocol-compatible client and retry."
        )
    return resolved


def capture(args: Sequence[str], *, stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            list(args), input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, close_fds=True,
        )
    except (OSError, ValueError):
        raise SafeFailure("A required local command could not be executed.") from None


def ensure_runtime_dirs() -> None:
    for path in (RUNTIME, CREDENTIALS, STATE):
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            path.chmod(0o700)
        except OSError:
            raise SafeFailure("Could not protect the local runtime directory.") from None
        info = path.stat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700:
            raise SafeFailure("Local runtime directory permissions are not owner-only.")


class ProjectLock:
    def __enter__(self) -> "ProjectLock":
        ensure_runtime_dirs()
        try:
            fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise SafeFailure(
                "StarRocks SQL workflow is busy or a previous lock is ambiguous. "
                "Confirm no workflow is active, then resolve the lock manually."
            ) from None
        except OSError:
            raise SafeFailure("Could not acquire the protected StarRocks workflow lock.") from None
        try:
            os.write(fd, f"pid={os.getpid()}\nstarted={utc_now()}\n".encode("ascii"))
            os.fsync(fd)
        finally:
            os.close(fd)
        self.owned = True
        try:
            cleanup_owned_temporaries()
        except SafeFailure:
            LOCK.unlink(missing_ok=True)
            self.owned = False
            raise
        return self

    def __exit__(self, _kind, _value, _traceback) -> None:
        if getattr(self, "owned", False):
            try:
                LOCK.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                say("WARNING: could not remove the workflow lock; inspect it before retrying.", error=True)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def cleanup_owned_temporaries() -> None:
    # Called only after exclusive lock acquisition. These are private client-input
    # scratch files from an interrupted prior invocation, never SQL output files.
    for prefix in ("mysql-client-", "mysql-auth-", "canary-marker-"):
        for path in STATE.glob(prefix + "*"):
            try:
                if path.is_file() and not path.is_symlink():
                    path.unlink()
            except OSError:
                raise SafeFailure("Could not remove interrupted private SQL client scratch state.") from None


def credential_path(identity: str) -> Path:
    return CREDENTIALS / PASSWORD_FILES[identity]


def read_password(identity: str) -> str:
    path = credential_path(identity)
    try:
        value = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        raise SafeFailure(f"Credential file for '{identity}' is missing or unreadable.") from None
    if not PASSWORD_RE.fullmatch(value):
        raise SafeFailure(f"Credential file for '{identity}' has an unsupported format; preserve it and resolve manually.")
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise SafeFailure(f"Credential file for '{identity}' must have mode 0600.")
    return value


def create_password(identity: str) -> str:
    path = credential_path(identity)
    value = secrets.token_hex(32)
    data = (value + "\n").encode("ascii")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return read_password(identity)
    except OSError:
        raise SafeFailure(f"Could not create the protected credential file for '{identity}'.") from None
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        try:
            path.unlink()
        except OSError:
            pass
        raise SafeFailure(f"Could not persist the protected credential file for '{identity}'.") from None
    return value


def file_secret(path: Path, label: str) -> str:
    try:
        value = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        raise SafeFailure(f"Required protected {label} file is missing or unreadable.") from None
    if not value or "\n" in value or "\r" in value:
        raise SafeFailure(f"Required protected {label} file has an invalid format.")
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise SafeFailure(f"Required protected {label} file must have mode 0600.")
    return value


class MysqlClient:
    def __init__(self, binary: str):
        self.binary = binary

    def run(
        self, sql: str, *, password: str | None, allow_error: bool = False,
        operation: str = "SQL operation",
    ) -> tuple[int, str]:
        args = [self.binary]
        option_path: Path | None = None
        if password is not None:
            if not PASSWORD_RE.fullmatch(password):
                raise SafeFailure("SQL authentication material has an unsupported format.")
            fd, name = tempfile.mkstemp(prefix="mysql-client-", dir=STATE, text=True)
            option_path = Path(name)
            try:
                os.fchmod(fd, 0o600)
                with os.fdopen(fd, "w", encoding="ascii") as stream:
                    stream.write(f'[client]\nuser="root"\npassword="{password}"\n')
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError:
                try:
                    option_path.unlink()
                except OSError:
                    pass
                raise SafeFailure("Could not prepare protected SQL client authentication.") from None
            args.append(f"--defaults-file={option_path}")
        else:
            args.extend(["--no-defaults", "--skip-password"])
        args.extend([
            "--protocol=TCP", f"--host={HOST}", f"--port={PORT}", "--user=root",
            "--connect-timeout=4", "--batch", "--raw", "--skip-column-names", "--silent",
        ])
        try:
            result = capture(args, stdin=sql.encode("utf-8"))
        finally:
            if option_path is not None:
                try:
                    option_path.unlink()
                except OSError:
                    raise SafeFailure("Could not remove a temporary SQL client authentication file.") from None
        output = result.stdout.decode("utf-8", errors="replace")
        self.last_stdout = output
        self.last_stderr = result.stderr.decode("utf-8", errors="replace")
        self.last_client_output = self.last_stdout + self.last_stderr
        if result.returncode != 0 and not allow_error:
            raise SafeFailure(f"StarRocks rejected {operation}; details were suppressed to protect credentials.")
        return result.returncode, output


def root_connection(mysql: MysqlClient) -> str | None:
    root_path = credential_path("root")
    if root_path.exists():
        password = read_password("root")
        mysql.run("SELECT 1;", password=password, operation="the root SQL connection check")
        return password
    mysql.run("SELECT 1;", password=None, operation="the root SQL connection check")
    return None


def docker_output(args: Sequence[str]) -> bytes:
    result = capture(["docker", *args])
    if result.returncode != 0:
        raise SafeFailure("Could not inspect the running StarRocks FE safely.")
    return result.stdout


def runtime_fingerprint(mysql: MysqlClient, root_password: str | None) -> tuple[str, str, list[str]]:
    image = docker_output(["inspect", "--format", "{{.Image}}", FE_CONTAINER]).decode("ascii", "strict").strip()
    conf = docker_output(["exec", FE_CONTAINER, "cat", FE_CONFIG])
    if not image.startswith("sha256:") or not conf:
        raise SafeFailure("Could not identify the running FE image and logging configuration.")
    _rc, dynamic_logging = mysql.run(
        "ADMIN SHOW FRONTEND CONFIG LIKE '%log%';", password=root_password,
        operation="FE logging configuration inspection",
    )
    keys = [line.split("\t", 1)[0].strip().lower() for line in dynamic_logging.splitlines() if "\t" in line]
    if not keys or not any("audit_log" in key for key in keys) or not any("profile_log" in key for key in keys):
        raise SafeFailure("Could not inspect the current dynamic FE logging configuration.")
    log_dirs: set[str] = {FE_LOG_DIR}
    found_audit_dir = False
    found_profile_dir = False
    for line in dynamic_logging.splitlines():
        fields = line.split("\t")
        if len(fields) < 3:
            continue
        key, value = fields[0].strip().lower(), fields[2].strip()
        if key in {"audit_log_dir", "profile_log_dir"} and value and value.lower() not in {"null", "******"}:
            resolved = value if value.startswith("/") else f"/opt/starrocks/fe/{value}"
            log_dirs.add(resolved.rstrip("/"))
            found_audit_dir |= key == "audit_log_dir"
            found_profile_dir |= key == "profile_log_dir"
    if not found_audit_dir or not found_profile_dir:
        raise SafeFailure("Could not resolve the current FE audit/profile log directories.")
    fingerprint = hashlib.sha256(conf + b"\0" + dynamic_logging.encode("utf-8")).hexdigest()
    return image, fingerprint, sorted(log_dirs)


def sql_literal(value: str) -> str:
    # Callers only use generated hex values or bounded, internally generated markers.
    if not re.fullmatch(r"[A-Za-z0-9_:-]{1,160}", value):
        raise SafeFailure("A SQL value failed the local safe-format check.")
    return "'" + value + "'"


def sql_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,62}", value):
        raise SafeFailure("A SQL identifier failed the local safe-format check.")
    return f"`{value}`"


def scan_canary_surfaces(
    markers: Sequence[str], since: str, mysql: MysqlClient, root_password: str | None, log_dirs: Sequence[str]
) -> None:
    # Query profile output is captured and searched only in memory; it is never printed.
    _rc, profile_output = mysql.run("SHOW PROFILELIST LIMIT 1000;", password=root_password)
    assert_client_output_clear(mysql, markers)
    for marker in markers:
        if marker in profile_output:
            raise SafeFailure("Canary value appeared in StarRocks query profile history.")

    logs = capture(["docker", "logs", "--since", since, FE_CONTAINER])
    if logs.returncode != 0:
        raise SafeFailure("Could not inspect FE container output for the canary interval.")
    combined_logs = logs.stdout + logs.stderr
    if any(marker.encode("ascii") in combined_logs for marker in markers):
        raise SafeFailure("Canary value appeared in FE container diagnostics.")

    # Grep every FE log file (including audit/profile logs) without returning log text.
    # A grep exit of 1 means no match; exit >=2 means the inspection was incomplete.
    for marker in markers:
        result = capture([
            "docker", "exec", FE_CONTAINER, "sh", "-c",
            'marker=$1; shift; for path do [ -d "$path" ] || exit 2; done; '
            'grep -R -F -q -- "$marker" "$@"; rc=$?; '
            'if [ "$rc" -eq 0 ]; then exit 0; '
            'elif [ "$rc" -eq 1 ]; then exit 1; else exit 2; fi',
            "starrocks-canary-scan", marker, *log_dirs,
        ])
        if result.returncode == 0:
            raise SafeFailure("Canary value appeared in an FE log, audit, or profile file.")
        if result.returncode != 1:
            raise SafeFailure("Could not inspect all FE log, audit, and profile files.")


def canary(mysql_binary: str) -> None:
    ensure_runtime_dirs()
    with ProjectLock():
        # Invalidate a prior marker before starting a fresh verification attempt.
        try:
            MARKER.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            raise SafeFailure("Could not invalidate the prior canary marker.") from None

        mysql = MysqlClient(mysql_binary)
        root_password = root_connection(mysql)
        image, config_hash, log_dirs = runtime_fingerprint(mysql, root_password)
        started = utc_now()
        suffix = secrets.token_hex(8)
        user_name = f"sql_probe_{suffix}"
        catalog_name = f"sql_probe_{suffix}"
        password_marker = f"CANARY_{secrets.token_hex(20)}"
        altered_password_marker = f"CANARY_{secrets.token_hex(20)}"
        access_marker = f"CANARY_{secrets.token_hex(20)}"
        secret_marker = f"CANARY_{secrets.token_hex(20)}"
        markers = [password_marker, altered_password_marker, access_marker, secret_marker]
        user_created = False
        catalog_created = False
        cleanup_ok = True
        try:
            mysql.run(
                f"CREATE USER {sql_literal(user_name)} IDENTIFIED BY {sql_literal(password_marker)};",
                password=root_password, operation="canary CREATE USER",
            )
            user_created = True
            assert_client_output_clear(mysql, markers)
            _rc, authentication = mysql.run(
                f"SHOW AUTHENTICATION FOR {user_name};", password=root_password,
                operation="canary authentication inspection",
            )
            assert_client_output_clear(mysql, markers)
            if user_name not in authentication or "yes" not in authentication.lower():
                raise SafeFailure("Could not verify the canary user's password-authentication state.")
            capture_mysql_as(mysql_binary, user_name, password_marker)
            mysql.run(
                f"ALTER USER {sql_literal(user_name)}@'%' IDENTIFIED BY {sql_literal(altered_password_marker)};",
                password=root_password, operation="canary ALTER USER",
            )
            assert_client_output_clear(mysql, markers)
            capture_mysql_as(mysql_binary, user_name, altered_password_marker)
            statement = "\n".join([
                f"CREATE EXTERNAL CATALOG {sql_identifier(catalog_name)} PROPERTIES (",
                '"type" = "iceberg",',
                '"iceberg.catalog.type" = "hive",',
                '"iceberg.catalog.hive.metastore.uris" = "thrift://hive-metastore:9083",',
                '"aws.s3.enable_ssl" = "false",',
                '"aws.s3.enable_path_style_access" = "true",',
                '"aws.s3.endpoint" = "http://object-store:9000",',
                '"aws.s3.region" = "us-east-1",',
                '"aws.s3.use_instance_profile" = "false",',
                f'"aws.s3.access_key" = "{access_marker}",',
                f'"aws.s3.secret_key" = "{secret_marker}"',
                ");",
            ])
            mysql.run(statement, password=root_password, operation="canary external-catalog creation")
            catalog_created = True
            assert_client_output_clear(mysql, markers)
            _rc, catalog_ddl = mysql.run(
                f"SHOW CREATE CATALOG {sql_identifier(catalog_name)};", password=root_password,
                operation="canary catalog definition inspection",
            )
            assert_client_stderr_clear(mysql, markers)
            if not catalog_ddl:
                raise SafeFailure("Could not inspect the disposable canary catalog definition.")
        finally:
            if catalog_created:
                try:
                    rc, _ = mysql.run(
                        f"DROP CATALOG {sql_identifier(catalog_name)};", password=root_password, allow_error=True
                    )
                    cleanup_ok = cleanup_ok and rc == 0
                except SafeFailure:
                    cleanup_ok = False
            if user_created:
                try:
                    rc, _ = mysql.run(
                        f"DROP USER {sql_literal(user_name)};", password=root_password, allow_error=True
                    )
                    cleanup_ok = cleanup_ok and rc == 0
                except SafeFailure:
                    cleanup_ok = False
        if not cleanup_ok:
            raise SafeFailure("Canary cleanup was incomplete; no passing marker was written.")
        scan_canary_surfaces(markers, started, mysql, root_password, log_dirs)
        marker = {
            "schema": 1,
            "result": "PASS",
            "fe_image": image,
            "fe_config_sha256": config_hash,
            "verified_at": utc_now(),
        }
        write_marker(marker)
        say("Secret-exposure canary passed for the current FE image and configuration.")


def assert_client_output_clear(mysql: MysqlClient, markers: Sequence[str]) -> None:
    output = getattr(mysql, "last_client_output", "")
    if any(marker in output for marker in markers):
        raise SafeFailure("Canary value appeared in SQL client output or diagnostics.")


def assert_client_stderr_clear(mysql: MysqlClient, markers: Sequence[str]) -> None:
    output = getattr(mysql, "last_stderr", "")
    if any(marker in output for marker in markers):
        raise SafeFailure("Canary value appeared in SQL client diagnostics.")


def write_marker(marker: dict[str, object]) -> None:
    data = (json.dumps(marker, sort_keys=True) + "\n").encode("ascii")
    fd, name = tempfile.mkstemp(prefix="canary-marker-", dir=STATE)
    temp = Path(name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, MARKER)
        MARKER.chmod(0o600)
    except OSError:
        try:
            temp.unlink()
        except OSError:
            pass
        raise SafeFailure("Could not store the protected non-secret canary marker.") from None


def require_current_marker(mysql: MysqlClient, root_password: str | None) -> tuple[str, str]:
    image, config_hash, _log_dirs = runtime_fingerprint(mysql, root_password)
    try:
        marker = json.loads(MARKER.read_text(encoding="ascii"))
        mode = stat.S_IMODE(MARKER.stat().st_mode)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise SafeFailure("No valid canary marker exists. Run the standalone canary first.") from None
    if mode != 0o600 or not isinstance(marker, dict):
        raise SafeFailure("Canary marker is malformed or not protected; rerun the standalone canary.")
    if set(marker) != {"schema", "result", "fe_image", "fe_config_sha256", "verified_at"}:
        raise SafeFailure("Canary marker contains unexpected fields; rerun the standalone canary.")
    if (
        marker.get("schema") != 1 or marker.get("result") != "PASS"
        or marker.get("fe_image") != image or marker.get("fe_config_sha256") != config_hash
    ):
        raise SafeFailure("Canary marker is stale or mismatched; rerun the standalone canary.")
    return image, config_hash


def user_exists(mysql: MysqlClient, identity: str, root_password: str) -> bool:
    _rc, output = mysql.run("SHOW USERS;", password=root_password)
    expected = f"'{identity.lower()}'@'%'"
    identities = {line.strip().lower().replace("`", "") for line in output.splitlines()}
    return expected in identities


def table_grants_are_scoped(
    mysql: MysqlClient,
    identity: str,
    root_password: str,
    current_tables: dict[str, set[str]] | None = None,
) -> None:
    _rc, output = mysql.run(
        f"SHOW GRANTS FOR {sql_literal(identity)}@'%';", password=root_password
    )
    public_grants = mysql.run("SHOW GRANTS FOR ROLE public;", password=root_password)[1]
    for line in public_grants.splitlines():
        if "grant" not in line.lower():
            continue
        normalized_public = re.sub(r"[`'\"\s]+", "", line.lower())
        builtin_info_schema = (
            "publicdefault_cataloggrantselectonalltablesindatabaseinformation_schematorolepublic"
        )
        if normalized_public != builtin_info_schema:
            raise SafeFailure("The built-in public role has unexpected grants; refusing to assert least-privilege access.")

    allowed_dbs = {"user_a": {"databasea"}, "user_b": {"databasea", "databaseb"},
                   "write_service_account": {"databasea", "databaseb"}}[identity]
    allowed_privileges = {"select"}
    if identity == "write_service_account":
        allowed_privileges.update({"insert", "update", "delete"})
    lines = [line.lower().replace("`", "") for line in output.splitlines() if "grant" in line.lower()]
    for line in lines:
        normalized = re.sub(r"\s+", " ", line)
        if re.search(r"grant\s+['\"]?public['\"]?\b", normalized) and " to " in normalized:
            continue
        if " on catalog iceberg " in normalized and re.search(r"grant\s+usage\s+on catalog", normalized):
            continue
        table_match = re.search(r"(?:iceberg\.)?([a-z0-9_]+)\.([a-z0-9_]+)\b", normalized)
        db_match = re.search(r"(?:in database|database)\s+([a-z0-9_]+)\b", normalized)
        if not db_match and table_match:
            db_match = table_match
        if not db_match:
            db_match = re.search(r"iceberg\.([a-z0-9_]+)\.(?:\*|all tables)", normalized)
        if not db_match or db_match.group(1) not in allowed_dbs:
            raise SafeFailure(f"Existing privileges for '{identity}' are broader or unrecognized; resolve manually.")
        grant_match = re.search(r"grant\s+(.+?)\s+on\s+", normalized)
        if not grant_match:
            raise SafeFailure(f"Existing privileges for '{identity}' are unrecognized; resolve manually.")
        privileges = {word for word in re.findall(r"[a-z_]+", grant_match.group(1)) if word not in {"privilege"}}
        privileges.discard("all")
        if not privileges or not privileges.issubset(allowed_privileges):
            raise SafeFailure(f"Existing privileges for '{identity}' exceed the approved access matrix.")
        dml_privileges = privileges.intersection({"insert", "update", "delete"})
        if dml_privileges and (identity != "write_service_account" or not table_match):
            raise SafeFailure("Writer DML grants must be scoped to explicitly existing tables.")
        if dml_privileges and current_tables is not None:
            database_name, table_name = table_match.group(1), table_match.group(2)
            if table_name not in current_tables.get(database_name, set()):
                raise SafeFailure("Writer has a DML grant outside the current existing-table set.")
        if identity == "user_a" and "databaseb" in normalized:
            raise SafeFailure("user_a has unexpected databaseB access; no grants were changed.")


def inspect_catalog(mysql: MysqlClient, root_password: str | None, secret: str) -> bool:
    _rc, output = mysql.run("SHOW CATALOGS;", password=root_password)
    # SHOW CATALOGS returns multiple tab-separated columns. Compare only the
    # catalog name, while preserving support for clients that return one column.
    exists = any(line.split("\t", 1)[0].strip().strip("` ").lower() == CATALOG for line in output.splitlines())
    if not exists:
        return False
    _rc, output = mysql.run(f"SHOW CREATE CATALOG {sql_identifier(CATALOG)};", password=root_password)
    # StarRocks masks credentials in SHOW CREATE CATALOG. Validate the exact
    # non-secret properties plus the server-rendered mask; never expect or emit
    # credential values from metadata output.
    required = [
        '"type"="iceberg"',
        '"iceberg.catalog.type"="hive"',
        '"iceberg.catalog.hive.metastore.uris"="thrift://hive-metastore:9083"',
        '"aws.s3.endpoint"="http://object-store:9000"',
        '"aws.s3.enable_ssl"="false"',
        '"aws.s3.enable_path_style_access"="true"',
        '"aws.s3.region"="us-east-1"',
        '"aws.s3.use_instance_profile"="false"',
    ]
    folded = output.lower().replace(" ", "")
    # StarRocks 4.1 masks catalog values with a fixed six-asterisk marker.
    access_key_mask = "st******ks"
    secret_mask = secret[:2] + "******" + secret[-2:]
    required.extend([
        f'"aws.s3.access_key"="{access_key_mask}"',
        f'"aws.s3.secret_key"="{secret_mask}"',
    ])
    if any(item.lower().replace(" ", "") not in folded for item in required):
        raise SafeFailure("Existing Iceberg catalog is conflicting or cannot be safely inspected; it was preserved.")
    # The DDL masks the credential body, so confirm that the existing catalog
    # can actually read an existing sample object before treating it as aligned.
    sample_tables = existing_tables(mysql, root_password or "", "databaseA")
    mysql.run(
        f"SELECT * FROM {sql_identifier(CATALOG)}.{sql_identifier('databaseA')}."
        f"{sql_identifier(sample_tables[0])} LIMIT 1;",
        password=root_password,
        operation="existing Iceberg sample read preflight",
    )
    return True


def catalog_create_sql(secret: str) -> str:
    # Unit 1 defines this stable, non-secret RustFS access-key ID in code.
    access_key = "starrocks"
    values = [
        ('"type"', '"iceberg"'),
        ('"iceberg.catalog.type"', '"hive"'),
        ('"iceberg.catalog.hive.metastore.uris"', '"thrift://hive-metastore:9083"'),
        ('"aws.s3.enable_ssl"', '"false"'),
        ('"aws.s3.enable_path_style_access"', '"true"'),
        ('"aws.s3.endpoint"', '"http://object-store:9000"'),
        ('"aws.s3.region"', '"us-east-1"'),
        ('"aws.s3.use_instance_profile"', '"false"'),
        ('"aws.s3.access_key"', f'"{access_key}"'),
        ('"aws.s3.secret_key"', f'"{secret}"'),
    ]
    props = ",\n  ".join(f"{key} = {value}" for key, value in values)
    return f"CREATE EXTERNAL CATALOG {sql_identifier(CATALOG)} PROPERTIES (\n  {props}\n);"


def reconcile_catalog(mysql: MysqlClient, root_password: str | None, secret: str, exists: bool) -> None:
    if not exists:
        mysql.run(catalog_create_sql(secret), password=root_password)


def capture_mysql_as(binary: str, identity: str, password: str) -> None:
    # Use the same protected option-file mechanism, but never print returned server data.
    args = [binary]
    fd, name = tempfile.mkstemp(prefix="mysql-auth-", dir=STATE, text=True)
    path = Path(name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(f'[client]\nuser="{identity}"\npassword="{password}"\n')
            stream.flush()
            os.fsync(stream.fileno())
        args.extend([
            f"--defaults-file={path}", "--protocol=TCP", f"--host={HOST}", f"--port={PORT}",
            f"--user={identity}", "--connect-timeout=4", "--batch", "--raw", "--skip-column-names", "--silent",
        ])
        result = capture(args, stdin=b"SELECT CURRENT_USER();\n")
    finally:
        try:
            path.unlink()
        except OSError:
            raise SafeFailure("Could not remove temporary SQL authentication material.") from None
    identity_result = result.stdout.decode("utf-8", errors="replace").lower()
    if result.returncode != 0 or identity.lower() not in identity_result:
        raise SafeFailure("SQL identity authentication check failed.")


def existing_tables(mysql: MysqlClient, root_password: str, database: str) -> list[str]:
    output = mysql.run(
        f"SHOW TABLES FROM {sql_identifier(CATALOG)}.{sql_identifier(database)};",
        password=root_password,
    )[1]
    tables = sorted({line.strip().strip("` ") for line in output.splitlines() if line.strip()})
    if not tables or any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", table) for table in tables):
        raise SafeFailure(f"No safely addressable existing tables were found in '{database}'.")
    return tables


def reconcile_grants(
    mysql: MysqlClient, identity: str, root_password: str, writer_tables: dict[str, list[str]] | None = None
) -> None:
    target = f"USER {sql_literal(identity)}@'%'"
    statements = [
        f"GRANT USAGE ON CATALOG {sql_identifier(CATALOG)} TO {target};",
        f"SET CATALOG {sql_identifier(CATALOG)};",
    ]
    if identity == "user_a":
        statements.append(f"GRANT SELECT ON ALL TABLES IN DATABASE `databaseA` TO {target};")
    elif identity == "user_b":
        for database in ("databaseA", "databaseB"):
            statements.append(f"GRANT SELECT ON ALL TABLES IN DATABASE `{database}` TO {target};")
    elif identity == "write_service_account":
        for database in ("databaseA", "databaseB"):
            statements.append(f"GRANT SELECT ON ALL TABLES IN DATABASE `{database}` TO {target};")
            for table in (writer_tables or {}).get(database, []):
                statements.append(
                    f"GRANT INSERT, UPDATE, DELETE ON TABLE `{database}`.`{table}` TO {target};"
                )
    mysql.run("\n".join(statements), password=root_password)
    table_grants_are_scoped(mysql, identity, root_password)


def reconcile_admin(mysql: MysqlClient, root_password: str) -> None:
    target = f"USER {sql_literal('admin')}@'%'"
    mysql.run(
        f"GRANT db_admin, user_admin, cluster_admin, security_admin TO {target};",
        password=root_password,
    )
    mysql.run(f"SET DEFAULT ROLE ALL TO {sql_literal('admin')}@'%';", password=root_password)


def ensure_backend(mysql_binary: str) -> None:
    """Register the BE using protected host-side SQL credentials after startup."""
    ensure_runtime_dirs()
    mysql = MysqlClient(mysql_binary)
    root_password = root_connection(mysql)
    if root_password is not None:
        require_current_marker(mysql, root_password)
    _rc, backends = mysql.run("SHOW BACKENDS;", password=root_password, operation="backend registration preflight")
    if not any("starrocks-be" in line.lower() for line in backends.splitlines()):
        mysql.run(
            'ALTER SYSTEM ADD BACKEND "starrocks-be:9050";',
            password=root_password,
            operation="BE registration",
        )
    for _ in range(30):
        _rc, backends = mysql.run("SHOW BACKENDS;", password=root_password, operation="backend readiness check")
        for line in backends.splitlines():
            columns = line.split("\t")
            if len(columns) > 8 and columns[1].lower() == "starrocks-be" and columns[8].lower() == "true":
                say("StarRocks BE is registered and alive.")
                return
        import time
        time.sleep(2)
    raise SafeFailure("StarRocks BE did not become alive after host-side registration.")


def bootstrap(mysql_binary: str) -> None:
    ensure_runtime_dirs()
    with ProjectLock():
        mysql = MysqlClient(mysql_binary)
        root_password = root_connection(mysql)
        require_current_marker(mysql, root_password)
        rustfs_secret = file_secret(CREDENTIALS / "rustfs-starrocks-secret-key", "StarRocks RustFS secret-key")
        if not re.fullmatch(r"[0-9a-fA-F]{32,256}", rustfs_secret):
            raise SafeFailure("StarRocks RustFS secret-key file has an unsupported format.")

        # Inspect all existing identities, credentials, grants, and catalog state
        # before the first SQL mutation. Unknown state fails closed.
        present: dict[str, bool] = {}
        passwords: dict[str, str | None] = {}
        for identity in IDENTITIES:
            present[identity] = user_exists(mysql, identity, root_password)
            path = credential_path(identity)
            if present[identity] and not path.exists():
                raise SafeFailure(f"SQL identity '{identity}' exists without its protected credential file; resolve manually.")
            passwords[identity] = read_password(identity) if path.exists() else None
            if present[identity] and passwords[identity] is not None:
                capture_mysql_as(mysql_binary, identity, passwords[identity])
            if present[identity] and identity != "admin":
                table_grants_are_scoped(mysql, identity, root_password)

        if passwords["admin"] and root_password and passwords["admin"] == root_password:
            raise SafeFailure("The protected root and admin credential files must contain distinct passwords.")
        catalog_exists = inspect_catalog(mysql, root_password, rustfs_secret)

        # Only after all drift preflight passes may root credentials be established.
        if root_password is None:
            root_password = create_password("root")
            mysql.run(
                f"ALTER USER 'root'@'%' IDENTIFIED BY {sql_literal(root_password)};",
                password=None,
            )
        mysql.run("SELECT 1;", password=root_password)

        # Resolve all local credentials before any user/catalog mutation.
        for identity in IDENTITIES:
            if passwords[identity] is None:
                passwords[identity] = create_password(identity)
        if passwords["admin"] == root_password:
            raise SafeFailure("The protected root and admin credential files must contain distinct passwords.")

        # Create the external catalog only when absent; the canary gate above is
        # mandatory because the DDL contains the RustFS secret.
        reconcile_catalog(mysql, root_password, rustfs_secret, catalog_exists)
        for identity in IDENTITIES:
            password = passwords[identity]
            assert password is not None
            if not present[identity]:
                mysql.run(
                    f"CREATE USER {sql_literal(identity)} IDENTIFIED BY {sql_literal(password)};",
                    password=root_password,
                )
                capture_mysql_as(mysql_binary, identity, password)

        # All app accounts now exist and have confirmed credentials. Check for
        # externally granted privileges again before applying any new grants.
        for identity in ("user_a", "user_b", "write_service_account"):
            table_grants_are_scoped(mysql, identity, root_password)

        namespaces = mysql.run(f"SHOW DATABASES FROM {sql_identifier(CATALOG)};", password=root_password)[1]
        normalized_namespaces = {line.strip().strip("` ").lower() for line in namespaces.splitlines()}
        if not {"databasea", "databaseb"}.issubset(normalized_namespaces):
            raise SafeFailure("The Iceberg catalog is reachable but expected sample databases were not discovered.")

        writer_tables = {
            database: existing_tables(mysql, root_password, database)
            for database in ("databaseA", "databaseB")
        }
        writer_table_sets = {
            database.lower(): {table.lower() for table in tables}
            for database, tables in writer_tables.items()
        }
        table_grants_are_scoped(mysql, "write_service_account", root_password, writer_table_sets)

        for identity in ("user_a", "user_b", "write_service_account"):
            reconcile_grants(mysql, identity, root_password, writer_tables)
        reconcile_admin(mysql, root_password)
        for identity, password in passwords.items():
            assert password is not None
            capture_mysql_as(mysql_binary, identity, password)
        say("StarRocks SQL bootstrap completed. Catalog, identities, grants, and authentication checks passed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Operator-only StarRocks SQL bootstrap controls")
    parser.add_argument("operation", choices=("canary", "bootstrap", "ensure-backend"))
    args = parser.parse_args()
    try:
        mysql_binary = require_command("mysql")
        if args.operation == "canary":
            canary(mysql_binary)
        elif args.operation == "ensure-backend":
            ensure_backend(mysql_binary)
        else:
            bootstrap(mysql_binary)
        return 0
    except SafeFailure as exc:
        say(f"ERROR: {exc}", error=True)
        return 1
    except KeyboardInterrupt:
        say("ERROR: interrupted; inspect the protected workflow state before retrying.", error=True)
        return 130
    except Exception:
        say("ERROR: unexpected internal failure; details suppressed.", error=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
