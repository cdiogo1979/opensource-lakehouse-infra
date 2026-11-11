"""Pure admission and stable-home naming policy shared by Hub hooks/tests."""

import hashlib
import logging
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

# The product model is mounted next to this module (/etc/jupyterhub) with the
# product files; in the repository it lives in infra/products.
try:
    import data_products
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "products"))
    import data_products


# The platform administrator is admitted with owner-level data access and is the Hub admin.
ADMIN_GROUPS = frozenset({data_products.PLATFORM_ADMIN_GROUP})
LOG = logging.getLogger("lakehouse.policy")
MAX_ACTIVE_SERVERS = 2
DEFAULT_CPU_LIMIT = 1.0
DEFAULT_MEMORY_LIMIT = "2G"


def approved_groups() -> frozenset[str]:
    """Groups admitted by the product files' apps.jupyterhub, read at every sign-in (BR-6).

    An unreadable or invalid product file fails closed to the platform administrator.
    """
    try:
        return data_products.jupyterhub_groups(data_products.load_all())
    except data_products.ProductError as error:
        LOG.error("Data product files are unusable; admitting only the platform administrator: %s", error)
        return ADMIN_GROUPS


def eligible_group_names(groups: object) -> frozenset[str]:
    """Return admitted role memberships; malformed claims fail closed."""
    if not isinstance(groups, (list, tuple, set)) or any(not isinstance(v, str) for v in groups):
        return frozenset()
    return frozenset(groups).intersection(approved_groups())


CHECKPOINT_ROLES = ("owner", "developer")
CHECKPOINT_ENVIRONMENT = "dev"


def checkpoint_buckets(groups: object, products=None) -> tuple[str, ...]:
    """The dev buckets whose checkpoint keys a user's server receives: products where a group is owner or developer.

    Never a uat or prod bucket; malformed claims give none.
    """
    if not isinstance(groups, (list, tuple, set)) or any(not isinstance(v, str) for v in groups):
        return ()
    products = data_products.load_all() if products is None else products
    member = frozenset(groups)
    return tuple(sorted(
        product.environment(CHECKPOINT_ENVIRONMENT).bucket
        for product in products
        if any(product.group(role) in member for role in CHECKPOINT_ROLES)
    ))


def checkpoint_key_volumes(buckets, host_dir: str, staged_dir: Path) -> dict[str, dict[str, str]]:
    """Read-only mounts of the staged keys; a missing or unsafe file fails the spawn."""
    host = Path(host_dir)
    if not host.is_absolute() or host.name != "checkpoint-keys":
        raise RuntimeError("The checkpoint key host folder is not configured safely.")
    volumes = {}
    for bucket in buckets:
        staged = staged_dir / bucket
        if staged.is_symlink() or not staged.is_file():
            raise RuntimeError(f"The checkpoint key for {bucket} is missing; run the product bootstrap.")
        volumes[str(host / bucket)] = {"bind": f"/run/secrets/lakehouse-checkpoints/{bucket}", "mode": "ro"}
    return volumes


def persistent_home_volume(subject: str) -> str:
    """Use a stable, collision-resistant Docker volume name without exposing sub."""
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("A stable OIDC subject is required for the user home.")
    digest = hashlib.sha256(subject.encode("utf-8")).hexdigest()[:32]
    return f"lakehouse-jupyter-home-{digest}"


async def attach_data_network(
    docker_call: Callable[..., Awaitable[object]], container_id: str, network_name: str
) -> None:
    """Await the second network attachment before returning to Hub readiness polling."""
    if not container_id or not network_name:
        raise ValueError("Container and network identifiers are required.")
    await docker_call("connect_container_to_network", container_id, network_name)


async def cleanup_partial_server(stop: Callable[..., Awaitable[object]]) -> bool:
    """Stop/remove a partial server while keeping its separately named home volume."""
    try:
        await stop(now=True)
        return True
    except Exception:
        return False
