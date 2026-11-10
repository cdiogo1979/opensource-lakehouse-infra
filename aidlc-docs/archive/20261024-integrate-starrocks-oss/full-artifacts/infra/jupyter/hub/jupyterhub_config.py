import os
from pathlib import Path

from dockerspawner import DockerSpawner
from jupyterhub.auth import DummyAuthenticator


c = get_config()

USERS = {
    "user_a": {
        "volume": "iceberg-poc-jupyter-user-a-work",
        "rustfs_access": "rustfs-user-a-access-key",
        "rustfs_secret": "rustfs-user-a-secret-key",
    },
    "user_b": {
        "volume": "iceberg-poc-jupyter-user-b-work",
        "rustfs_access": "rustfs-user-b-access-key",
        "rustfs_secret": "rustfs-user-b-secret-key",
    },
    "admin": {
        "volume": "iceberg-poc-jupyter-admin-work",
        "rustfs_access": "rustfs-admin-access-key",
        "rustfs_secret": "rustfs-admin-secret-key",
    },
}

credentials_dir = Path(os.environ["JUPYTER_CREDENTIALS_DIR"]).resolve()
examples_dir = Path(os.environ["JUPYTER_EXAMPLES_DIR"]).resolve()
host_gid = int(os.environ["JUPYTER_HOST_GID"])
realm = os.environ.get("KERBEROS_REALM", "LAKEHOUSE.LOCAL")
aws_region = os.environ.get("AWS_REGION", "us-east-1")

c.JupyterHub.bind_url = "http://:8000"
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_port = 8081
c.JupyterHub.hub_connect_ip = "iceberg-poc-jupyterhub"
c.JupyterHub.cookie_secret_file = "/srv/jupyterhub/jupyterhub_cookie_secret"
c.JupyterHub.db_url = "sqlite:////srv/jupyterhub/jupyterhub.sqlite"
c.JupyterHub.authenticator_class = DummyAuthenticator
c.Authenticator.allow_all = False
c.Authenticator.allowed_users = set(USERS)
c.Authenticator.admin_users = {"admin"}
c.JupyterHub.spawner_class = DockerSpawner
c.JupyterHub.log_level = "INFO"

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


def configure_user_server(spawner):
    username = spawner.user.name
    identity = USERS.get(username)
    if identity is None:
        raise ValueError("No notebook identity is configured for this username.")

    keytab = credentials_dir / "keytabs" / f"{username}.keytab"
    access_key = credentials_dir / identity["rustfs_access"]
    secret_key = credentials_dir / identity["rustfs_secret"]

    spawner.volumes = {
        identity["volume"]: {
            "bind": "/home/jovyan/work",
            "mode": "rw",
        },
        str(keytab): {
            "bind": "/run/credentials/identity.keytab",
            "mode": "ro",
        },
        str(access_key): {
            "bind": "/run/credentials/rustfs-access-key",
            "mode": "ro",
        },
        str(secret_key): {
            "bind": "/run/credentials/rustfs-secret-key",
            "mode": "ro",
        },
        str(examples_dir): {
            "bind": "/opt/jupyter-examples",
            "mode": "ro",
        },
    }
    spawner.extra_create_kwargs = {
        "user": "10001:10001",
    }
    spawner.extra_host_config = {
        "group_add": [str(host_gid)],
        "tmpfs": {
            "/run/krb5": "uid=10001,gid=10001,mode=0700",
        },
    }
    spawner.environment = {
        "KERBEROS_REALM": realm,
        "KERBEROS_PRINCIPAL": f"{username}@{realm}",
        "KRB5_CONFIG": "/etc/krb5.conf",
        "KRB5CCNAME": "FILE:/run/krb5/ccache",
        "AWS_REGION": aws_region,
        "AWS_DEFAULT_REGION": aws_region,
        "S3_ENDPOINT": "http://object-store:9000",
        "SPARK_LOCAL_IP": "127.0.0.1",
    }


c.Spawner.pre_spawn_hook = configure_user_server
