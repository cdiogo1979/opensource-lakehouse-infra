#!/usr/bin/env python3
"""Delete all local v2 lakehouse state so the platform can be rebuilt from scratch.

Removes the lakehouse-local containers, data volumes (databases, buckets, realm,
users, Jenkins and Airflow metadata, StarRocks metadata and storage), Jupyter user
homes, networks, and this repository's generated runtime files (secrets,
certificates, Airflow Bundles).
Images, other projects' resources, and anything outside this repository's
.runtime directory are never touched. Irreversible.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / ".runtime"
PROJECT = "lakehouse-local"
VOLUMES = tuple(f"{PROJECT}_{name}" for name in (
    "keycloak-db-data", "polaris-db-data", "rustfs-data", "ldap-data", "jupyterhub-state", "jenkins-home", "airflow-postgres-data",
    "starrocks-fe-meta", "starrocks-be-storage",
))
VOLUME_PREFIXES = ("lakehouse-jupyter-home-",)
NETWORKS = tuple(f"{PROJECT}_{name}" for name in (
    "core", "jupyter-user", "data-access", "rustfs-identity", "airflow-internal", "airflow-spark", "starrocks",
))
RUNTIME_ROLES = ("jupyter-user-server", "airflow-spark-run")
# state: the data products' applied names, void once their objects are deleted.
RUNTIME_DIRECTORIES = ("credentials", "container-mounts", "airflow-dag-bundles", "state")


def parse_labels(value: str) -> dict[str, str]:
    labels = {}
    for item in (value or "").split(","):
        key, separator, text = item.partition("=")
        if separator:
            labels[key] = text
    return labels


def select_inventory(containers: list[dict], volumes: list[str], networks: list[str], runtime: Path) -> dict:
    """Choose exactly the v2 resources to delete from the current Docker and file state.

    Args:
        containers: Items with "name" and "labels" (a label dict).
        volumes: Existing volume names.
        networks: Existing network names.
        runtime: This repository's .runtime directory.

    Returns:
        A dict of sorted lists: containers, volumes, networks, directories.
    """
    chosen_containers = sorted(
        item["name"] for item in containers
        if item["labels"].get("com.docker.compose.project") == PROJECT
        or item["labels"].get("lakehouse-local.role") in RUNTIME_ROLES
    )
    chosen_volumes = sorted(v for v in volumes if v in VOLUMES or v.startswith(VOLUME_PREFIXES))
    chosen_networks = sorted(n for n in networks if n in NETWORKS)
    directories = sorted(str(runtime / name) for name in RUNTIME_DIRECTORIES if (runtime / name).exists())
    return {"containers": chosen_containers, "volumes": chosen_volumes, "networks": chosen_networks, "directories": directories}


def is_removable_directory(path: Path, runtime: Path = RUNTIME) -> bool:
    """Only the named generated directories directly under this repository's .runtime may be deleted."""
    resolved = path.resolve()
    return not path.is_symlink() and resolved.parent == runtime.resolve() and resolved.name in RUNTIME_DIRECTORIES


def docker(*args: str) -> str:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=True).stdout


def discover() -> dict:
    containers = []
    for line in docker("ps", "-a", "--format", "{{json .}}").splitlines():
        item = json.loads(line)
        containers.append({"name": item["Names"], "labels": parse_labels(item.get("Labels", ""))})
    volumes = docker("volume", "ls", "--format", "{{.Name}}").split()
    networks = docker("network", "ls", "--format", "{{.Name}}").split()
    return select_inventory(containers, volumes, networks, RUNTIME)


def print_inventory(inventory: dict) -> None:
    print("The lakehouse reset will permanently delete:")
    for kind in ("containers", "volumes", "networks", "directories"):
        items = inventory[kind]
        print(f"  {kind} ({len(items)}):")
        for item in items:
            print(f"    - {item}")
    print("Kept: images, other projects' volumes and containers, and everything outside this repository's .runtime.")


def confirmed(assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print("ERROR: the reset needs interactive confirmation; rerun with --yes for non-interactive use.", file=sys.stderr)
        return False
    try:
        return input("Type 'reset' to delete all of the above: ").strip() == "reset"
    except EOFError:
        return False


def remove(inventory: dict) -> None:
    for name in inventory["containers"]:
        docker("rm", "--force", "--volumes", name)
        print(f"Removed container {name}")
    for name in inventory["volumes"]:
        docker("volume", "rm", name)
        print(f"Removed volume {name}")
    for name in inventory["networks"]:
        docker("network", "rm", name)
        print(f"Removed network {name}")
    for value in inventory["directories"]:
        path = Path(value)
        if not is_removable_directory(path):
            raise RuntimeError(f"Refusing to delete a path outside {RUNTIME}: {path}")
        shutil.rmtree(path)
        print(f"Removed {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--yes", action="store_true", help="skip the interactive confirmation")
    mode.add_argument("--dry-run", action="store_true", help="only print what would be deleted")
    args = parser.parse_args()
    try:
        inventory = discover()
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        print("ERROR: could not list Docker resources; is Docker running?", file=sys.stderr)
        return 1
    print_inventory(inventory)
    if args.dry_run:
        print("Dry run: nothing was deleted.")
        return 0
    if not any(inventory.values()):
        print("Nothing to delete; the environment is already clean.")
        return 0
    if not confirmed(args.yes):
        print("Reset aborted; nothing was deleted.")
        return 1
    try:
        remove(inventory)
    except (subprocess.CalledProcessError, RuntimeError, OSError) as error:
        detail = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
        print(f"ERROR: reset stopped: {detail}. Fix the cause and rerun; completed steps are not repeated.", file=sys.stderr)
        return 1
    print("Reset complete. Rebuild with: scripts/lakehouse.sh start && scripts/bootstrap-default-product.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
