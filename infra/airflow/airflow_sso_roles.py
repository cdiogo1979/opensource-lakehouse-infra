"""Airflow SSO group authorization helpers.

Group -> Airflow role comes from the data product files (apps.airflow), read at
every sign-in, so a new product needs no restart (BR-6). An unreadable or
invalid product file fails closed: only the platform administrator signs in.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterable
from pathlib import Path

AIRFLOW_ROLE_ORDER = ("Admin", "User", "Viewer")
PLATFORM_ADMIN_GROUP = "role-platform-admin"
LOG = logging.getLogger("lakehouse.airflow_sso")


def _data_products():
    """The product model, mounted next to this module in the API server only.

    Other Airflow services load this module through webserver_config but never
    sign users in, so the import is deferred; in the repository the model lives
    in infra/products.
    """
    try:
        import data_products
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "products"))
        import data_products
    return data_products


def group_role_mapping() -> dict[str, str]:
    try:
        products = _data_products()
        return products.airflow_group_roles(products.load_all())
    except Exception as error:  # an unusable model or file fails closed
        LOG.error("Data product files are unusable; only the platform administrator may sign in: %s", error)
        return {PLATFORM_ADMIN_GROUP: "Admin"}


def approved_groups(groups: object, mapping: dict[str, str] | None = None) -> list[str]:
    if isinstance(groups, (str, bytes, dict)) or not isinstance(groups, Iterable):
        return []
    mapping = group_role_mapping() if mapping is None else mapping
    return [group for group in mapping if group in groups]


def roles_for_groups(groups: object) -> list[str]:
    mapping = group_role_mapping()
    matched_groups = approved_groups(groups, mapping)
    return [
        role
        for role in AIRFLOW_ROLE_ORDER
        if any(mapping[group] == role for group in matched_groups)
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
