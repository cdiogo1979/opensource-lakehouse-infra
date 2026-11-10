"""JupyterHub OIDC admission and isolated DockerSpawner configuration."""

import os
from pathlib import Path

from oauthenticator.generic import GenericOAuthenticator

from lakehouse_policy import ADMIN_GROUPS, eligible_group_names
from lakehouse_spawner import LakehouseDockerSpawner


class LakehouseOAuthenticator(GenericOAuthenticator):
    """Admits the groups the data product files list for JupyterHub, read at each sign-in."""

    async def check_allowed(self, username, auth_model):
        if auth_model is None:
            return True
        if auth_model.get("admin"):
            return True
        return bool(eligible_group_names(auth_model.get("groups")))


def read_secret(path: str) -> str:
    secret_path = Path(path)
    if secret_path.is_symlink() or not secret_path.is_file():
        raise RuntimeError("A required JupyterHub secret is unavailable.")
    if secret_path.stat().st_mode & 0o077:
        raise RuntimeError("A JupyterHub secret has unsafe permissions.")
    value = secret_path.read_text(encoding="utf-8").strip()
    if not value or any(char not in "0123456789abcdefABCDEF" for char in value):
        raise RuntimeError("A required JupyterHub secret has an invalid format.")
    return value


c = get_config()
client_secret = read_secret("/run/secrets/jupyterhub_oidc_client_secret")
crypt_key = read_secret("/run/secrets/jupyterhub_auth_state_crypt_key")

c.JupyterHub.bind_url = "http://:8000"
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_port = 8081
c.JupyterHub.hub_connect_ip = "jupyterhub"
c.JupyterHub.db_url = "sqlite:////srv/jupyterhub/jupyterhub.sqlite"
c.JupyterHub.cookie_secret_file = "/srv/jupyterhub/jupyterhub_cookie_secret"
c.JupyterHub.concurrent_spawn_limit = 2
c.JupyterHub.active_server_limit = 2
c.JupyterHub.log_level = "INFO"
c.JupyterHub.extra_handlers = []

c.JupyterHub.authenticator_class = LakehouseOAuthenticator
c.Authenticator.enable_auth_state = True
c.CryptKeeper.keys = [crypt_key]
c.Authenticator.allow_all = False
c.Authenticator.manage_groups = True
# Admission follows the data product files (LakehouseOAuthenticator.check_allowed).
c.Authenticator.admin_groups = set(ADMIN_GROUPS)
c.Authenticator.refresh_pre_spawn = True
c.GenericOAuthenticator.client_id = "jupyterhub"
c.GenericOAuthenticator.client_secret = client_secret
c.GenericOAuthenticator.oauth_callback_url = os.environ["JUPYTERHUB_OAUTH_CALLBACK_URL"]
c.GenericOAuthenticator.authorize_url = "http://keycloak.localhost:8080/realms/lakehouse/protocol/openid-connect/auth"
c.GenericOAuthenticator.token_url = "http://keycloak:8080/realms/lakehouse/protocol/openid-connect/token"
c.GenericOAuthenticator.userdata_url = "http://keycloak:8080/realms/lakehouse/protocol/openid-connect/userinfo"
c.GenericOAuthenticator.userdata_token_method = "GET"
c.GenericOAuthenticator.username_claim = "sub"
c.GenericOAuthenticator.auth_state_groups_key = "oauth_user.groups"
c.GenericOAuthenticator.manage_groups = True
c.GenericOAuthenticator.admin_groups = set(ADMIN_GROUPS)
c.GenericOAuthenticator.scope = ["openid", "profile", "email"]
c.GenericOAuthenticator.enable_pkce = True
c.GenericOAuthenticator.refresh_pre_spawn = True
c.GenericOAuthenticator.basic_auth = False

c.JupyterHub.spawner_class = LakehouseDockerSpawner
c.DockerSpawner.image = os.environ["DOCKER_NOTEBOOK_IMAGE"]
c.DockerSpawner.pull_policy = "ifnotpresent"
c.DockerSpawner.network_name = os.environ["JUPYTER_USER_NETWORK_NAME"]
c.DockerSpawner.data_access_network_name = os.environ["DATA_ACCESS_NETWORK_NAME"]
c.LakehouseDockerSpawner.broker_ca_host_path = os.environ["JUPYTERHUB_BROKER_CA_HOST_PATH"]
c.DockerSpawner.environment = {
    "LAKEHOUSE_TOKEN_BROKER_URL": "https://jupyterhub:8443/api/v1/token",
    "LAKEHOUSE_TOKEN_BROKER_CA": "/run/certs/jupyterhub-broker-ca.crt",
}
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.remove = True
c.DockerSpawner.cmd = ["jupyterhub-singleuser"]
c.DockerSpawner.extra_create_kwargs = {
    "labels": {"lakehouse-local.role": "jupyter-user-server"}
}
c.DockerSpawner.mem_limit = os.environ.get("JUPYTERHUB_SINGLEUSER_MEMORY_LIMIT", "2G")
c.DockerSpawner.cpu_limit = float(os.environ.get("JUPYTERHUB_SINGLEUSER_CPU_LIMIT", "1"))
c.Spawner.default_url = "/lab"
c.Spawner.http_timeout = 120
c.Spawner.start_timeout = 120
c.Spawner.ip = "0.0.0.0"
c.Spawner.port = 8888
c.Spawner.pre_spawn_hook = LakehouseDockerSpawner.check_current_admission

# The broker is started by the Hub subclass on a separate TLS server, bound
# only to the stable jupyter-user network interface.
for tls_path in (
    "/run/certs/jupyterhub-broker-server.crt",
    "/run/certs/jupyterhub-broker-server-key.pem",
    "/run/certs/jupyterhub-broker-ca.crt",
):
    if Path(tls_path).is_symlink() or not Path(tls_path).is_file():
        raise RuntimeError("JupyterHub broker TLS material is unavailable.")
