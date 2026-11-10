"""Contract tests for the confidential JupyterHub Keycloak client."""

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "keycloak_bootstrap", ROOT / "infra/keycloak/bootstrap-realm.py"
)
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


class JupyterHubClientContractTests(unittest.TestCase):
    def test_confidential_authorization_code_client_uses_exact_callback(self):
        client = bootstrap.jupyterhub_client_configuration("test-secret")
        self.assertEqual(client["clientId"], "jupyterhub")
        self.assertFalse(client["publicClient"])
        self.assertTrue(client["standardFlowEnabled"])
        self.assertFalse(client["directAccessGrantsEnabled"])
        self.assertFalse(client["serviceAccountsEnabled"])
        self.assertEqual(client["attributes"]["pkce.code.challenge.method"], "S256")
        self.assertEqual(
            client["redirectUris"],
            ["http://jupyterhub.localhost:8000/hub/oauth_callback"],
        )

    def test_group_mapper_is_explicitly_access_token_and_userinfo_only(self):
        class FakeAPI:
            def __init__(self):
                self.created = None

            def request(self, method, path, payload=None, *, query=None):
                if method == "GET":
                    return 200, []
                self.created = payload
                return 201, None

        api = FakeAPI()
        bootstrap.ensure_jupyterhub_group_mapper(api, "client-id")
        config = api.created["config"]
        self.assertEqual(api.created["protocolMapper"], "oidc-group-membership-mapper")
        self.assertEqual(config["claim.name"], "groups")
        self.assertEqual(config["full.path"], "false")
        self.assertEqual(config["access.token.claim"], "true")
        self.assertEqual(config["userinfo.token.claim"], "true")
        self.assertEqual(config["id.token.claim"], "false")

    def test_group_mapper_reconciliation_is_idempotent_and_rejects_conflicts(self):
        desired = {
            "name": "lakehouse-jupyterhub-groups",
            "protocolMapper": "oidc-group-membership-mapper",
            "config": {
                "claim.name": "groups",
                "full.path": "false",
                "id.token.claim": "false",
                "access.token.claim": "true",
                "userinfo.token.claim": "true",
            },
        }

        class ExistingMapperAPI:
            def __init__(self, mapper):
                self.mapper = mapper
                self.posts = 0

            def request(self, method, path, payload=None, *, query=None):
                if method == "GET":
                    return 200, [self.mapper]
                self.posts += 1
                return 201, None

        api = ExistingMapperAPI(desired)
        bootstrap.ensure_jupyterhub_group_mapper(api, "client-id")
        self.assertEqual(api.posts, 0)
        api = ExistingMapperAPI({**desired, "config": {**desired["config"], "full.path": "true"}})
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.ensure_jupyterhub_group_mapper(api, "client-id")
        self.assertEqual(api.posts, 0)

    def test_existing_client_conflict_is_refused(self):
        class ConflictingAPI:
            def request(self, method, path, payload=None, *, query=None):
                if path.endswith("/clients"):
                    return 200, [{"clientId": "jupyterhub", "id": "id", "publicClient": True}]
                raise AssertionError("Conflicting client must be refused before further requests")

        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.ensure_client(
                ConflictingAPI(), bootstrap.jupyterhub_client_configuration("secret")
            )

    def test_only_the_approved_local_callback_port_can_be_reconciled(self):
        self.assertTrue(
            bootstrap._is_local_jupyter_callback_change(
                "redirectUris",
                ["http://jupyterhub.localhost:8000/hub/oauth_callback"],
                ["http://jupyterhub.localhost:8088/hub/oauth_callback"],
            )
        )
        self.assertFalse(
            bootstrap._is_local_jupyter_callback_change(
                "redirectUris",
                ["http://jupyterhub.localhost:8000/hub/oauth_callback"],
                ["https://attacker.example/hub/oauth_callback"],
            )
        )

    def test_existing_client_secret_mismatch_is_refused(self):
        representation = bootstrap.jupyterhub_client_configuration("expected-secret")
        existing = {
            **representation,
            "id": "client-id",
            "secret": None,
            "redirectUris": representation["redirectUris"],
            "webOrigins": representation["webOrigins"],
        }

        class WrongSecretAPI:
            def request(self, method, path, payload=None, *, query=None):
                if path.endswith("/clients"):
                    return 200, [existing]
                if path.endswith("/client-secret"):
                    return 200, {"value": "different-secret"}
                raise AssertionError("Unexpected Keycloak admin request")

        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.ensure_client(WrongSecretAPI(), representation)


if __name__ == "__main__":
    unittest.main()
