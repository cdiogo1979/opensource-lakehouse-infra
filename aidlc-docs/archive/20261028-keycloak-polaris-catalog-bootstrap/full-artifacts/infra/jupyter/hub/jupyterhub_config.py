import asyncio
import json
import os
import ssl
from pathlib import Path

from dockerspawner import DockerSpawner
from ldapauthenticator import LDAPAuthenticator
from ldapauthenticator.ldapauthenticator import TlsStrategy
from ldap3 import AUTO_BIND_NO_TLS, AUTO_BIND_TLS_BEFORE_BIND, Connection, Server, Tls
from ldap3.core.exceptions import LDAPBindError
from lakehouse_ldap import current_role

c = get_config()

CONFIG_DIR = Path("/etc/jupyterhub")
IDENTITY_REGISTRY = json.loads((CONFIG_DIR / "user-identities.json").read_text())
host_credentials_dir = Path(os.environ["JUPYTER_CREDENTIALS_DIR"])
validation_credentials_dir = Path(
    os.environ.get("JUPYTER_CREDENTIALS_VALIDATION_DIR", "/run/credential-validation")
).resolve(strict=True)
if not host_credentials_dir.is_absolute():
    raise RuntimeError("The Docker host credential directory must be an absolute path.")
examples_dir = Path(os.environ["JUPYTER_EXAMPLES_DIR"])
if not examples_dir.is_absolute():
    raise RuntimeError("The Docker host examples directory must be an absolute path.")
host_gid = int(os.environ["JUPYTER_HOST_GID"])
host_uid = int(os.environ["JUPYTER_HOST_UID"])
realm = os.environ.get("KERBEROS_REALM", "LAKEHOUSE.LOCAL")
aws_region = os.environ.get("AWS_REGION", "us-east-1")
ldap_host = os.environ.get("FREEIPA_LDAP_HOST", "ipa.lakehouse.local")
ldap_user_base = os.environ.get(
    "FREEIPA_LDAP_USER_BASE", "cn=users,cn=accounts,dc=lakehouse,dc=local"
)
ldap_group_base = os.environ.get(
    "FREEIPA_LDAP_GROUP_BASE", "cn=groups,cn=accounts,dc=lakehouse,dc=local"
)
ldap_reader_dn = os.environ.get(
    "FREEIPA_LDAP_READER_DN",
    "uid=jupyterhub-ldap-reader,cn=users,cn=accounts,dc=lakehouse,dc=local",
)
ldap_ca_file = "/run/freeipa/ca.crt"
ldap_reader_password_file = Path("/run/secrets/freeipa-jupyterhub-ldap-reader-password")
auth_state_key_file = Path("/run/secrets/jupyterhub-auth-state-crypt-key")


def _read_secret(path):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("A required JupyterHub secret file is missing or unsafe.")
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        raise RuntimeError("A JupyterHub secret file has unsafe permissions.")
    value = path.read_text().strip()
    if not value:
        raise RuntimeError("A required JupyterHub secret file is empty.")
    return value


ldap_reader_password = _read_secret(ldap_reader_password_file)
auth_state_key = _read_secret(auth_state_key_file)


class StrictLDAPAuthenticator(LDAPAuthenticator):
    def get_connection(self, userdn, password):
        if self.tls_strategy == TlsStrategy.on_connect:
            use_ssl = True
            auto_bind = AUTO_BIND_NO_TLS
        elif self.tls_strategy == TlsStrategy.before_bind:
            use_ssl = False
            auto_bind = AUTO_BIND_TLS_BEFORE_BIND
        else:
            raise RuntimeError("Insecure LDAP transport is disabled.")

        server = Server(
            self.server_address,
            port=self.server_port,
            use_ssl=use_ssl,
            tls=Tls(**self.tls_kwargs),
            connect_timeout=5,
        )
        try:
            return Connection(
                server,
                user=userdn,
                password=password,
                auto_bind=auto_bind,
                receive_timeout=5,
            )
        except LDAPBindError:
            return None

    async def authenticate(self, handler, data):
        try:
            auth_model = await super().authenticate(handler, data)
        except Exception:
            # LDAPAuthenticator may raise on directory outages, TLS failures,
            # and bind/search errors before returning an authentication model.
            # Treat those conditions as a normal denial instead of leaking a
            # 500 response from the login handler.
            self.log.warning("LDAP authentication failed; denying login.")
            return None
        if not auth_model:
            return None
        username = auth_model["name"]
        try:
            role = await asyncio.to_thread(
                current_role,
                username,
                ldap_host,
                ldap_user_base,
                ldap_group_base,
                ldap_reader_dn,
                ldap_reader_password,
                ldap_ca_file,
            )
        except Exception:
            self.log.warning("LDAP role verification failed for %s; denying login.", username)
            return None
        auth_model.setdefault("auth_state", {})["lakehouse_role"] = role
        return auth_model

    async def check_allowed(self, username, auth_model):
        auth_state = (auth_model or {}).get("auth_state") or {}
        role = auth_state.get("lakehouse_role")
        return (username == "administrator" and role == "admin") or (
            username == "developer-user" and role == "developer"
        ) or (username == "analyst-user" and role == "analyst")

