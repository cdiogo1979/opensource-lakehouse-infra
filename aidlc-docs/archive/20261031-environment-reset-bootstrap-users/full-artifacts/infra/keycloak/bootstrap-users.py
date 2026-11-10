#!/usr/bin/env python3
"""Reset the bootstrap users to their default password and exactly their default group.

Unlike the create-only realm bootstrap, every run re-applies the defaults from
bootstrap-users.json. Users outside that file are never touched. Passwords are
never printed.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import uuid
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("bootstrap_realm", Path(__file__).with_name("bootstrap-realm.py"))
realm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(realm)
REALM = realm.REALM


def plan_user_changes(exists: bool, current_groups: set[str], desired_group: str) -> dict:
    """Decide how to bring one bootstrap user to its defaults.

    Args:
        exists: Whether the user already exists in the realm.
        current_groups: Names of the user's current realm groups.
        desired_group: The user's single default group.

    Returns:
        A plan with keys create, update_profile, reset_password, remove_groups, and add_group.
    """
    if not exists:
        return {"create": True, "update_profile": False, "reset_password": False,
                "remove_groups": set(), "add_group": True}
    return {"create": False, "update_profile": True, "reset_password": True,
            "remove_groups": set(current_groups) - {desired_group},
            "add_group": desired_group not in current_groups}


def user_groups(api, user_id: str) -> dict[str, str]:
    status, memberships = api.request("GET", f"/admin/realms/{REALM}/users/{user_id}/groups")
    realm.checked(status, (200,), "User group lookup")
    return {item["name"]: item["id"] for item in memberships or []}


def apply_user(api, user: dict, groups: dict[str, dict], password: str, email_domain: str) -> dict:
    current = realm.find_user(api, user["username"])
    current_groups = user_groups(api, current["id"]) if current else {}
    plan = plan_user_changes(current is not None, set(current_groups), user["group"])
    if plan["create"]:
        current = realm.create_missing_bootstrap_user(api, user, password, email_domain)
    if plan["update_profile"]:
        profile = realm.bootstrap_user_representation(user, password, email_domain)
        profile.pop("credentials")
        status, _ = api.request("PUT", f"/admin/realms/{REALM}/users/{current['id']}", {**current, **profile})
        realm.checked(status, (204,), f"Update bootstrap user {user['username']}")
    if plan["reset_password"]:
        status, _ = api.request("PUT", f"/admin/realms/{REALM}/users/{current['id']}/reset-password",
                                {"type": "password", "value": password, "temporary": False})
        realm.checked(status, (204,), f"Reset password for {user['username']}")
    for name in sorted(plan["remove_groups"]):
        status, _ = api.request("DELETE", f"/admin/realms/{REALM}/users/{current['id']}/groups/{current_groups[name]}")
        realm.checked(status, (204,), f"Remove {user['username']} from {name}")
    if plan["add_group"]:
        realm.add_user_to_group(api, current["id"], groups[user["group"]])
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-password-file", type=Path, default=Path(".runtime/credentials/keycloak-admin-password"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    args = parser.parse_args()
    operation_id = str(uuid.uuid4())
    try:
        identities = realm.load_bootstrap_identities()
        api = realm.KeycloakAdmin(args.base_url, os.environ.get("KEYCLOAK_ADMIN_USERNAME", "admin"),
                                  realm.read_secret(args.admin_password_file))
        api.login()
        groups = {}
        for name in identities["groups"]:
            group = realm.find_group(api, name)
            if not group:
                raise realm.BootstrapError(f"Group {name!r} is missing; run infra/keycloak/bootstrap-realm.py first.")
            groups[name] = group
        for user in identities["users"]:
            plan = apply_user(api, user, groups, identities["default_password"], identities["email_domain"])
            action = "created" if plan["create"] else "reset"
            removed = f"; removed from {len(plan['remove_groups'])} other group(s)" if plan["remove_groups"] else ""
            print(f"Bootstrap user {user['username']}: {action}; group {user['group']}{removed}.")
        print(f"Bootstrap users match their defaults (operation_id={operation_id}; users={len(identities['users'])}).")
        return 0
    except realm.BootstrapError as error:
        print(f"Bootstrap user reset failed (operation_id={operation_id}): {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
