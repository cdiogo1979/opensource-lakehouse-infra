"""FAB security manager enforcing the approved Keycloak group contract."""

from __future__ import annotations

import os

from airflow.providers.fab.auth_manager.security_manager.override import (
    FabAirflowSecurityManagerOverride,
)

from airflow_sso_roles import can_oauth_login, roles_for_groups
from airflow_auth_views import LakehouseAuthOAuthView


class LakehouseSecurityManager(FabAirflowSecurityManagerOverride):
    authoauthview = LakehouseAuthOAuthView

    def get_oauth_user_info(self, provider: str, response: dict) -> dict:
        if provider != "keycloak":
            raise ValueError(f"Unsupported OAuth provider: {provider}")
        userinfo_response = self.oauth_remotes[provider].get("userinfo")
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()
        if not isinstance(userinfo, dict):
            return {}
        groups = userinfo.get("groups", [])
        return {
            "username": userinfo.get("preferred_username"),
            "first_name": userinfo.get("given_name", ""),
            "last_name": userinfo.get("family_name", ""),
            "email": userinfo.get("email", ""),
            "role_keys": groups if isinstance(groups, list) else [],
        }

    def auth_user_oauth(self, userinfo: dict):
        local_admin_username = os.environ.get("AIRFLOW_ADMIN_USERNAME", "admin")
        if not can_oauth_login(userinfo, local_admin_username):
            return None
        # Role keys become Airflow role names here, from the product files at
        # sign-in; AUTH_ROLES_MAPPING is then a fixed identity map.
        userinfo["role_keys"] = roles_for_groups(userinfo["role_keys"])
        return super().auth_user_oauth(userinfo)