c.JupyterHub.bind_url = "http://:8000"
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_port = 8081
c.JupyterHub.hub_connect_ip = "iceberg-poc-jupyterhub"
c.JupyterHub.cookie_secret_file = "/srv/jupyterhub/jupyterhub_cookie_secret"
c.JupyterHub.db_url = "sqlite:////srv/jupyterhub/jupyterhub.sqlite"
c.JupyterHub.authenticator_class = StrictLDAPAuthenticator
c.CryptKeeper.keys = [auth_state_key]
c.Authenticator.enable_auth_state = True
c.Authenticator.allow_all = False
c.Authenticator.allowed_users = {"administrator"}
c.Authenticator.admin_users = {"administrator"}
c.JupyterHub.spawner_class = DockerSpawner
c.JupyterHub.log_level = "INFO"

c.LDAPAuthenticator.server_address = ldap_host
c.LDAPAuthenticator.server_port = 636
c.LDAPAuthenticator.tls_strategy = "on_connect"
c.LDAPAuthenticator.tls_kwargs = {
    "validate": ssl.CERT_REQUIRED,
    "ca_certs_file": ldap_ca_file,
}
c.LDAPAuthenticator.lookup_dn = True
c.LDAPAuthenticator.lookup_dn_search_user = ldap_reader_dn
c.LDAPAuthenticator.lookup_dn_search_password = ldap_reader_password
c.LDAPAuthenticator.lookup_dn_search_filter = "({login_attr}={login})"
c.LDAPAuthenticator.lookup_dn_user_dn_attribute = "uid"
c.LDAPAuthenticator.user_search_base = ldap_user_base
c.LDAPAuthenticator.user_attribute = "uid"
c.LDAPAuthenticator.allowed_groups = []

c.DockerSpawner.image = os.environ["DOCKER_NOTEBOOK_IMAGE"]
c.DockerSpawner.network_name = os.environ["DOCKER_NETWORK_NAME"]
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.remove = True
c.DockerSpawner.cmd = ["jupyterhub-singleuser"]
c.Spawner.default_url = "/lab"
c.Spawner.http_timeout = 120
c.Spawner.start_timeout = 120
c.Spawner.ip = "0.0.0.0"
c.Spawner.port = 8888


def _validate_credential_file(relative_path):
    relative_path = Path(relative_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise RuntimeError("The mapped user credential path is invalid.")
    path = validation_credentials_dir / relative_path
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("The mapped user credential is missing or unsafe.")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(validation_credentials_dir):
        raise RuntimeError("The mapped user credential resolves outside the credential directory.")
    for parent in path.parents:
        if parent == validation_credentials_dir:
            break
        if parent.is_symlink():
            raise RuntimeError("The mapped user credential path contains a symlink.")
    mode = path.stat().st_mode & 0o777
    # On Docker Desktop, bind-mounted host files are reported as UID 0 inside
    # Linux containers. Host ownership is verified by the host-side startup
    # preflight; this in-container check still enforces safe mode bits.
    if mode & 0o007 or mode & 0o020:
        raise RuntimeError("The mapped user credential has unsafe permissions.")
    return str(host_credentials_dir / relative_path)


async def configure_user_server(spawner):
    username = spawner.user.name
    identity = IDENTITY_REGISTRY.get(username)
    if identity is None:
        raise RuntimeError("No notebook identity is configured for this user.")

    expected_role = identity["role"]
    try:
        actual_role = await asyncio.to_thread(
            current_role,
            username,
            ldap_host,
            ldap_user_base,
            ldap_group_base,
            ldap_reader_dn,
            ldap_reader_password,
            ldap_ca_file,
        )
    except Exception as error:
        raise RuntimeError("Current directory authorization could not be verified.") from error
    if actual_role != expected_role:
        raise RuntimeError("Current directory role does not match the notebook identity.")

    keytab = _validate_credential_file(Path("keytabs") / identity["keytab"])
    access_key = _validate_credential_file(identity["rustfs_access"])
    secret_key = _validate_credential_file(identity["rustfs_secret"])

    spawner.volumes = {
        identity["volume"]: {"bind": "/home/jovyan/work", "mode": "rw"},
        keytab: {"bind": "/run/credential-source/identity.keytab", "mode": "ro"},
        access_key: {"bind": "/run/credential-source/rustfs-access-key", "mode": "ro"},
        secret_key: {"bind": "/run/credential-source/rustfs-secret-key", "mode": "ro"},
        str(examples_dir): {
            "bind": "/opt/jupyter-examples",
            "mode": "ro",
        },
    }
    spawner.extra_create_kwargs = {"user": "0:0"}
    spawner.extra_host_config = {
        "group_add": [str(host_gid)],
        "tmpfs": {
            "/run/krb5": "uid=0,gid=0,mode=0700,noexec,nosuid,size=16m",
        },
    }
    spawner.extra_host_config["tmpfs"]["/run/credentials"] = (
        "uid=0,gid=10001,mode=0750,noexec,nosuid,size=16m"
    )
    spawner.environment = {
        "HOME": "/home/jovyan",
        "KERBEROS_REALM": realm,
        "KERBEROS_PRINCIPAL": identity["mit_principal"],
        "KRB5_CONFIG": "/etc/krb5.conf",
        "KRB5CCNAME": "FILE:/run/krb5/ccache",
        "AWS_REGION": aws_region,
        "AWS_DEFAULT_REGION": aws_region,
        "S3_ENDPOINT": "http://object-store:9000",
        "SPARK_LOCAL_IP": "127.0.0.1",
        "JUPYTER_HOST_GID": str(host_gid),
        "JUPYTER_HOST_UID": str(host_uid),
    }


c.Spawner.pre_spawn_hook = configure_user_server
