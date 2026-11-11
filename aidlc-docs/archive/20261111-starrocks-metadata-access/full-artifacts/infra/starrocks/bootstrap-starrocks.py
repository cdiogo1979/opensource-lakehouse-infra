#!/usr/bin/env python3
"""Idempotent StarRocks bootstrap: runtime, Iceberg catalogs, roles, and MV databases.

--runtime-only (run by `lakehouse.sh start`) sets the root password on a fresh FE
and registers the BE. A full run (run when a data product is applied) also
creates the three shared Iceberg REST catalogs on Polaris as srv-starrocks, every
product's materialized-view databases, and the managed roles with exactly the
grants of the product files: database-scoped per product, catalog-wide for the
platform administrator (BR-3). --remove drops one product's roles and MV
databases (refused while they hold MVs or tables, unless --purge-data);
--inventory prints their counts. It refuses conflicting catalogs and never
prints SQL output, the root password, or the catalog secret.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent))
import starrocks_common as sr  # noqa: E402

BACKEND = ("starrocks-be", 9050)
CREDENTIAL_KEY = "iceberg.catalog.oauth2.credential"
SERVICE_CLIENT_ID = "srv-starrocks"
POLARIS_CATALOG_URI = "http://polaris:8181/api/catalog"
KEYCLOAK_TOKEN_URI = "http://keycloak:8080/realms/lakehouse/protocol/openid-connect/token"
SMOKE_TABLE = "bootstrap_smoke_test"
LDAP_BIND_DN_PATTERN = sr.LDAP_BIND_DN_PATTERN
ensure_ldap_login = sr.ensure_ldap_login


@dataclass(frozen=True, order=True)
class Grant:
    role: str
    privilege: str
    catalog: str
    object: str  # CATALOG | ALL DATABASES | ALL TABLES IN ALL DATABASES | DATABASE <db> | ALL TABLES IN DATABASE <db> | ALL MATERIALIZED VIEWS IN DATABASE <db>


@dataclass
class GrantPlan:
    add: list[Grant] = field(default_factory=list)
    revoke: list[Grant] = field(default_factory=list)


# ---- Catalog definitions (pure) ----

def catalog_definition(env: sr.Environment, secret: str) -> dict[str, str]:
    return {
        "type": "iceberg",
        "iceberg.catalog.type": "rest",
        "iceberg.catalog.uri": POLARIS_CATALOG_URI,
        "iceberg.catalog.warehouse": env.catalog,
        "iceberg.catalog.security": "oauth2",
        CREDENTIAL_KEY: f"{SERVICE_CLIENT_ID}:{secret}",
        "iceberg.catalog.oauth2.server-uri": KEYCLOAK_TOKEN_URI,
        "iceberg.catalog.oauth2.scope": "openid",
        "iceberg.catalog.oauth2.token-refresh-enabled": "true",
        "iceberg.catalog.vended-credentials-enabled": "true",
        "aws.s3.endpoint": "http://rustfs:9000",
        "aws.s3.enable_path_style_access": "true",
        "aws.s3.region": "us-east-1",
    }


def render_catalog_properties(properties: dict[str, str]) -> str:
    pairs = ",\n".join(f"  {sr.quote_literal(key)} = {sr.quote_literal(value)}" for key, value in properties.items())
    return f"PROPERTIES (\n{pairs}\n)"


_QUOTED = r"""('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")"""
_PAIR = re.compile(_QUOTED + r"\s*=\s*" + _QUOTED, re.S)
_UNESCAPE = {"\\\\": "\\", "\\'": "'", '\\"': '"', "\\n": "\n", "\\r": "\r", "\\t": "\t", "\\0": "\x00"}


def _unquote(text: str) -> str:
    return re.sub(r"\\.", lambda m: _UNESCAPE.get(m.group(0), m.group(0)[1]), text[1:-1])


def parse_catalog_properties(ddl: str) -> dict[str, str]:
    """Properties from a CREATE (EXTERNAL) CATALOG statement, as rendered or as SHOW CREATE prints it."""
    start = ddl.upper().find("PROPERTIES")
    if start < 0:
        return {}
    return {_unquote(key): _unquote(value) for key, value in _PAIR.findall(ddl[start:])}


def plan_catalog(existing: dict[str, str] | None, desired: dict[str, str]) -> Literal["create", "equal", "conflict"]:
    """Compare everything except the (masked) credential; extra keys StarRocks adds are ignored."""
    if existing is None:
        return "create"
    for key, value in desired.items():
        if key == CREDENTIAL_KEY:
            continue
        if existing.get(key) != value:
            return "conflict"
    return "equal"


# ---- Role grants (pure) ----

# StarRocks checks SELECT on an external catalog's information_schema tables, which SQL
# clients such as DBeaver query to list a database's tables; their rows are filtered by
# the user's own privileges, so the grant reveals nothing the role can't already see.
METADATA_DATABASE = "information_schema"


def _catalog_grants(role: str, catalog: str, level: str, database: str | None = None) -> set[Grant]:
    """BR-3: database-scoped grants for a product role; catalog-wide when database is None."""
    if level == "none":
        return set()
    if database is None:
        tables, databases = "ALL TABLES IN ALL DATABASES", "ALL DATABASES"
        if level == "manage":
            return {Grant(role, "ALL", catalog, obj) for obj in ("CATALOG", databases, tables)}
        grants = {Grant(role, "USAGE", catalog, "CATALOG"), Grant(role, "SELECT", catalog, tables)}
        if level == "write":
            grants |= {Grant(role, "INSERT", catalog, tables), Grant(role, "CREATE TABLE", catalog, databases)}
        return grants
    tables, db = f"ALL TABLES IN DATABASE {database}", f"DATABASE {database}"
    grants = {Grant(role, "USAGE", catalog, "CATALOG"), Grant(role, "SELECT", catalog, f"ALL TABLES IN DATABASE {METADATA_DATABASE}")}
    if level == "manage":
        return grants | {Grant(role, "ALL", catalog, db), Grant(role, "ALL", catalog, tables)}
    grants.add(Grant(role, "SELECT", catalog, tables))
    if level == "write":
        grants |= {Grant(role, "INSERT", catalog, tables), Grant(role, "CREATE TABLE", catalog, db)}
    return grants


def _mv_grants(role: str, database: str, level: str) -> set[Grant]:
    mvs, db = f"ALL MATERIALIZED VIEWS IN DATABASE {database}", f"DATABASE {database}"
    catalog = sr.INTERNAL_CATALOG
    if level == "none":
        return set()
    if level == "manage":
        return {Grant(role, "ALL", catalog, db), Grant(role, "ALL", catalog, mvs)}
    grants = {Grant(role, "SELECT", catalog, mvs)}
    if level == "author":
        grants |= {Grant(role, "CREATE MATERIALIZED VIEW", catalog, db)}
        grants |= {Grant(role, privilege, catalog, mvs) for privilege in ("ALTER", "REFRESH", "DROP")}
    return grants


def role_grants(model: sr.Model | None = None) -> set[Grant]:
    grants: set[Grant] = set()
    for scope in (model or sr.MODEL).scopes:
        grants |= _catalog_grants(scope.role, scope.catalog, scope.level, scope.database)
        if scope.mv_database:
            grants |= _mv_grants(scope.role, scope.mv_database, scope.mv_level)
    return grants


def _covered(grant: Grant, desired: set[Grant]) -> bool:
    return grant in desired or Grant(grant.role, "ALL", grant.catalog, grant.object) in desired


def plan_grants(current: set[Grant], desired: set[Grant], managed: tuple[str, ...] | None = None) -> GrantPlan:
    """Grant what is missing; revoke privileges on managed roles the files do not cover (SR-10, SR-11, BR-7)."""
    managed_roles = set(managed if managed is not None else sr.MANAGED_ROLES)
    return GrantPlan(
        add=sorted(desired - current),
        revoke=sorted(g for g in current if g.role in managed_roles and not _covered(g, desired)),
    )


_GRANT_STATEMENT = re.compile(r"^GRANT\s+(?P<privileges>.+?)\s+ON\s+(?P<object>.+?)\s+TO\s+ROLE\s+", re.I | re.S)


def _bare(name: str) -> str:
    return name.strip().strip("`'\"")


def parse_role_grants(role: str, rows: list[dict[str, str]]) -> tuple[set[Grant], list[str]]:
    """Grants from SHOW GRANTS FOR ROLE; returns (understood grants, unrecognised statements)."""
    grants: set[Grant] = set()
    unknown: list[str] = []
    for row in rows:
        statement = (row.get("Grants") or "").strip()
        match = _GRANT_STATEMENT.match(statement)
        if not match:
            if statement and not re.match(r"^GRANT\s+'[^']+'(\s*,\s*'[^']+')*\s+TO\s+ROLE", statement, re.I):
                unknown.append(statement)
            continue
        catalog = (row.get("Catalog") or "").strip()
        if catalog.upper() in ("", "NULL"):
            catalog = ""
        obj = re.sub(r"\s+", " ", match.group("object").strip())
        upper = obj.upper()
        if upper.startswith("CATALOG "):
            catalog, obj = _bare(obj[len("CATALOG "):]), "CATALOG"
        elif upper in ("ALL DATABASES", "ALL TABLES IN ALL DATABASES"):
            obj = upper
        elif upper.startswith("ALL TABLES IN DATABASE "):
            obj = "ALL TABLES IN DATABASE " + _bare(obj[len("ALL TABLES IN DATABASE "):])
        elif upper.startswith("ALL MATERIALIZED VIEWS IN DATABASE "):
            obj = "ALL MATERIALIZED VIEWS IN DATABASE " + _bare(obj[len("ALL MATERIALIZED VIEWS IN DATABASE "):])
        elif upper.startswith("DATABASE "):
            obj = "DATABASE " + _bare(obj[len("DATABASE "):])
        else:
            unknown.append(statement)
            continue
        for privilege in match.group("privileges").split(","):
            grants.add(Grant(role, re.sub(r"\s+", " ", privilege.strip().upper()), catalog, obj))
    return grants, unknown


def render_grant(grant: Grant, revoke: bool = False) -> str:
    verb, preposition = ("REVOKE", "FROM") if revoke else ("GRANT", "TO")
    role = sr.quote_identifier(grant.role)
    if grant.object == "CATALOG":
        return f"{verb} {grant.privilege} ON CATALOG {sr.quote_identifier(grant.catalog)} {preposition} ROLE {role};"
    obj = grant.object
    for prefix in ("ALL MATERIALIZED VIEWS IN DATABASE ", "ALL TABLES IN DATABASE ", "DATABASE "):
        if obj.startswith(prefix):
            obj = prefix + sr.quote_identifier(obj[len(prefix):])
            break
    return f"SET CATALOG {sr.quote_identifier(grant.catalog)};\n{verb} {grant.privilege} ON {obj} {preposition} ROLE {role};"


# ---- Runtime steps ----

def ensure_root_password(transport: str, password_file: Path, timeout_seconds: int) -> str:
    password = sr.read_secret(password_file)
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            sr.make_runner(transport, password).query("SELECT 1;", "root login")
            return "already-set"
        except sr.StarRocksError:
            pass
        try:
            fresh = sr.make_runner(transport, None)
            fresh.query("SELECT 1;", "fresh root login")
        except sr.StarRocksError:
            if time.monotonic() >= deadline:
                raise sr.StarRocksError(
                    "StarRocks root login failed with the protected password and with no password; "
                    "restore .runtime/credentials/starrocks-root-password or reset StarRocks."
                ) from None
            time.sleep(3)
            continue
        fresh.execute(f"ALTER USER 'root' IDENTIFIED BY {sr.quote_literal(password)};", "set root password")
        return "set"


def _backend_host(row: dict[str, str]) -> str:
    # 4.1 reports the registered host (FQDN here) in the IP column; older releases used Host.
    return row.get("IP") or row.get("Host") or ""


def ensure_backend(runner: sr.SqlRunner, timeout_seconds: int) -> str:
    host, port = BACKEND
    backends = runner.query("SHOW BACKENDS;", "list backends")
    outcome = "already-registered"
    if not any(_backend_host(row) == host for row in backends):
        runner.execute(f"ALTER SYSTEM ADD BACKEND {sr.quote_literal(f'{host}:{port}')};", "register backend")
        outcome = "registered"
    deadline = time.monotonic() + timeout_seconds
    while True:
        rows = runner.query("SHOW BACKENDS;", "check backend")
        if any(_backend_host(row) == host and row.get("Alive", "").lower() == "true" for row in rows):
            return outcome
        if time.monotonic() >= deadline:
            raise sr.StarRocksError("The StarRocks BE did not become alive in time.")
        time.sleep(3)


# ---- Product steps ----

def ensure_catalogs(runner: sr.SqlRunner, secret: str, recreate: bool, dry_run: bool) -> None:
    existing_names = {row.get("Catalog") for row in runner.query("SHOW CATALOGS;", "list catalogs")}
    plans: list[tuple[sr.Environment, str, dict[str, str]]] = []
    for env in sr.ENVIRONMENTS:
        desired = catalog_definition(env, secret)
        if recreate and env.catalog in existing_names:
            plans.append((env, "recreate", desired))
            continue
        current = None
        if env.catalog in existing_names:
            rows = runner.query(f"SHOW CREATE CATALOG {sr.quote_identifier(env.catalog)};", f"read catalog {env.catalog}")
            current = parse_catalog_properties(rows[0].get("Create Catalog", "") if rows else "")
        plans.append((env, plan_catalog(current, desired), desired))
    conflicts = [env.catalog for env, outcome, _ in plans if outcome == "conflict"]
    if conflicts:
        raise sr.StarRocksError(
            "Existing StarRocks catalog(s) differ from the contract: " + ", ".join(conflicts)
            + ". Review, then rerun with --recreate-catalogs."
        )
    for env, outcome, desired in plans:
        print(f"StarRocks catalog {env.catalog}: {outcome}{' (dry run)' if dry_run and outcome != 'equal' else ''}.")
        if dry_run or outcome == "equal":
            continue
        name = sr.quote_identifier(env.catalog)
        if outcome == "recreate":
            runner.execute(f"DROP CATALOG {name};", f"drop catalog {env.catalog}")
        runner.execute(
            f"CREATE EXTERNAL CATALOG {name}\n{render_catalog_properties(desired)};", f"create catalog {env.catalog}"
        )


def ensure_mv_databases(runner: sr.SqlRunner, dry_run: bool, model: sr.Model | None = None) -> None:
    databases = (model or sr.MODEL).mv_databases
    for database in databases:
        if not dry_run:
            runner.execute(
                f"CREATE DATABASE IF NOT EXISTS {sr.quote_identifier(sr.INTERNAL_CATALOG)}.{sr.quote_identifier(database)};",
                f"create MV database {database}",
            )
    print("StarRocks materialized-view databases: " + ", ".join(databases) + ".")


def ensure_roles(runner: sr.SqlRunner, dry_run: bool, model: sr.Model | None = None) -> None:
    model = model or sr.MODEL
    desired = role_grants(model)
    current: set[Grant] = set()
    unknown: list[str] = []
    existing = {row.get("Name") or row.get("RoleName") or "" for row in runner.query("SHOW ROLES;", "list roles")}
    for role in model.managed_roles:
        if role not in existing:
            if dry_run:
                print(f"StarRocks role {role}: would be created.")
                continue
            runner.execute(f"CREATE ROLE IF NOT EXISTS {sr.quote_identifier(role)};", f"create role {role}")
        rows = runner.query(f"SHOW GRANTS FOR ROLE {sr.quote_identifier(role)};", f"read grants of {role}")
        understood, unrecognised = parse_role_grants(role, rows)
        current |= understood
        unknown += [f"{role}" for _ in unrecognised]
    plan = plan_grants(current, desired, model.managed_roles)
    if not dry_run:
        # Additions first, then revocations (BR-7).
        for grant in plan.add:
            runner.execute(render_grant(grant), f"grant to {grant.role}")
        for grant in plan.revoke:
            runner.execute(render_grant(grant, revoke=True), f"revoke from {grant.role}")
    for grant in plan.revoke:
        print(f"StarRocks role {grant.role}: {'would revoke' if dry_run else 'revoked'} {grant.privilege} on {grant.object} in {grant.catalog or 'system'}.")
    for role in sorted(set(unknown)):
        print(f"WARNING: StarRocks role {role} has a grant this bootstrap does not recognise; review it manually.")
    print(f"StarRocks roles: {len(model.managed_roles)} managed; {len(plan.add)} grant(s) applied, {len(plan.revoke)} revoked"
          f"{' (dry run)' if dry_run else ''}.")


def mv_inventory(runner: sr.SqlRunner, product) -> dict[str, int]:
    """Tables and MVs per environment in the product's MV databases (0 for a missing database)."""
    present = {row.get("Database") for row in runner.query(f"SHOW DATABASES FROM {sr.quote_identifier(sr.INTERNAL_CATALOG)};", "list MV databases")}
    counts = {}
    for env in product.environments:
        if env.mv_database not in present:
            counts[env.key] = 0
            continue
        rows = runner.query(
            f"SHOW TABLES FROM {sr.quote_identifier(sr.INTERNAL_CATALOG)}.{sr.quote_identifier(env.mv_database)};",
            f"list {env.mv_database}",
        )
        counts[env.key] = len(rows)
    return counts


def remove_product(runner: sr.SqlRunner, product, remaining: list, purge: bool, dry_run: bool) -> None:
    counts = mv_inventory(runner, product)
    if any(counts.values()) and not purge:
        raise sr.StarRocksError(f"MV databases of {product.name} still hold tables or MVs {counts}; rerun with --purge-data.")
    prefix = "would " if dry_run else ""
    for env in product.environments:
        if counts.get(env.key) is None:
            continue
        print(f"StarRocks MV database {env.mv_database}: {prefix}drop.")
        if not dry_run:
            runner.execute(
                f"DROP DATABASE IF EXISTS {sr.quote_identifier(sr.INTERNAL_CATALOG)}.{sr.quote_identifier(env.mv_database)} FORCE;",
                f"drop MV database {env.mv_database}",
            )
    existing = {row.get("Name") or row.get("RoleName") or "" for row in runner.query("SHOW ROLES;", "list roles")}
    for group in product.group_names():
        role = sr.data_products.starrocks_role(group)
        if role in existing:
            print(f"StarRocks role {role}: {prefix}drop.")
            if not dry_run:
                runner.execute(f"DROP ROLE {sr.quote_identifier(role)};", f"drop role {role}")
    # The platform administrator's grants on the dropped MV databases are revoked here.
    ensure_roles(runner, dry_run, sr.build_model(remaining))


def smoke_check(runner: sr.SqlRunner) -> None:
    for env in sr.ENVIRONMENTS:
        table = ".".join(sr.quote_identifier(part) for part in (env.catalog, env.namespace, SMOKE_TABLE))
        rows = runner.query(f"SELECT count(*) AS n FROM {table};", f"read {env.catalog} smoke table")
        count = rows[0].get("n", "?") if rows else "?"
        print(f"StarRocks read {env.catalog}.{env.namespace}.{SMOKE_TABLE}: {count} row(s).")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-only", action="store_true", help="only set the root password and register the BE")
    parser.add_argument("--recreate-catalogs", action="store_true", help="drop and recreate the three catalogs (secret rotation or repair)")
    parser.add_argument("--dry-run", action="store_true", help="read state and print the plan without changing StarRocks")
    parser.add_argument("--skip-smoke", action="store_true", help="skip reading the Polaris smoke tables")
    parser.add_argument("--product", type=Path, action="append", default=[], help="product file (validated; roles always follow every file)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--remove", action="store_true", help="drop one product's roles and MV databases")
    mode.add_argument("--inventory", action="store_true", help="print one product's MV database table counts as JSON")
    parser.add_argument("--purge-data", action="store_true", help="with --remove: drop MV databases that still hold objects")
    parser.add_argument("--transport", choices=("docker", "network"), default="docker")
    parser.add_argument("--root-password-file", type=Path, default=sr.CREDENTIALS / "starrocks-root-password")
    parser.add_argument("--catalog-secret-file", type=Path, default=sr.CREDENTIALS / "srv-starrocks-client-secret")
    args = parser.parse_args(argv)
    if (args.remove or args.inventory) and len(args.product) != 1:
        parser.error("--remove and --inventory need exactly one --product")
    if not sr.starrocks_enabled():
        print("NOTICE: StarRocks is disabled (STARROCKS_ENABLED=false); skipping the StarRocks bootstrap.")
        return 0
    timeout = int(os.environ.get("STARTUP_TIMEOUT_SECONDS", "600"))
    try:
        if not args.runtime_only:
            sr.require_products()
            selected, every = sr.data_products.resolve_products(args.product, removal=args.remove or args.inventory)
            if args.remove and selected[0].protected:
                raise sr.data_products.ProductError("The default data product cannot be removed.")
        if args.dry_run or args.remove or args.inventory:
            runner = sr.root_runner(args.transport, args.root_password_file)
        else:
            print(f"StarRocks root password: {ensure_root_password(args.transport, args.root_password_file, timeout)}.")
            runner = sr.root_runner(args.transport, args.root_password_file)
            print(f"StarRocks backend: {ensure_backend(runner, timeout)}.")
            print(f"StarRocks LDAP password login: {ensure_ldap_login(runner)}.")
        if args.runtime_only:
            return 0
        if args.inventory:
            print(json.dumps(mv_inventory(runner, selected[0]), sort_keys=True))
            return 0
        if args.remove:
            remove_product(runner, selected[0], sr.data_products.remaining_products(every, selected[0]), args.purge_data, args.dry_run)
        else:
            ensure_catalogs(runner, sr.read_secret(args.catalog_secret_file), args.recreate_catalogs, args.dry_run)
            ensure_mv_databases(runner, args.dry_run)
            ensure_roles(runner, args.dry_run)
            if not args.dry_run and not args.skip_smoke:
                smoke_check(runner)
    except sr.data_products.ProductError as error:
        print(f"ERROR: StarRocks bootstrap refused: {error}", file=sys.stderr)
        return 2
    except sr.StarRocksError as error:
        print(f"ERROR: StarRocks bootstrap failed: {error}", file=sys.stderr)
        return 1
    print("StarRocks bootstrap completed." if not args.dry_run else "StarRocks dry run completed; nothing was changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
