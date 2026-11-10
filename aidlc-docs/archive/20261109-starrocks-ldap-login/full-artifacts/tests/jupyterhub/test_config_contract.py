"""Static contract checks for the generated JupyterHub configuration."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class HubConfigContractTests(unittest.TestCase):
    def test_config_uses_confidential_oidc_and_encrypted_auth_state(self):
        config = (ROOT / "infra/jupyter/hub/jupyterhub_config.py").read_text()
        self.assertIn("class LakehouseOAuthenticator(GenericOAuthenticator):", config)
        self.assertIn("authenticator_class = LakehouseOAuthenticator", config)
        self.assertIn("enable_auth_state = True", config)
        self.assertIn("CryptKeeper.keys = [crypt_key]", config)
        self.assertIn('username_claim = "sub"', config)
        self.assertIn("enable_pkce = True", config)

    def test_config_admits_the_product_file_groups_and_platform_admin(self):
        config = (ROOT / "infra/jupyter/hub/jupyterhub_config.py").read_text()
        # Admission is read from the data product files at each sign-in, never hard-coded.
        self.assertIn("return bool(eligible_group_names(auth_model.get(\"groups\")))", config)
        self.assertNotIn("allowed_groups", config)
        self.assertEqual(config.count("admin_groups = set(ADMIN_GROUPS)"), 2)
        self.assertNotIn("role-default-", config)
        compose = (ROOT / "compose.jupyter.yml").read_text()
        self.assertIn("- ./data-products:/etc/jupyterhub/data-products:ro", compose)
        self.assertIn("- ./infra/products/data_products.py:/etc/jupyterhub/data_products.py:ro", compose)

    def test_active_hub_config_has_no_ldap_or_keytab_dependencies(self):
        config = (ROOT / "infra/jupyter/hub/jupyterhub_config.py").read_text()
        image = (ROOT / "infra/jupyter/hub/Dockerfile").read_text()
        for legacy in ("LDAPAuthenticator", "FREEIPA", "keytab", "kinit", "rustfs-secret-key"):
            self.assertNotIn(legacy, config)
        self.assertNotIn("lakehouse_ldap.py", image)
        self.assertNotIn("user-identities.json", image)

    def test_two_server_limit_and_spawn_revalidation_are_configured(self):
        config = (ROOT / "infra/jupyter/hub/jupyterhub_config.py").read_text()
        self.assertIn("concurrent_spawn_limit = 2", config)
        self.assertIn("active_server_limit = 2", config)
        self.assertIn('DockerSpawner.pull_policy = "ifnotpresent"', config)
        self.assertIn('DockerSpawner.cmd = ["jupyterhub-singleuser"]', config)
        self.assertIn('exec "$@"', (ROOT / "infra/jupyter/singleuser/start-session.sh").read_text())
        self.assertIn("refresh_pre_spawn = True", config)
        self.assertIn("pre_spawn_hook = LakehouseDockerSpawner.check_current_admission", config)
        self.assertIn("connect_container_to_network", (ROOT / "infra/jupyter/hub/lakehouse_policy.py").read_text())
        self.assertIn("lakehouse-local.role", config)
        self.assertIn("docker rm --force", (ROOT / "scripts/lakehouse.sh").read_text())
        self.assertNotIn("docker.sock", (ROOT / "infra/jupyter/singleuser/Dockerfile").read_text())

    def test_oauth_userinfo_uses_supported_http_method_option(self):
        config = (ROOT / "infra/jupyter/hub/jupyterhub_config.py").read_text()
        self.assertIn('userdata_token_method = "GET"', config)
        self.assertNotIn("userdata_method =", config)

    def test_spawner_validates_ca_inside_hub_and_uses_host_path_only_for_bind(self):
        spawner = (ROOT / "infra/jupyter/hub/lakehouse_spawner.py").read_text()
        self.assertIn('Path("/run/certs/jupyterhub-broker-ca.crt")', spawner)
        self.assertIn("not ca_container_path.is_file()", spawner)
        self.assertNotIn("not ca_host_path.is_file()", spawner)

    def test_singleuser_image_copies_java_security_configuration(self):
        dockerfile = (ROOT / "infra/jupyter/singleuser/Dockerfile").read_text()
        self.assertIn("COPY --from=spark-runtime /etc/java-17-openjdk /etc/java-17-openjdk", dockerfile)


if __name__ == "__main__":
    unittest.main()


class MaintenanceServiceContractTests(unittest.TestCase):
    def test_maintenance_service_token_is_a_mounted_secret_scoped_to_users(self):
        config = (ROOT / "infra/jupyter/hub/jupyterhub_config.py").read_text()
        self.assertIn('read_secret("/run/secrets/jupyterhub_maintenance_token")', config)
        self.assertIn('"scopes": ["admin:users"], "services": ["lakehouse-maintenance"]', config)
        compose = (ROOT / "compose.jupyter.yml").read_text()
        self.assertIn("jupyterhub-maintenance-token:/run/secrets/jupyterhub_maintenance_token:ro", compose)
