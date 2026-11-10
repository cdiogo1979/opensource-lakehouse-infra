"""DockerSpawner hooks for the local dual-network lakehouse topology."""

from dockerspawner import DockerSpawner
from traitlets import Unicode
from pathlib import Path
from lakehouse_policy import (
    attach_data_network,
    checkpoint_buckets,
    checkpoint_key_volumes,
    cleanup_partial_server,
    eligible_group_names,
    persistent_home_volume,
)

# The staged checkpoint keys, mounted read-only into the Hub for these checks.
CHECKPOINT_KEYS_DIR = Path("/run/secrets/checkpoint-keys")


class LakehouseDockerSpawner(DockerSpawner):
    """Attach the data network before Hub begins its server readiness checks."""

    data_access_network_name = Unicode(config=True)
    broker_ca_host_path = Unicode(config=True)
    checkpoint_keys_host_dir = Unicode(config=True)

    @staticmethod
    async def check_current_admission(spawner):
        auth_state = await spawner.user.get_auth_state()
        oauth_user = (auth_state or {}).get("oauth_user") or {}
        if not eligible_group_names(oauth_user.get("groups")):
            raise RuntimeError("Current Keycloak group admission check failed.")
        volumes = dict(spawner.volumes or {})
        volumes[persistent_home_volume(spawner.user.name)] = {
            "bind": "/home/jovyan/work",
            "mode": "rw",
        }
        ca_host_path = Path(spawner.broker_ca_host_path)
        # Docker bind sources are host paths and are not necessarily visible inside
        # the Hub container. Validate the read-only in-container mount instead.
        ca_container_path = Path("/run/certs/jupyterhub-broker-ca.crt")
        if (
            not ca_host_path.is_absolute()
            or ca_host_path.name != "jupyterhub-broker-ca.crt"
            or ca_host_path.is_symlink()
            or ca_container_path.is_symlink()
            or not ca_container_path.is_file()
        ):
            raise RuntimeError("The broker CA host mount is unavailable or unsafe.")
        volumes[str(ca_host_path)] = {
            "bind": "/run/certs/jupyterhub-broker-ca.crt",
            "mode": "ro",
        }
        # The dev checkpoint keys of the user's owner and developer products (never uat or prod).
        volumes.update(checkpoint_key_volumes(
            checkpoint_buckets(oauth_user.get("groups")), spawner.checkpoint_keys_host_dir, CHECKPOINT_KEYS_DIR))
        spawner.volumes = volumes

    async def start(self):
        address = await super().start()
        try:
            container_id = self.container_id
            if not container_id:
                raise RuntimeError("DockerSpawner did not return a container identifier.")
            await attach_data_network(self.docker, container_id, self.data_access_network_name)
        except Exception as error:
            if not await cleanup_partial_server(self.stop):
                self.log.warning("Failed to clean up a partially started user server.")
            raise RuntimeError("Could not attach the user server to its data network.") from error
        return address
