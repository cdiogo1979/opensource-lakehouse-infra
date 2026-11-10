"""Contract tests for the Airflow Keycloak OIDC client."""

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "keycloak_bootstrap", ROOT / "infra/keycloak/bootstrap-realm.py"
)
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


class AirflowClientContractTests(unittest.TestCase):
    def test_confidential_client_uses_exact_callback_and_disabled_alternatives(self):
        client = bootstrap.airflow_client_configuration("test-secret")
        self.assertEqual(client["clientId"], "airflow")
        self.assertFalse(client["publicClient"])
        self.assertTrue(client["standardFlowEnabled"])
        self.assertFalse(client["directAccessGrantsEnabled"])
        self.assertFalse(client["serviceAccountsEnabled"])
        self.assertEqual(
            client["redirectUris"],
            [
                "http://localhost:8085/auth/oauth-authorized/keycloak",
                "http://127.0.0.1:8085/auth/oauth-authorized/keycloak",
            ],
        )
        self.assertEqual(client["webOrigins"], [])

    def test_existing_client_reconciles_only_the_previous_exact_callback(self):
        desired = bootstrap.airflow_client_configuration("test-secret")
        existing = {
            **desired,
            "id": "client-id",
            "redirectUris": [bootstrap.AIRFLOW_LEGACY_REDIRECT_URI],
            "secret": None,
        }

        class ExistingClientAPI:
            def __init__(self):
                self.updated = None

            def request(self, method, path, payload=None, *, query=None):
                if method == "GET" and path.endswith("/clients"):
                    return 200, [existing]
                if method == "GET" and path.endswith("/client-secret"):
                    return 200, {"value": "test-secret"}
                if method == "PUT":
                    self.updated = payload
                    return 204, None
                raise AssertionError(f"Unexpected request: {method} {path}")

        api = ExistingClientAPI()
        bootstrap.ensure_client(api, desired)
        self.assertEqual(api.updated["redirectUris"], desired["redirectUris"])

    def test_airflow_callback_reconciliation_rejects_other_uri_changes(self):
        self.assertFalse(
            bootstrap._is_airflow_callback_correction(
                "redirectUris",
                ["http://attacker.example/callback"],
                list(bootstrap.AIRFLOW_REDIRECT_URIS),
            )
        )
        self.assertFalse(
            bootstrap._is_airflow_callback_correction(
                "webOrigins",
                [bootstrap.AIRFLOW_LEGACY_REDIRECT_URI],
                list(bootstrap.AIRFLOW_REDIRECT_URIS),
            )
        )

    def test_existing_localhost_only_callback_reconciles_to_both_loopback_hosts(self):
        desired = bootstrap.airflow_client_configuration("test-secret")
        existing = {
            **desired,
            "id": "client-id",
            "redirectUris": [bootstrap.AIRFLOW_REDIRECT_URIS[0]],
            "secret": None,
        }

        class ExistingClientAPI:
            def __init__(self):
                self.updated = None

            def request(self, method, path, payload=None, *, query=None):
                if method == "GET" and path.endswith("/clients"):
                    return 200, [existing]
                if method == "GET" and path.endswith("/client-secret"):
                    return 200, {"value": "test-secret"}
                if method == "PUT":
                    self.updated = payload
                    return 204, None
                raise AssertionError(f"Unexpected request: {method} {path}")

        api = ExistingClientAPI()
        bootstrap.ensure_client(api, desired)
        self.assertEqual(api.updated["redirectUris"], desired["redirectUris"])

    def test_group_mapper_exposes_groups_to_userinfo_and_access_token(self):
        class FakeAPI:
            def __init__(self):
                self.created = None

            def request(self, method, path, payload=None, *, query=None):
                if method == "GET":
                    return 200, []
                self.created = payload
                return 201, None

        api = FakeAPI()
        bootstrap.ensure_airflow_group_mapper(api, "client-id")
        mapper = api.created
        self.assertEqual(mapper["protocolMapper"], "oidc-group-membership-mapper")
        self.assertEqual(mapper["config"]["claim.name"], "groups")
        self.assertEqual(mapper["config"]["full.path"], "false")
        self.assertEqual(mapper["config"]["access.token.claim"], "true")
        self.assertEqual(mapper["config"]["userinfo.token.claim"], "true")
        self.assertEqual(mapper["config"]["id.token.claim"], "false")

    def test_group_mapper_is_idempotent_and_rejects_conflicts(self):
        desired = {
            "name": bootstrap.AIRFLOW_GROUP_MAPPER_NAME,
            "protocol": "openid-connect",
            "protocolMapper": "oidc-group-membership-mapper",
            "consentRequired": False,
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
        bootstrap.ensure_airflow_group_mapper(api, "client-id")
        self.assertEqual(api.posts, 0)
        api = ExistingMapperAPI(
            {**desired, "config": {**desired["config"], "full.path": "true"}}
        )
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.ensure_airflow_group_mapper(api, "client-id")
        self.assertEqual(api.posts, 0)

    def test_existing_client_direct_grant_conflict_is_refused(self):
        desired = bootstrap.airflow_client_configuration("test-secret")
        existing = {
            **desired,
            "id": "client-id",
            "directAccessGrantsEnabled": True,
            "secret": None,
        }

        class ConflictingAPI:
            def request(self, method, path, payload=None, *, query=None):
                if path.endswith("/clients"):
                    return 200, [existing]
                raise AssertionError("Conflicting client must be refused immediately")

        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.ensure_client(ConflictingAPI(), desired)

    def test_realm_contract_documents_callback_and_group_claim_without_secret(self):
        contract = json.loads(
            (ROOT / "infra/keycloak/realm-contract.json").read_text(
                encoding="utf-8"
            )
        )
        airflow = contract["clients"]["airflow"]
        self.assertEqual(
            airflow["redirect_uris"],
            [
                "http://localhost:8085/auth/oauth-authorized/keycloak",
                "http://127.0.0.1:8085/auth/oauth-authorized/keycloak",
            ],
        )
        self.assertEqual(airflow["group_claim"], "groups")
        self.assertNotIn("secret", json.dumps(airflow).lower())


if __name__ == "__main__":
    unittest.main()
