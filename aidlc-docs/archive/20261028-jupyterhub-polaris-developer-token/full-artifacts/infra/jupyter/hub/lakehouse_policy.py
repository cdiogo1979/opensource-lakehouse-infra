"""Pure admission and stable-home naming policy shared by Hub hooks/tests."""

import hashlib
from collections.abc import Awaitable, Callable


APPROVED_GROUPS = frozenset({"role-default-developer", "role-default-analyst"})
MAX_ACTIVE_SERVERS = 2
DEFAULT_CPU_LIMIT = 1.0
DEFAULT_MEMORY_LIMIT = "2G"


def eligible_group_names(groups: object) -> frozenset[str]:
    """Return admitted role memberships; malformed claims fail closed."""
    if not isinstance(groups, (list, tuple, set)) or any(not isinstance(v, str) for v in groups):
        return frozenset()
    return frozenset(groups).intersection(APPROVED_GROUPS)


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
