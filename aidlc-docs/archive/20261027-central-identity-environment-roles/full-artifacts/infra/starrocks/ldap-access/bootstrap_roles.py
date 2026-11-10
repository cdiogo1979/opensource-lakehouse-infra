#!/usr/bin/env python3
"""Bootstrap StarRocks native roles mapped to FreeIPA LDAP groups.

This command is intentionally restricted to a disposable StarRocks test FE.
It never targets the default lakehouse FE or executes against a generic host.
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
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FE_CONTAINER = "starrocks-ldap-test-fe"
COMPOSE_PROJECT = "starrocks-ldap-test"
COMPOSE_SERVICE = "starrocks-ldap-test-fe"
USERNAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
GROUPS = {
    "lakehouse-developers": "lakehouse_developer",
    "lakehouse-analysts": "lakehouse_analyst",
    "lakehouse-writers": "lakehouse_writer",
}
USERS = ("developer-user", "analyst-user", "write-service-account")


class BootstrapError(Exception):
    """Safe operator-facing failure; subprocess output is never included."""


def read_secret(path: Path, label: str) -> str:
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
        value = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        raise BootstrapError(f"Required {label} file is unavailable.") from None
    if mode != 0o600 or not value or "\n" in value or "\r" in value:
        raise BootstrapError(f"Required {label} file must contain one value and have mode 0600.")
    return value


def require_private_test_path(path: Path, relative_directory: str, label: str) -> Path:
    base = ROOT / relative_directory
    try:
        resolved = path.resolve(strict=True)
        resolved_base = base.resolve(strict=True)
    except OSError:
        raise BootstrapError(f"The isolated test {label} path is unavailable.") from None
    if not resolved.is_relative_to(resolved_base) or path.is_symlink():
        raise BootstrapError(f"The {label} must come from the isolated test secret directory.")
    return resolved


def sql_literal(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def sql_identifier(value: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise BootstrapError("A catalog/database identifier has an unsupported format.")
    return f"`{value}`"


def parse_database_list(raw: str, label: str) -> list[str]:
    names = [name.strip() for name in raw.split(",") if name.strip()]
    if not names or any(not IDENTIFIER_PATTERN.fullmatch(name) for name in names):
        raise BootstrapError(f"Provide a non-empty, comma-separated list of valid {label} database names.")
    if len(set(names)) != len(names):
        raise BootstrapError(f"The {label} database list contains duplicates.")
    return names


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="apply to the isolated StarRocks test FE")
    parser.add_argument("--catalog", default="iceberg")
    parser.add_argument("--prod-databases", required=True, help="comma-separated production Hive database names")
    parser.add_argument("--dev-databases", required=True, help="comma-separated development Hive database names")
    parser.add_argument("--uat-databases", required=True, help="comma-separated UAT Hive database names")
    parser.add_argument("--mv-prod-database", default="default_lh", help="internal default_catalog database for production materialized views")
    parser.add_argument("--mv-dev-database", default="default_lhdev", help="internal default_catalog database for development materialized views")
    parser.add_argument("--mv-uat-database", default="default_lhuat", help="internal default_catalog database for UAT materialized views")
    parser.add_argument(
        "--ldap-url", default="ldaps://ipa.ranger-test.lakehouse.test:636",
        help="isolated FreeIPA LDAPS endpoint; do not use a production endpoint in this test command",
    )
    parser.add_argument(
        "--ldap-user-base-dn", default="cn=users,cn=accounts,dc=lakehouse,dc=test",
    )
    parser.add_argument(
        "--ldap-group-base-dn", default="cn=groups,cn=accounts,dc=lakehouse,dc=test",
    )
    parser.add_argument(
        "--ldap-bind-dn",
        default="uid=ranger-usersync-bind,cn=users,cn=accounts,dc=lakehouse,dc=test",
        help="read-only isolated directory account DN",
    )
    parser.add_argument(
        "--ldap-bind-password-file",
        type=Path,
        default=ROOT / ".runtime/ranger-test/secrets/ranger-usersync-bind-password",
    )
    parser.add_argument(
        "--admin-option-file", type=Path,
        default=ROOT / ".runtime/starrocks-ldap-test/secrets/mysql-admin.cnf",
        help="protected MySQL client option file for the isolated test FE admin",
    )
    return parser.parse_args()


def validate_target() -> None:
    docker = shutil.which("docker")
    if docker is None:
        raise BootstrapError("Docker CLI is required to verify the isolated target FE.")
    result = subprocess.run(
        [docker, "inspect", FE_CONTAINER], capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise BootstrapError("The isolated StarRocks test FE is not present; no SQL was applied.")
    try:
        item = json.loads(result.stdout)[0]
    except (IndexError, json.JSONDecodeError):
        raise BootstrapError("Could not verify the isolated FE identity; no SQL was applied.") from None
    labels = item.get("Config", {}).get("Labels") or {}
    if (item.get("Name", "").lstrip("/") != FE_CONTAINER
            or labels.get("com.docker.compose.project") != COMPOSE_PROJECT
            or labels.get("com.docker.compose.service") != COMPOSE_SERVICE):
        raise BootstrapError("The StarRocks FE does not have the required disposable test identity; no SQL was applied.")
    bindings = item.get("HostConfig", {}).get("PortBindings") or {}
    if any(binding for binding in bindings.values()):
        raise BootstrapError("The isolated FE must not publish any host ports; no SQL was applied.")


def create_sql(args: argparse.Namespace, ldap_password: str) -> str:
    prod = parse_database_list(args.prod_databases, "production")
    dev = parse_database_list(args.dev_databases, "development")
    uat = parse_database_list(args.uat_databases, "UAT")
    mv_databases = [args.mv_prod_database, args.mv_dev_database, args.mv_uat_database]
    if any(not IDENTIFIER_PATTERN.fullmatch(name) for name in mv_databases) or len(set(mv_databases)) != 3:
        raise BootstrapError("Materialized-view databases must be three distinct valid database names.")
    sets = [set(prod), set(dev), set(uat)]
    if sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]:
        raise BootstrapError("Environment database lists must be disjoint to preserve the access boundary.")
    if not args.ldap_url.startswith("ldaps://"):
        raise BootstrapError("LDAP group lookup must use LDAPS.")
    if not args.catalog or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", args.catalog):
        raise BootstrapError("The StarRocks external catalog name has an unsupported format.")
    if not USERNAME_PATTERN.fullmatch("developer-user"):
        raise BootstrapError("The configured LDAP login names have an unsupported format.")

    group_filter = "(&(objectClass=groupOfNames)(|" + "".join(
        f"(cn={group})" for group in GROUPS
    ) + "))"
    statements = [
        "-- Idempotent StarRocks native LDAP role bootstrap for the disposable FE only.",
        "-- LDAP users are explicitly registered because this StarRocks version's",
        "-- security-integration mode is not used with native authorization.",
        "CREATE GROUP PROVIDER lakehouse_freeipa_groups PROPERTIES (",
        '  "type"="ldap",',
        f'  "ldap_conn_url"={sql_literal(args.ldap_url)},',
        f'  "ldap_bind_root_dn"={sql_literal(args.ldap_bind_dn)},',
        f'  "ldap_bind_root_pwd"={sql_literal(ldap_password)},',
        f'  "ldap_bind_base_dn"={sql_literal(args.ldap_group_base_dn)},',
        f'  "ldap_group_filter"={sql_literal(group_filter)},',
        '  "ldap_group_identifier_attr"="cn",',
        '  "ldap_group_member_attr"="member",',
        '  "ldap_ssl_conn_allow_insecure"="false",',
        '  "ldap_ssl_conn_trust_store_path"="/run/ldap/freeipa-test-ca.crt",',
        '  "ldap_cache_refresh_interval"="60",',
        '  "ldap_cache_max_stale_time"="300"',
        ");",
        # Native LDAP-authenticated users only consult a Group Provider when
        # it is listed in the cluster-wide group_provider setting.
        'ADMIN SET FRONTEND CONFIG ("group_provider" = "lakehouse_freeipa_groups");',
    ]
    # Do not pin an explicit LDAP DN with `AS '<dn>'`: StarRocks' legacy
    # per-user DN form does not participate in LDAP group resolution. The
    # isolated FE uses authentication_ldap_simple_bind_dn_pattern so LDAP
    # authentication records the resolved DN for the external group provider.
    for username in USERS:
        if not USERNAME_PATTERN.fullmatch(username):
            raise BootstrapError("A configured LDAP login name has an unsupported format.")
        statements.append(f"CREATE USER IF NOT EXISTS `{username}` IDENTIFIED WITH authentication_ldap_simple;")
    for role in GROUPS.values():
        statements.append(f"CREATE ROLE IF NOT EXISTS `{role}`;")
    statements.append(f"SET CATALOG `{args.catalog}`;")

    def grant_read(role: str, databases: list[str]) -> None:
        statements.append(f"GRANT USAGE ON CATALOG `{args.catalog}` TO ROLE `{role}`;")
        for database in databases:
            db = sql_identifier(database)
            statements.append(f"GRANT SELECT ON ALL TABLES IN DATABASE {db} TO ROLE `{role}`;")
            statements.append(f"GRANT SELECT ON ALL VIEWS IN DATABASE {db} TO ROLE `{role}`;")

    def grant_insert(role: str, databases: list[str]) -> None:
        for database in databases:
            statements.append(
                f"GRANT INSERT ON ALL TABLES IN DATABASE {sql_identifier(database)} TO ROLE `{role}`;"
            )

    all_databases = prod + dev + uat
    grant_read("lakehouse_developer", all_databases)
    grant_insert("lakehouse_developer", dev)
    grant_read("lakehouse_analyst", prod)
    grant_read("lakehouse_writer", all_databases)
    grant_insert("lakehouse_writer", all_databases)

    # Keep analytical outputs in the internal catalog so each environment has
    # its own database. These are intentionally separate from the Iceberg
    # source catalog even when the database names match.
    statements.append("SET CATALOG `default_catalog`;")
    for database in mv_databases:
        db = sql_identifier(database)
        statements.append(f"CREATE DATABASE IF NOT EXISTS {db};")
    for role in GROUPS.values():
        statements.append("GRANT USAGE ON CATALOG `default_catalog` TO ROLE `" + role + "`;")

    def grant_mv_read(role: str, databases: list[str]) -> None:
        for database in databases:
            statements.append(
                f"GRANT SELECT ON ALL MATERIALIZED VIEWS IN DATABASE {sql_identifier(database)} TO ROLE `{role}`;"
            )

    grant_mv_read("lakehouse_developer", mv_databases)
    grant_mv_read("lakehouse_analyst", [args.mv_prod_database])
    grant_mv_read("lakehouse_writer", mv_databases)
    statements.append(
        "GRANT CREATE MATERIALIZED VIEW ON DATABASE "
        f"{sql_identifier(args.mv_prod_database)}, {sql_identifier(args.mv_dev_database)}, "
        f"{sql_identifier(args.mv_uat_database)} TO ROLE `lakehouse_writer`;"
    )
    for database in mv_databases:
        statements.append(
            "GRANT ALTER, REFRESH, DROP ON ALL MATERIALIZED VIEWS IN DATABASE "
            f"{sql_identifier(database)} TO ROLE `lakehouse_writer`;"
        )
    for group_name, role in GROUPS.items():
        statements.append(f"GRANT `{role}` TO EXTERNAL GROUP `{group_name}`;")
    # Asynchronous MV refresh tasks do not inherit LDAP group-derived roles.
    # The fixed service account is the sole exception: grant the writer role
    # directly and make it a default role so background refresh sees source
    # SELECT. Removing its LDAP group is not a revocation operation; disable
    # the FreeIPA account to block authentication.
    statements.append("GRANT `lakehouse_writer` TO USER 'write-service-account'@'%';")
    statements.append("ALTER USER 'write-service-account'@'%' DEFAULT ROLE ALL;")
    return "\n".join(statements) + "\n"


def apply_sql(sql: str, option_file: Path) -> None:
    option_file = require_private_test_path(option_file, ".runtime/starrocks-ldap-test/secrets", "admin option file")
    expected_option_file = ROOT / ".runtime/starrocks-ldap-test/secrets/mysql-admin.cnf"
    if option_file != expected_option_file.resolve(strict=True):
        raise BootstrapError("Use the mounted isolated StarRocks admin option file; no SQL was applied.")
    try:
        mode = stat.S_IMODE(option_file.stat().st_mode)
    except OSError:
        raise BootstrapError("The isolated StarRocks admin option file is unavailable; no SQL was applied.") from None
    if mode != 0o600:
        raise BootstrapError("The isolated StarRocks admin option file must have mode 0600; no SQL was applied.")
    docker = shutil.which("docker")
    if docker is None:
        raise BootstrapError("Docker CLI is required to connect to the isolated FE; no SQL was applied.")
    cli = [docker, "exec", "-i", FE_CONTAINER, "mysql",
           "--defaults-extra-file=/run/admin/mysql-admin.cnf", "--protocol=TCP", "--host=127.0.0.1",
           "--port=9030", "--connect-timeout=5", "--batch", "--silent"]
    # StarRocks 4.1.6 rejects ALTER GROUP PROVIDER even though newer docs list
    # it. This command is hard-guarded to the disposable FE, so replace only
    # the named test provider and reassert its external-group grants below.
    provider_statement = "CREATE GROUP PROVIDER lakehouse_freeipa_groups PROPERTIES ("
    if provider_statement not in sql:
        raise BootstrapError("The expected isolated LDAP provider statement is missing; no SQL was applied.")
    sql = sql.replace(
        provider_statement,
        "DROP GROUP PROVIDER IF EXISTS lakehouse_freeipa_groups;\n" + provider_statement,
        1,
    )
    result = subprocess.run(
        cli,
        input=sql, text=True, capture_output=True, check=False,
    )
    if result.returncode != 0:
        raise BootstrapError("StarRocks rejected the LDAP role bootstrap; client details were suppressed.")


def main() -> int:
    args = parse_args()
    try:
        validate_target()
        args.ldap_bind_password_file = require_private_test_path(
            args.ldap_bind_password_file, ".runtime/ranger-test/secrets", "LDAP bind credential"
        )
        ldap_password = read_secret(args.ldap_bind_password_file, "LDAP read-only bind credential")
        sql = create_sql(args, ldap_password)
        if args.apply:
            apply_sql(sql, args.admin_option_file)
            print("StarRocks LDAP group provider, users, roles, grants, and group mappings applied to the isolated test FE.")
        else:
            print("Dry run passed: isolated FE target and role scopes are valid; SQL and credentials were not displayed or applied.")
            print("Role scope: developer=read all/write dev/read MVs in all environments; analyst=read prod/read prod MVs; writer=read/write all/manage MVs in all environments; unrelated DDL/security grants are not included.")
    except BootstrapError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
