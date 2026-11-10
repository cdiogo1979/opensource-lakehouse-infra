#!/usr/bin/env python3
"""Read-only preflight or explicit apply of the production FreeIPA group provider.

This is intentionally separate from the disposable-FE bootstrap. It is pinned
to the existing production FE identity and requires the production network,
LDAPS CA, FE SQL TLS, and protected credentials to be present.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FE = "iceberg-poc-starrocks-fe"
EXPECTED_IMAGE = "local/starrocks-fe:4.1.6-kerberos"
FE_CONF = "/opt/starrocks/fe/conf/fe.conf"
PROVIDER = "lakehouse_freeipa_groups"
LDAP_HOST = os.environ.get("FREEIPA_PRODUCTION_HOSTNAME", "ipa-prod.lakehouse.local")
LDAP_BIND_DN = "uid=starrocks-ldap-reader,cn=users,cn=accounts,dc=lakehouse,dc=local"
GROUPS = ("lakehouse-developers", "lakehouse-analysts", "lakehouse-writers")
GROUP_BASE = "cn=groups,cn=accounts,dc=lakehouse,dc=local"
CA_FILE = ROOT / ".runtime/freeipa-production/ca.crt"
SQL_CA = ROOT / ".runtime/starrocks-production/sql-tls/starrocks-production.crt"
LDAP_PASSWORD = ROOT / ".runtime/credentials/freeipa-production-starrocks-reader-password"
ADMIN_PASSWORD = ROOT / ".runtime/credentials/starrocks-admin-password"


class SafeFailure(Exception):
    """Operator-safe failure without subprocess or secret details."""


def run(args: list[str], *, input_text: str | None = None, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args, input=input_text, capture_output=True, text=True, check=False,
            timeout=timeout, close_fds=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise SafeFailure("A required local or Docker operation failed; details were suppressed.") from None


def private_secret(path: Path, label: str) -> str:
    try:
        if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise SafeFailure(f"The protected {label} file is missing or has unsafe permissions.")
        value = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        raise SafeFailure(f"The protected {label} file is unavailable.") from None
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise SafeFailure(f"The protected {label} file has an invalid format.")
    return value


def require_public_certificate(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise SafeFailure(f"The {label} certificate is unavailable.")
    openssl = shutil.which("openssl")
    if not openssl or run([openssl, "x509", "-in", str(path), "-noout"], timeout=10).returncode:
        raise SafeFailure(f"The {label} file is not a valid X.509 certificate.")


def inspect_fe(expected_project: str) -> dict:
    docker = shutil.which("docker")
    if not docker:
        raise SafeFailure("Docker CLI is unavailable; no SQL was sent.")
    result = run([docker, "inspect", FE])
    if result.returncode:
        raise SafeFailure("The expected production StarRocks FE is unavailable; no SQL was sent.")
    try:
        item = json.loads(result.stdout)[0]
    except (IndexError, json.JSONDecodeError):
        raise SafeFailure("Could not verify the production FE identity; no SQL was sent.") from None
    labels = item.get("Config", {}).get("Labels") or {}
    if (
        item.get("Name", "").lstrip("/") != FE
        or item.get("Config", {}).get("Image") != EXPECTED_IMAGE
        or labels.get("com.docker.compose.project") != expected_project
        or labels.get("com.docker.compose.service") != "starrocks-fe"
        or item.get("State", {}).get("Health", {}).get("Status") != "healthy"
    ):
        raise SafeFailure("The running FE does not match the expected production Compose identity/image/health; no SQL was sent.")
    bindings = item.get("HostConfig", {}).get("PortBindings") or {}
    sql_bindings = bindings.get("9030/tcp") or []
    if not any(binding.get("HostIp") == "127.0.0.1" and binding.get("HostPort") == "9030" for binding in sql_bindings):
        raise SafeFailure("The production FE SQL port is not bound only to the expected loopback endpoint; no SQL was sent.")
    networks = item.get("NetworkSettings", {}).get("Networks") or {}
    if "iceberg-poc-net" not in networks or "iceberg-poc-freeipa-production-net" not in networks:
        raise SafeFailure("The production FE is not attached to both approved networks; no SQL was sent.")
    mounts = {m.get("Destination") for m in item.get("Mounts", [])}
    expected_mounts = {
        "/run/ldap/freeipa-production-ca.crt",
        "/run/sql-tls/starrocks-production.jks",
        "/run/sql-tls/keystore-password",
    }
    if not expected_mounts.issubset(mounts):
        raise SafeFailure("The production FE does not have all expected LDAP and SQL TLS mounts; no SQL was sent.")
    conf = run([docker, "exec", FE, "cat", FE_CONF])
    if conf.returncode:
        raise SafeFailure("Could not inspect the production FE LDAP/TLS settings; no SQL was sent.")
    for key, value in (
        ("authentication_ldap_simple_server_host", LDAP_HOST),
        ("authentication_ldap_simple_server_port", "636"),
        ("authentication_ldap_simple_bind_dn_pattern", "uid=${USER},cn=users,cn=accounts,dc=lakehouse,dc=local"),
        ("authentication_ldap_simple_ssl_conn_allow_insecure", "false"),
        ("authentication_ldap_simple_ssl_conn_trust_store_path", "/run/ldap/freeipa-production-ca.crt"),
        ("ssl_force_secure_transport", "true"),
        ("ssl_keystore_location", "/run/sql-tls/starrocks-production.jks"),
    ):
        if not re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*{re.escape(value)}\s*$", conf.stdout):
            raise SafeFailure(f"The production FE setting '{key}' is absent or differs from the reviewed value; no SQL was sent.")
    return item


def mysql_query(sql: str, password: str, mysql: str, sql_ca: Path) -> str:
    runtime = ROOT / ".runtime/state"
    if runtime.is_symlink():
        raise SafeFailure("The protected SQL client state directory is a symbolic link.")
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    runtime.chmod(0o700)
    if not runtime.is_dir() or stat.S_IMODE(runtime.stat().st_mode) != 0o700:
        raise SafeFailure("The SQL client state directory is not owner-only.")
    fd, name = tempfile.mkstemp(prefix="production-ldap-mysql-", dir=runtime, text=True)
    option_file = Path(name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(f'[client]\nuser="admin"\npassword="{password}"\n')
            stream.write('protocol=TCP\nhost=127.0.0.1\nport=9030\n')
            stream.write('ssl-mode=VERIFY_IDENTITY\n')
            stream.write(f'ssl-ca="{sql_ca}"\n')
            stream.flush()
            os.fsync(stream.fileno())
        result = run([
            mysql, f"--defaults-file={option_file}", "--connect-timeout=5",
            "--batch", "--raw", "--skip-column-names", "--silent",
        ], input_text=sql, timeout=40)
        if result.returncode:
            raise SafeFailure("The verified TLS SQL request failed; client diagnostics were suppressed.")
        return result.stdout
    finally:
        option_file.unlink(missing_ok=True)


def provider_sql(password: str) -> str:
    escaped = password.replace("\\", "\\\\").replace("'", "''")
    group_filter = "(&(objectClass=groupOfNames)(|" + "".join(f"(cn={name})" for name in GROUPS) + "))"
    return "\n".join((
        f"CREATE GROUP PROVIDER {PROVIDER} PROPERTIES (",
        '  "type"="ldap",',
        f'  "ldap_conn_url"="ldaps://{LDAP_HOST}:636",',
        f'  "ldap_bind_root_dn"="{LDAP_BIND_DN}",',
        f'  "ldap_bind_root_pwd"="{escaped}",',
        f'  "ldap_bind_base_dn"="{GROUP_BASE}",',
        f'  "ldap_group_filter"="{group_filter}",',
        '  "ldap_group_identifier_attr"="cn",',
        '  "ldap_group_member_attr"="member",',
        '  "ldap_ssl_conn_allow_insecure"="false",',
        '  "ldap_ssl_conn_trust_store_path"="/run/ldap/freeipa-production-ca.crt",',
        '  "ldap_cache_refresh_interval"="60",',
        '  "ldap_cache_max_stale_time"="300"',
        ");",
        f'ADMIN SET FRONTEND CONFIG ("group_provider" = "{PROVIDER}");',
        "",
    ))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="create the named provider on the guarded production FE")
    parser.add_argument("--compose-project", required=True, help="exact Compose project label reported by Docker inspect")
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", args.compose_project):
            raise SafeFailure("The Compose project label has an unsupported format.")
        inspect_fe(args.compose_project)
        require_public_certificate(CA_FILE, "production FreeIPA CA")
        require_public_certificate(SQL_CA, "StarRocks SQL CA")
        ldap_password = private_secret(LDAP_PASSWORD, "production LDAP reader password")
        admin_password = private_secret(ADMIN_PASSWORD, "production StarRocks admin password")
        mysql = shutil.which(os.environ.get("MYSQL_CLI", "mysql"))
        if not mysql:
            raise SafeFailure("A MySQL-compatible CLI is unavailable; no SQL was sent.")

        show = mysql_query("SHOW GROUP PROVIDERS;\n", admin_password, mysql, SQL_CA)
        if PROVIDER.casefold() in show.casefold():
            raise SafeFailure("The named provider already exists. Reconcile it through a separately reviewed update; no SQL was sent.")
        if show.strip():
            raise SafeFailure("A different LDAP group provider already exists. Resolve provider coexistence before proceeding; no SQL was sent.")

        users = mysql_query("SHOW USERS;\n", admin_password, mysql, SQL_CA)
        legacy_writer_exists = bool(re.search(r"(?m)^write_service_account\s", users))
        ldap_writer_exists = bool(re.search(r"(?m)^write-service-account\s", users))
        print(
            "Writer identity inventory: existing underscore account present="
            f"{str(legacy_writer_exists).lower()}, LDAP hyphen account present="
            f"{str(ldap_writer_exists).lower()}; no equivalence or grant transfer is assumed."
        )
        if args.apply:
            mysql_query(provider_sql(ldap_password), admin_password, mysql, SQL_CA)
            readback = mysql_query(f"SHOW CREATE GROUP PROVIDER {PROVIDER};\n", admin_password, mysql, SQL_CA)
            if PROVIDER not in readback or "ldap" not in readback.casefold():
                raise SafeFailure("Provider readback did not confirm the expected provider; preserve state and inspect manually.")
            print("Production LDAP group provider created and read back over identity- and CA-verified SQL TLS.")
        else:
            print("Production FE/network/TLS guard and read-only provider preflight passed. No SQL changes were applied.")
            print("Dry-run scope: create only the missing FreeIPA LDAP Group Provider; no users, roles, grants, or groups are created.")
        return 0
    except SafeFailure as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
