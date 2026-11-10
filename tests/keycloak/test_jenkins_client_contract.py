"""Contract tests for the Jenkins Keycloak OIDC client."""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "keycloak_bootstrap_jenkins", ROOT / "infra/keycloak/bootstrap-realm.py"
)
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)

CALLBACKS_8090 = [
    "http://localhost:8090/securityRealm/finishLogin",
    "http://127.0.0.1:8090/securityRealm/finishLogin",
]
LOGOUTS_8090 = ["http://localhost:8090/", "http://127.0.0.1:8090/"]


class ExistingClientAPI:
    def __init__(self, existing, secret="test-secret"):
        self.existing = existing
        self.secret = secret
        self.updated = None

    def request(self, method, path, payload=None, *, query=None):
        if method == "GET" and path.endswith("/clients"):
            return 200, [self.existing]
        if method == "GET" and path.endswith("/client-secret"):
            return 200, {"value": self.secret}
        if method == "PUT":
            self.updated = payload
            return 204, None
        raise AssertionError(f"Unexpected request: {method} {path}")


class JenkinsClientContractTests(unittest.TestCase):
    def test_confidential_client_uses_exact_uris_and_pkce(self):
        client = bootstrap.jenkins_client_configuration("test-secret", 8090)
        self.assertEqual(client["clientId"], "jenkins")
        self.assertFalse(client["publicClient"])
        self.assertTrue(client["standardFlowEnabled"])
        self.assertFalse(client["directAccessGrantsEnabled"])
        self.assertFalse(client["serviceAccountsEnabled"])
        self.assertEqual(client["redirectUris"], CALLBACKS_8090)
        self.assertEqual(client["webOrigins"], [])
        self.assertEqual(client["attributes"]["pkce.code.challenge.method"], "S256")
        self.assertEqual(client["attributes"]["post.logout.redirect.uris"].split("##"), LOGOUTS_8090)

    def test_port_resolution_order_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("JENKINS_HOST_PORT=18090\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"JENKINS_HOST_PORT": "28090"}):
                self.assertEqual(bootstrap.jenkins_port(env_file), 28090)
            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(bootstrap.jenkins_port(env_file), 18090)
                self.assertEqual(bootstrap.jenkins_port(Path(directory) / "missing"), 8090)
            with mock.patch.dict(os.environ, {"JENKINS_HOST_PORT": "70000"}):
                with self.assertRaises(bootstrap.BootstrapError):
                    bootstrap.jenkins_port(env_file)

    def test_group_mapper_puts_groups_in_the_id_token(self):
        class FakeAPI:
            created = None

            def request(self, method, path, payload=None, *, query=None):
                if method == "GET":
                    return 200, []
                FakeAPI.created = payload
                return 201, None

        bootstrap.ensure_jenkins_group_mapper(FakeAPI(), "client-id")
        self.assertEqual(FakeAPI.created["name"], "lakehouse-jenkins-groups")
        self.assertEqual(FakeAPI.created["config"]["claim.name"], "groups")
        self.assertEqual(FakeAPI.created["config"]["full.path"], "false")
        self.assertEqual(FakeAPI.created["config"]["id.token.claim"], "true")
        self.assertEqual(FakeAPI.created["config"]["userinfo.token.claim"], "true")

    def test_port_move_reconciles_only_exact_previous_uris(self):
        desired = bootstrap.jenkins_client_configuration("test-secret", 8090)
        previous = bootstrap.jenkins_client_configuration("test-secret", 18090)
        api = ExistingClientAPI({**previous, "id": "client-id", "secret": None})
        bootstrap.ensure_client(api, desired)
        self.assertEqual(api.updated["redirectUris"], CALLBACKS_8090)
        self.assertEqual(api.updated["attributes"]["post.logout.redirect.uris"].split("##"), LOGOUTS_8090)

    def test_other_changes_and_secret_mismatch_are_refused(self):
        desired = bootstrap.jenkins_client_configuration("test-secret", 8090)
        for redirects in (["http://attacker.example:8090/securityRealm/finishLogin", CALLBACKS_8090[1]], ["http://localhost:8090/*"]):
            api = ExistingClientAPI({**desired, "id": "client-id", "redirectUris": redirects, "secret": None})
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.ensure_client(api, desired)
            self.assertIsNone(api.updated)
        api = ExistingClientAPI({**desired, "id": "client-id", "secret": None}, secret="other")
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.ensure_client(api, desired)

    def test_rustfs_port_moves_are_not_accepted_for_jenkins_paths(self):
        self.assertFalse(bootstrap._is_jenkins_port_change(
            bootstrap.rustfs_console_uris(9002, bootstrap.RUSTFS_CALLBACK_PATH),
            bootstrap.rustfs_console_uris(9001, bootstrap.RUSTFS_CALLBACK_PATH),
        ))

    def test_realm_contract_matches_the_default_client(self):
        contract = json.loads((ROOT / "infra/keycloak/realm-contract.json").read_text(encoding="utf-8"))
        jenkins = contract["clients"]["jenkins"]
        self.assertEqual(jenkins["redirect_uris"], CALLBACKS_8090)
        self.assertEqual(jenkins["post_logout_redirect_uris"], LOGOUTS_8090)
        self.assertEqual(jenkins["pkce"], "S256")
        self.assertTrue(jenkins["group_claim_in_id_token"])
        self.assertNotIn("role-default-writer", jenkins["authorized_groups"])

    def test_bootstrap_always_configures_the_jenkins_client(self):
        main = (ROOT / "infra/keycloak/bootstrap-realm.py").read_text(encoding="utf-8").split("def main()", 1)[1]
        self.assertIn('default=Path(".runtime/credentials/jenkins-oidc-client-secret")', main)
        self.assertIn("ensure_client(api, jenkins_client_configuration(jenkins_secret, jenkins_host_port))", main)
        self.assertIn('ensure_jenkins_group_mapper(api, jenkins["id"])', main)


if __name__ == "__main__":
    unittest.main()
