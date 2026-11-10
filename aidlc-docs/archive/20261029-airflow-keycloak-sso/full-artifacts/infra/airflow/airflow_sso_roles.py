"""Dependency-free Airflow SSO group authorization helpers."""

from __future__ import annotations

from collections.abc import Iterable


GROUP_ROLE_MAPPING = {
    "role-default-owner": "Admin",
    "role-default-developer": "Admin",
    "role-default-analyst": "User",
    "role-default-writer": "Viewer",
}
AIRFLOW_ROLE_ORDER = ("Admin", "User", "Viewer")


def approved_groups(groups: object) -> list[str]:
    if isinstance(groups, (str, bytes, dict)) or not isinstance(groups, Iterable):
        return []
    return [group for group in GROUP_ROLE_MAPPING if group in groups]


def roles_for_groups(groups: object) -> list[str]:
    matched_groups = approved_groups(groups)
    return [
        role
        for role in AIRFLOW_ROLE_ORDER
        if any(GROUP_ROLE_MAPPING[group] == role for group in matched_groups)
    ]


def can_oauth_login(userinfo: object, local_admin_username: str) -> bool:
    if not isinstance(userinfo, dict):
        return False
    username = userinfo.get("username")
    return (
        isinstance(username, str)
        and bool(username)
        and username != local_admin_username
        and bool(
            roles_for_groups(userinfo.get("role_keys"))
        )
    )
