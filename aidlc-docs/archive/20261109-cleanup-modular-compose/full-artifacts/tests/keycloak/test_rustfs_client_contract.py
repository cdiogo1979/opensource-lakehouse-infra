"""Contract tests for the RustFS console Keycloak OIDC client."""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "keycloak_bootstrap_rustfs", ROOT / "infra/keycloak/bootstrap-realm.py"
)
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)

CALLBACKS_9001 = [
    "http://localhost:9001/rustfs/admin/v3/oidc/callback/default",
    "http://127.0.0.1:9001/rustfs/admin/v3/oidc/callback/default",
]
LOGOUTS_9001 = [
    "http://localhost:9001/rustfs/console/auth/login",
    "http://127.0.0.1:9001/rustfs/console/auth/login",
]


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


class RustfsClientContractTests(unittest.TestCase):
    def test_confidential_client_uses_exact_console_uris_and_pkce(self):
        client = bootstrap.rustfs_client_configuration("test-secret", 9001)
        self.assertEqual(client["clientId"], "rustfs")
        self.assertFalse(client["publicClient"])
        self.assertTrue(client["standardFlowEnabled"])
        self.assertFalse(client["directAccessGrantsEnabled"])
        self.assertFalse(client["serviceAccountsEnabled"])
        self.assertEqual(client["clientAuthenticatorType"], "client-secret")
        self.assertEqual(client["redirectUris"], CALLBACKS_9001)
        self.assertEqual(client["webOrigins"], [])
        self.assertEqual(client["attributes"]["pkce.code.challenge.method"], "S256")
        self.assertEqual(client["attributes"]["post.logout.redirect.uris"].split("##"), LOGOUTS_9001)
        self.assertFalse(any("*" in uri for uri in client["redirectUris"] + LOGOUTS_9001))

    def test_console_port_comes_from_environment_then_env_file_then_default(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("OTHER=1\nRUSTFS_CONSOLE_HOST_PORT=19001\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"RUSTFS_CONSOLE_HOST_PORT": "29001"}):
                self.assertEqual(bootstrap.rustfs_console_port(env_file), 29001)
            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(bootstrap.rustfs_console_port(env_file), 19001)
                self.assertEqual(bootstrap.rustfs_console_port(Path(directory) / "missing"), 9001)

    def test_invalid_console_port_is_rejected(self):
        for value in ("0", "65536", "90a1", "-1"):
            with mock.patch.dict(os.environ, {"RUSTFS_CONSOLE_HOST_PORT": value}):
                with self.assertRaises(bootstrap.BootstrapError):
                    bootstrap.rustfs_console_port(Path("/nonexistent/.env"))

    def test_group_mapper_puts_groups_in_the_id_token(self):
        class FakeAPI:
            created = None

            def request(self, method, path, payload=None, *, query=None):
                if method == "GET":
                    return 200, []
                FakeAPI.created = payload
                return 201, None

        bootstrap.ensure_rustfs_group_mapper(FakeAPI(), "client-id")
        mapper = FakeAPI.created
        self.assertEqual(mapper["name"], "lakehouse-rustfs-groups")
        self.assertEqual(mapper["protocolMapper"], "oidc-group-membership-mapper")
        self.assertEqual(
            mapper["config"],
            {
                "claim.name": "groups",
                "full.path": "false",
                "id.token.claim": "true",
                "access.token.claim": "true",
                "userinfo.token.claim": "true",
            },
        )

    def test_group_mapper_rejects_conflicts_and_duplicates(self):
        conflicting = {
            "name": bootstrap.RUSTFS_GROUP_MAPPER_NAME,
            "protocolMapper": "oidc-group-membership-mapper",
            "config": {"claim.name": "groups", "full.path": "true"},
        }
        for mappers in ([conflicting], [conflicting, conflicting]):
            class FakeAPI:
                def request(self, method, path, payload=None, *, query=None):
                    if method == "GET":
                        return 200, mappers
                    raise AssertionError("must not create")

            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.ensure_rustfs_group_mapper(FakeAPI(), "client-id")

    def test_console_port_change_reconciles_only_the_exact_previous_uris(self):
        desired = bootstrap.rustfs_client_configuration("test-secret", 9001)
        previous = bootstrap.rustfs_client_configuration("test-secret", 19001)
        api = ExistingClientAPI({**previous, "id": "client-id", "secret": None})
        bootstrap.ensure_client(api, desired)
        self.assertEqual(api.updated["redirectUris"], CALLBACKS_9001)
        self.assertEqual(api.updated["attributes"]["post.logout.redirect.uris"].split("##"), LOGOUTS_9001)

    def test_other_callback_changes_are_refused(self):
        desired = bootstrap.rustfs_client_configuration("test-secret", 9001)
        for redirects in (
            ["http://attacker.example:9001/rustfs/admin/v3/oidc/callback/default", CALLBACKS_9001[1]],
            ["http://localhost:9001/*"],
            CALLBACKS_9001[:1],
        ):
            api = ExistingClientAPI({**desired, "id": "client-id", "redirectUris": redirects, "secret": None})
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.ensure_client(api, desired)
            self.assertIsNone(api.updated)
        self.assertFalse(
            bootstrap._is_rustfs_console_port_change(
                bootstrap.rustfs_console_uris(19001, bootstrap.RUSTFS_CALLBACK_PATH),
                bootstrap.rustfs_console_uris(29001, bootstrap.RUSTFS_POST_LOGOUT_PATH),
            )
        )

    def test_secret_mismatch_is_refused(self):
        desired = bootstrap.rustfs_client_configuration("test-secret", 9001)
        api = ExistingClientAPI({**desired, "id": "client-id", "secret": None}, secret="other-secret")
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.ensure_client(api, desired)
        self.assertIsNone(api.updated)

    def test_realm_contract_matches_the_default_client(self):
        contract = json.loads((ROOT / "infra/keycloak/realm-contract.json").read_text(encoding="utf-8"))
        rustfs = contract["clients"]["rustfs"]
        self.assertEqual(rustfs["redirect_uris"], CALLBACKS_9001)
        self.assertEqual(rustfs["post_logout_redirect_uris"], LOGOUTS_9001)
        self.assertEqual(rustfs["pkce"], "S256")
        self.assertEqual(rustfs["group_claim"], "groups")
        self.assertTrue(rustfs["group_claim_in_id_token"])
        self.assertEqual(sorted(rustfs["group_values"]), sorted(contract["groups"]))

    def test_bootstrap_always_configures_the_rustfs_client(self):
        source = (ROOT / "infra/keycloak/bootstrap-realm.py").read_text(encoding="utf-8")
        main = source.split("def main()", 1)[1]
        self.assertIn('default=Path(".runtime/credentials/rustfs-oidc-client-secret")', main)
        self.assertIn("ensure_client(api, rustfs_client_configuration(rustfs_secret, rustfs_port))", main)
        self.assertIn("ensure_rustfs_group_mapper(api, rustfs[\"id\"])", main)


if __name__ == "__main__":
    unittest.main()
