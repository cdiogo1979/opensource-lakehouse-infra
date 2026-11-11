#!/usr/bin/env python3
"""Synchronize StarRocks LDAP-login users and role grants with Keycloak product groups.

Every Keycloak user in a product group gets a StarRocks user that logs in with
its own username and LDAP password (`authentication_ldap_simple`, over TLS),
holding exactly the managed roles of its groups as default roles. Platform admins
also get the built-in admin roles. Users of the former token login (JWT) are
switched in place, keeping their grants and objects. Managed users who left every
product group are dropped. Root, built-in users, and native-password users are
never changed. If Keycloak cannot be read, or returns no product-group members,
nothing is applied.

With --bind-pattern-only it only re-applies the LDAP bind pattern that an FE
restart resets, so password logins recover even while the user sync is refused.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import starrocks_common as sr  # noqa: E402

REALM = "lakehouse"
# Users log in with their LDAP password (the FE binds as uid=<user>,ou=people);
# JWT users from the former token login are switched in place.
LDAP_PLUGIN = "AUTHENTICATION_LDAP_SIMPLE"
JWT_PLUGIN = "AUTHENTICATION_JWT"
MANAGED_PLUGINS = frozenset({LDAP_PLUGIN, JWT_PLUGIN})
GRANTABLE_ROLES = frozenset(sr.MANAGED_ROLES) | frozenset(sr.PLATFORM_ADMIN_BUILTINS)


@dataclass(frozen=True)
class UserState:
    name: str
    plugin: str
    roles: frozenset[str]


@dataclass
class UserPlan:
    create: list[tuple[str, frozenset[str]]] = field(default_factory=list)
    grant: list[tuple[str, str]] = field(default_factory=list)
    revoke: list[tuple[str, str]] = field(default_factory=list)
    defaults: list[str] = field(default_factory=list)
    drop: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    switch: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.create or self.switch or self.grant or self.revoke or self.defaults or self.drop)


# ---- Pure planning ----

def desired_users(memberships: dict[str, set[str]]) -> dict[str, frozenset[str]]:
    """Keycloak username -> StarRocks roles, for users in at least one product group (SR-13, SR-14)."""
    desired: dict[str, frozenset[str]] = {}
    for username, groups in memberships.items():
        if username.startswith(sr.SERVICE_ACCOUNT_PREFIX):
            continue
        roles = {sr.GROUP_ROLES[group] for group in groups if group in sr.GROUP_ROLES}
        if not roles:
            continue
        if sr.PLATFORM_ADMIN_GROUP in groups:
            roles |= set(sr.PLATFORM_ADMIN_BUILTINS)
        desired[username] = frozenset(roles)
    return desired


def plan_users(current: dict[str, UserState], desired: dict[str, frozenset[str]]) -> UserPlan:
    """Changes that make managed (LDAP, or former JWT) users match the desired users (SR-14, SR-16, BR-3)."""
    plan = UserPlan()
    for name in sorted(desired):
        roles = desired[name]
        state = current.get(name)
        if state is None:
            plan.create.append((name, roles))
            plan.grant += [(name, role) for role in sorted(roles)]
            plan.defaults.append(name)
            continue
        if state.plugin not in MANAGED_PLUGINS:
            plan.conflicts.append(name)
            continue
        if state.plugin == JWT_PLUGIN:
            plan.switch.append(name)
        missing = sorted(roles - state.roles)
        extra = sorted((state.roles & GRANTABLE_ROLES) - roles)
        plan.grant += [(name, role) for role in missing]
        plan.revoke += [(name, role) for role in extra]
        if missing or extra:
            plan.defaults.append(name)
    plan.drop = sorted(name for name, state in current.items() if state.plugin in MANAGED_PLUGINS and name not in desired)
    return plan


def render_plan(plan: UserPlan) -> list[tuple[str, str]]:
    """(SQL, operation) in apply order: create, switch, grant, revoke, default roles, drop."""
    statements: list[tuple[str, str]] = []
    for name, _roles in plan.create:
        statements.append((f"CREATE USER IF NOT EXISTS {sr.user_identity(name)} IDENTIFIED WITH authentication_ldap_simple;", f"create user {name}"))
    for name in plan.switch:
        # ALTER keeps the user's grants and the objects it owns (materialized views).
        statements.append((f"ALTER USER {sr.user_identity(name)} IDENTIFIED WITH authentication_ldap_simple;", f"switch {name} to LDAP login"))
    for name, role in plan.grant:
        statements.append((f"GRANT {sr.quote_identifier(role)} TO USER {sr.user_identity(name)};", f"grant {role} to {name}"))
    for name, role in plan.revoke:
        statements.append((f"REVOKE {sr.quote_identifier(role)} FROM USER {sr.user_identity(name)};", f"revoke {role} from {name}"))
    for name in plan.defaults:
        statements.append((f"SET DEFAULT ROLE ALL TO {sr.user_identity(name)};", f"default roles of {name}"))
    for name in plan.drop:
        statements.append((f"DROP USER {sr.user_identity(name)};", f"drop user {name}"))
    return statements


# ---- Keycloak ----

class KeycloakError(Exception):
    pass


def _http(url: str, token: str | None = None, data: bytes | None = None) -> object:
    request = urllib.request.Request(url, data=data, headers={"Authorization": f"Bearer {token}"} if token else {})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise KeycloakError("Keycloak request failed") from error


# Product groups that are gone from Keycloak (a product being removed); their roles
# are no longer required to exist.
MISSING_GROUPS: set[str] = set()


def read_keycloak_memberships(base_url: str, admin_password: str) -> dict[str, set[str]]:
    form = urllib.parse.urlencode({"grant_type": "password", "client_id": "admin-cli", "username": "admin", "password": admin_password}).encode()
    token = _http(f"{base_url}/realms/master/protocol/openid-connect/token", data=form).get("access_token")  # type: ignore[union-attr]
    if not token:
        raise KeycloakError("Keycloak admin login failed")
    memberships: dict[str, set[str]] = {}
    for group in sr.GROUP_ROLES:
        found = _http(f"{base_url}/admin/realms/{REALM}/groups?" + urllib.parse.urlencode({"search": group, "exact": "true"}), token)
        matches = [item for item in found or [] if item.get("name") == group]  # type: ignore[union-attr]
        if not matches and group != sr.PLATFORM_ADMIN_GROUP:
            # A product being removed: its groups are gone, so its members lose its roles.
            print(f"Keycloak group {group} is missing; treating it as empty.")
            MISSING_GROUPS.add(group)
            continue
        if len(matches) != 1:
            raise KeycloakError(f"Keycloak group {group} not found")
        first = 0
        while True:
            page = _http(f"{base_url}/admin/realms/{REALM}/groups/{matches[0]['id']}/members?first={first}&max=500", token)
            for user in page or []:  # type: ignore[union-attr]
                if user.get("username") and user.get("enabled", True):
                    memberships.setdefault(user["username"], set()).add(group)
            if len(page or []) < 500:  # type: ignore[arg-type]
                break
            first += 500
    return memberships


# ---- StarRocks ----

def _identity_name(text: str) -> str:
    # 'name'@'%' -> name
    return text.split("@", 1)[0].strip().strip("'`\"")


def read_starrocks_users(runner: sr.SqlRunner) -> dict[str, UserState]:
    rows = runner.query("SHOW ALL AUTHENTICATION;", "list users")
    users: dict[str, UserState] = {}
    for row in rows:
        name = _identity_name(row.get("UserIdentity", ""))
        plugin = (row.get("AuthPlugin") or "").strip().upper()
        if not name or name == "root":
            continue
        roles: frozenset[str] = frozenset()
        if plugin in MANAGED_PLUGINS:
            grants = runner.query(f"SHOW GRANTS FOR {sr.user_identity(name)};", f"read grants of {name}")
            roles = frozenset(role for grant in grants for role in parse_user_roles(grant.get("Grants", "")))
        users[name] = UserState(name, plugin, roles)
    return users


def missing_managed_roles(runner: sr.SqlRunner) -> list[str]:
    rows = runner.query("SHOW ROLES;", "list roles")
    present = {row.get("Name") or row.get("RoleName") or "" for row in rows}
    retired = {sr.GROUP_ROLES[group] for group in MISSING_GROUPS}
    return [role for role in sr.MANAGED_ROLES if role not in present and role not in retired]


_ROLE_GRANT = re.compile(r"^GRANT\s+((?:'[^']+'\s*,\s*)*'[^']+')\s+TO\s+(?:USER\s+)?'", re.I)


def parse_user_roles(statement: str) -> set[str]:
    """Role names from a role-grant line such as GRANT 'r1', 'r2' TO 'user'@'%'; privilege grants yield nothing."""
    match = _ROLE_GRANT.match(statement.strip())
    return set(re.findall(r"'([^']+)'", match.group(1))) if match else set()


def ensure_bind_pattern(transport: str, root_password_file: Path, dry_run: bool = False) -> int:
    """Re-apply the LDAP bind pattern if the FE lost it; needs no Keycloak and no product files."""
    try:
        runner = sr.root_runner(transport, root_password_file)
        if dry_run:
            rows = runner.query("ADMIN SHOW FRONTEND CONFIG LIKE 'authentication_ldap_simple_bind_dn_pattern';", "read LDAP bind pattern")
            state = "already-set" if rows and rows[0].get("Value") == sr.LDAP_BIND_DN_PATTERN else "would be set"
        else:
            state = sr.ensure_ldap_login(runner)
    except sr.StarRocksError as error:
        print(f"ERROR: StarRocks LDAP bind pattern check failed: {error}", file=sys.stderr)
        return 1
    if state == "set":
        print("StarRocks LDAP bind pattern was missing (FE restart) and is set again.")
    else:
        print(f"StarRocks LDAP bind pattern: {state}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=("docker", "network"), default="docker")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keycloak-url", default="http://127.0.0.1:8080")
    parser.add_argument("--keycloak-admin-password-file", type=Path, default=sr.CREDENTIALS / "keycloak-admin-password")
    parser.add_argument("--root-password-file", type=Path, default=sr.CREDENTIALS / "starrocks-root-password")
    parser.add_argument("--bind-pattern-only", action="store_true", help="only re-apply the LDAP bind pattern after an FE restart")
    args = parser.parse_args(argv)
    if not sr.starrocks_enabled():
        print("NOTICE: StarRocks is disabled (STARROCKS_ENABLED=false); skipping the StarRocks user reconcile.")
        return 0
    if args.bind_pattern_only:
        return ensure_bind_pattern(args.transport, args.root_password_file, args.dry_run)
    try:
        sr.require_products()
    except sr.StarRocksError as error:
        print(f"ERROR: StarRocks user reconcile refused: {error}", file=sys.stderr)
        return 1
    try:
        memberships = read_keycloak_memberships(args.keycloak_url, sr.read_secret(args.keycloak_admin_password_file))
    except (KeycloakError, sr.StarRocksError) as error:
        print(f"ERROR: StarRocks user reconcile aborted, nothing changed: {error}.", file=sys.stderr)
        return 1
    desired = desired_users(memberships)
    if not desired:
        print("ERROR: Keycloak returned no product-group members; refusing to change StarRocks users.", file=sys.stderr)
        return 1
    try:
        runner = sr.root_runner(args.transport, args.root_password_file)
        missing = missing_managed_roles(runner)
        if missing:
            # The scheduled reconciler can run before the product bootstrap creates
            # the roles; creating users then would leave them without grants.
            print("ERROR: StarRocks roles are not bootstrapped yet (" + ", ".join(missing)
                  + "); run infra/starrocks/bootstrap-starrocks.py first. Nothing changed.", file=sys.stderr)
            return 1
        if not args.dry_run and sr.ensure_ldap_login(runner) == "set":
            print("StarRocks LDAP bind pattern was missing (FE restart) and is set again.")
        plan = plan_users(read_starrocks_users(runner), desired)
        if not args.dry_run:
            for sql, operation in render_plan(plan):
                runner.execute(sql, operation)
    except sr.StarRocksError as error:
        print(f"ERROR: StarRocks user reconcile failed: {error}", file=sys.stderr)
        return 1
    for name in plan.conflicts:
        print(f"WARNING: StarRocks user {name} exists without JWT authentication; left unchanged.")
    suffix = " (dry run; nothing changed)" if args.dry_run else ""
    print(
        f"StarRocks users reconciled{suffix}: {len(desired)} desired; created {[n for n, _ in plan.create]}; switched to LDAP {plan.switch}; "
        f"{len(plan.grant)} grant(s), {len(plan.revoke)} revoke(s); dropped {plan.drop}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
