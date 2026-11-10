#!/usr/bin/env python3
"""Reject a configured Docker bridge subnet that overlaps local routes."""

from __future__ import annotations

import ipaddress
import json
import os
import shutil
import subprocess
import sys


def _run(argv: list[str]) -> str:
    try:
        result = subprocess.run(argv, check=True, text=True, capture_output=True, timeout=15)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"Could not inspect local network state with {argv[0]}.") from error
    return result.stdout


def route_networks() -> list[ipaddress._BaseNetwork]:
    if shutil.which("ip"):
        try:
            entries = json.loads(_run(["ip", "-j", "route", "show", "table", "all"]))
            results = []
            for entry in entries:
                destination = entry.get("dst")
                if destination and destination != "default":
                    results.append(ipaddress.ip_network(destination, strict=False))
            return results
        except (ValueError, TypeError, json.JSONDecodeError):
            pass
    if shutil.which("netstat"):
        results = []
        for line in _run(["netstat", "-rn", "-f", "inet"]).splitlines():
            fields = line.split()
            if not fields or fields[0].lower() == "destination" or fields[0] == "default":
                continue
            try:
                destination = fields[0]
                route_address = destination.split("/", 1)[0]
                if route_address.replace(".", "").isdigit():
                    if "/" in destination:
                        address, prefix = destination.split("/", 1)
                    else:
                        address, prefix = destination, str(8 * len(destination.split(".")))
                    components = address.split(".")
                    if len(components) < 4:
                        destination = ".".join(components + ["0"] * (4 - len(components))) + f"/{prefix}"
                results.append(ipaddress.ip_network(destination, strict=False))
            except ValueError:
                continue
        return results
    raise RuntimeError("Neither iproute2 nor netstat is available for route conflict checks.")


def docker_networks(expected_subnet: ipaddress._BaseNetwork) -> tuple[list[ipaddress._BaseNetwork], bool]:
    if not shutil.which("docker"):
        return [], False
    ids = _run(["docker", "network", "ls", "-q"]).splitlines()
    if not ids:
        return [], False
    data = json.loads(_run(["docker", "network", "inspect", *ids]))
    results = []
    own_network_exists = False
    for network in data:
        if network.get("Name") == "lakehouse-local_jupyter-user":
            own_network_exists = True
            configured = {
                ipaddress.ip_network(config["Subnet"], strict=False)
                for config in network.get("IPAM", {}).get("Config", []) or []
                if config.get("Subnet")
            }
            if configured and configured != {expected_subnet}:
                raise RuntimeError(
                    "The existing lakehouse-local_jupyter-user network has a different subnet; "
                    "review and recreate that network explicitly before startup."
                )
            continue
        for config in network.get("IPAM", {}).get("Config", []) or []:
            subnet = config.get("Subnet")
            if subnet:
                results.append(ipaddress.ip_network(subnet, strict=False))
    return results, own_network_exists


def check(subnet_text: str, hub_ip_text: str) -> None:
    subnet = ipaddress.ip_network(subnet_text, strict=True)
    hub_ip = ipaddress.ip_address(hub_ip_text)
    if hub_ip not in subnet or hub_ip in (subnet.network_address, subnet.broadcast_address):
        raise RuntimeError("JUPYTERHUB_BROKER_BIND_IP must be a usable address inside JUPYTER_USER_SUBNET.")
    routes = route_networks()
    docker_conflicts, own_network_exists = docker_networks(subnet)
    if own_network_exists:
        routes = [route for route in routes if route != subnet]
    conflicts = routes + docker_conflicts
    overlapping = [network for network in conflicts if network.version == subnet.version and network.overlaps(subnet)]
    if overlapping:
        detail = ", ".join(str(network) for network in sorted(set(overlapping), key=str))
        raise RuntimeError(f"JUPYTER_USER_SUBNET {subnet} overlaps local route or Docker network(s): {detail}")


def main() -> None:
    subnet = os.environ.get("JUPYTER_USER_SUBNET", "172.30.240.0/24")
    hub_ip = os.environ.get("JUPYTERHUB_BROKER_BIND_IP", "172.30.240.2")
    try:
        check(subnet, hub_ip)
    except (ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(f"Jupyter user subnet preflight passed for {subnet}.")


if __name__ == "__main__":
    main()
