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
        # Only the platform administrator is Airflow Admin; owners and developers are User.
        self.assertEqual(roles.roles_for_groups(["role-default-owner"]), ["User"])
        self.assertEqual(roles.roles_for_groups(["role-default-developer"]), ["User"])
        self.assertEqual(roles.roles_for_groups(["role-default-analyst"]), ["User"])
        self.assertEqual(roles.roles_for_groups(["role-default-writer"]), ["Viewer"])
        self.assertEqual(roles.roles_for_groups(["role-platform-admin"]), ["Admin"])

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
        self.assertEqual(roles.roles_for_groups(groups), ["User", "Viewer"])
        self.assertEqual(roles.roles_for_groups([*groups, "role-platform-admin"]), ["Admin", "User", "Viewer"])

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
        # Groups become Airflow role names at sign-in from the data product files.
        self.assertIn('AUTH_ROLES_MAPPING = {role: [role] for role in ("Admin", "User", "Viewer")}', config)
        self.assertNotIn("role-default-", config)
        manager = (ROOT / "infra/airflow/airflow_oauth_security_manager.py").read_text(encoding="utf-8")
        self.assertIn('userinfo["role_keys"] = roles_for_groups(userinfo["role_keys"])', manager)
        compose = (ROOT / "compose.airflow.yml").read_text(encoding="utf-8")
        self.assertIn("- ./data-products:/opt/airflow/data-products:ro", compose)
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


class AirflowProductMappingTests(unittest.TestCase):
    """Every product file's apps.airflow is read at sign-in (BR-6)."""

    def test_a_new_product_maps_without_a_restart_and_bad_files_fail_closed(self):
        import tempfile

        dp = roles._data_products()
        original = dp.PRODUCTS_DIR
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("default", "sales"):
                (root / f"{name}.yaml").write_text(dp.render_template(name), encoding="utf-8")
            dp.PRODUCTS_DIR = root
            try:
                self.assertEqual(roles.roles_for_groups(["role-sales-writer"]), ["Viewer"])
                self.assertEqual(roles.roles_for_groups(["role-sales-owner", "role-default-writer"]), ["User", "Viewer"])
                (root / "broken.yaml").write_text("name: [", encoding="utf-8")
                self.assertEqual(roles.roles_for_groups(["role-sales-owner"]), [])
                self.assertEqual(roles.roles_for_groups(["role-platform-admin"]), ["Admin"])
            finally:
                dp.PRODUCTS_DIR = original


class AirflowImportTests(unittest.TestCase):
    def test_module_loads_without_the_product_model(self):
        # Build and Test finding: airflow-init loads this module without the mount.
        source = (ROOT / "infra/airflow/airflow_sso_roles.py").read_text(encoding="utf-8")
        module_level = source.split("def _data_products", 1)[0]
        self.assertNotIn("import data_products", module_level)
