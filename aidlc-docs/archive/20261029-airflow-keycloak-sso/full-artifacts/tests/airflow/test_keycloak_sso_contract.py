"""Contract tests for Airflow's Keycloak authorization behavior."""

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "airflow_sso_roles", ROOT / "infra/airflow/airflow_sso_roles.py"
)
roles = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(roles)


class AirflowSsoContractTests(unittest.TestCase):
    def test_approved_groups_map_to_exact_airflow_roles(self):
        self.assertEqual(roles.roles_for_groups(["role-default-owner"]), ["Admin"])
        self.assertEqual(roles.roles_for_groups(["role-default-developer"]), ["Admin"])
        self.assertEqual(roles.roles_for_groups(["role-default-analyst"]), ["User"])
        self.assertEqual(roles.roles_for_groups(["role-default-writer"]), ["Viewer"])

    def test_multiple_approved_groups_assign_every_distinct_role(self):
        groups = [
            "role-default-writer",
            "role-default-analyst",
            "role-default-owner",
            "role-default-developer",
            "unapproved",
        ]
        self.assertEqual(roles.approved_groups(groups), [
            "role-default-owner",
            "role-default-developer",
            "role-default-analyst",
            "role-default-writer",
        ])
        self.assertEqual(roles.roles_for_groups(groups), ["Admin", "User", "Viewer"])

    def test_missing_unknown_and_malformed_group_claims_are_denied(self):
        for groups in (None, [], ["unapproved"], "role-default-owner", {"unexpected": True}):
            with self.subTest(groups=groups):
                self.assertEqual(roles.roles_for_groups(groups), [])
                self.assertFalse(
                    roles.can_oauth_login(
                        {"username": "alice", "role_keys": groups}, "admin"
                    )
                )

    def test_local_admin_username_cannot_be_replaced_by_oauth_identity(self):
        self.assertFalse(
            roles.can_oauth_login(
                {
                    "username": "admin",
                    "role_keys": ["role-default-owner"],
                },
                "admin",
            )
        )
        self.assertTrue(
            roles.can_oauth_login(
                {
                    "username": "alice",
                    "role_keys": ["role-default-owner"],
                },
                "admin",
            )
        )

    def test_fab_configuration_is_scoped_to_approved_groups_and_secret_file(self):
        config = (ROOT / "infra/airflow/webserver_config.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('AUTH_USER_REGISTRATION_ROLE = "Public"', config)
        self.assertIn("AUTH_ROLES_SYNC_AT_LOGIN = True", config)
        self.assertIn('"role-default-owner": ["Admin"]', config)
        self.assertIn('"role-default-developer": ["Admin"]', config)
        self.assertIn('"role-default-analyst": ["User"]', config)
        self.assertIn('"role-default-writer": ["Viewer"]', config)
        self.assertIn("sys.path.insert(0, CONFIG_DIR)", config)
        self.assertIn('Path(\n    "/run/secrets/keycloak_airflow_client_secret"', config)
        self.assertIn(
            '"authorize_url": "http://keycloak.localhost:8080/realms/lakehouse/protocol/openid-connect/auth"',
            config,
        )
        self.assertIn(
            '"issuer": "http://keycloak.localhost:8080/realms/lakehouse"',
            config,
        )
        self.assertIn(
            '"jwks_uri": "http://keycloak:8080/realms/lakehouse/protocol/openid-connect/certs"',
            config,
        )
        self.assertIn('"id_token_signing_alg_values_supported": ["RS256"]', config)
        self.assertNotIn('"server_metadata_url":', config)
        self.assertIn(
            '"access_token_url": "http://keycloak:8080/realms/lakehouse/protocol/openid-connect/token"',
            config,
        )
        self.assertNotIn("client_secret\": \"", config)

    def test_local_password_route_is_separate_and_admin_restricted(self):
        views = (ROOT / "infra/airflow/airflow_auth_views.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('@expose("/local-login/", methods=["GET", "POST"])', views)
        self.assertIn('os.environ.get("AIRFLOW_ADMIN_USERNAME", "admin")', views)
        self.assertIn("if form.username.data == local_admin_username:", views)
        self.assertIn("self.appbuilder.sm.auth_user_db(", views)


if __name__ == "__main__":
    unittest.main()
