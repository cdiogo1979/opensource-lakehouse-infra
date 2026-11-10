#!/usr/bin/env python3
"""Reject FreeIPA validation subnets that overlap an existing Docker network."""

from __future__ import annotations

import ipaddress
import json
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: check-network.py SUBNET SERVER_IP NETWORK_NAME", file=sys.stderr)
        return 2

    requested = ipaddress.ip_network(sys.argv[1], strict=True)
    server_ip = ipaddress.ip_address(sys.argv[2])
    network_name = sys.argv[3]
    if server_ip not in requested or server_ip in {requested.network_address, requested.broadcast_address}:
        print("FreeIPA validation IP must be a usable address in the configured subnet.", file=sys.stderr)
        return 2

    try:
        names = subprocess.run(
            ["docker", "network", "ls", "--format", "{{.Name}}"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        print("Unable to inspect Docker networks; FreeIPA validation startup is blocked.", file=sys.stderr)
        return 1

    for name in names:
        if name == network_name:
            continue
        try:
            raw = subprocess.run(
                ["docker", "network", "inspect", name],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            ).stdout
            inspected = json.loads(raw)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            print(f"Unable to inspect Docker network {name!r}; startup is blocked.", file=sys.stderr)
            return 1

        for item in inspected:
            for config in item.get("IPAM", {}).get("Config") or []:
                subnet = config.get("Subnet")
                if not subnet:
                    continue
                try:
                    existing = ipaddress.ip_network(subnet, strict=False)
                except ValueError:
                    print(f"Docker network {name!r} reports an invalid subnet; startup is blocked.", file=sys.stderr)
                    return 1
                if requested.version == existing.version and requested.overlaps(existing):
                    print(
                        f"FreeIPA validation subnet overlaps Docker network {name!r}; configure a different subnet.",
                        file=sys.stderr,
                    )
                    return 1

    print("FreeIPA validation subnet does not overlap an existing Docker network.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
