#!/usr/bin/env python3
"""Exercise OIDC and reconciliation behavior during a local Keycloak outage."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REALM = "lakehouse"
KEYCLOAK = "http://127.0.0.1:8080"
POLARIS = "http://127.0.0.1:8181"


class CheckError(Exception):
    """Safe operator-facing error."""


def read_secret(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise CheckError("A protected credential required for the outage check is unavailable.")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0]:
        raise CheckError("A protected credential required for the outage check is empty.")
    return lines[0]


def writer_token() -> str:
    form = urllib.parse.urlencode({
        "grant_type": "password",
        "client_id": "lakehouse-writer",
        "client_secret": read_secret(ROOT / ".runtime/credentials/keycloak-writer-client-secret"),
        "username": "srv-default-writer",
        "password": read_secret(ROOT / ".runtime/credentials/srv-default-writer-password"),
        "scope": "openid",
    }).encode()
    req = urllib.request.Request(
        f"{KEYCLOAK}/realms/{REALM}/protocol/openid-connect/token",
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        token = json.loads(response.read()).get("access_token")
    if not isinstance(token, str) or not token:
        raise CheckError("Keycloak did not issue the writer test token.")
    return token


def main() -> int:
    stopped = False
    try:
        token = writer_token()
        stop = subprocess.run(
            ["docker", "compose", "-f", "compose.core.yml", "stop", "keycloak"], cwd=ROOT,
            check=False, capture_output=True, text=True, timeout=60,
        )
        if stop.returncode != 0:
            raise CheckError("Could not stop only the project Keycloak service for the outage test.")
        stopped = True

        try:
            urllib.request.urlopen(f"{KEYCLOAK}/realms/{REALM}", timeout=3)
            raise CheckError("Keycloak remained reachable after the stop operation.")
        except (urllib.error.URLError, TimeoutError, OSError):
            print("Outage check: Keycloak endpoint became unavailable.")

        try:
            writer_token()
            raise CheckError("Keycloak issued a new token while its service was stopped.")
        except (urllib.error.URLError, TimeoutError, OSError):
            print("Outage check: a new writer token could not be issued.")
        except urllib.error.HTTPError:
            print("Outage check: Keycloak token endpoint returned an error while the service was stopped.")

        principal = urllib.parse.quote("srv-default-writer", safe="")
        req = urllib.request.Request(
            f"{POLARIS}/api/management/v1/principals/{principal}",
            headers={"Authorization": f"Bearer {token}", "Polaris-Realm": REALM, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                polaris_status = response.status
        except urllib.error.HTTPError as error:
            polaris_status = error.code
        if polaris_status == 403:
            print("Outage check: Polaris continued validating an already-issued writer token (expected management HTTP 403).")
        elif polaris_status == 401:
            print("Outage check: Polaris rejected the existing token while Keycloak was unavailable (HTTP 401).")
        else:
            raise CheckError(f"Polaris returned unexpected HTTP {polaris_status} for the existing writer token.")

        reconcile = subprocess.run(
            [sys.executable, "infra/polaris/reconcile-keycloak-groups.py"], cwd=ROOT,
            check=False, capture_output=True, text=True, timeout=60,
        )
        if reconcile.returncode == 0:
            raise CheckError("Membership reconciliation reported success while Keycloak was unavailable.")
        print("Outage check: membership reconciliation failed closed while Keycloak was unavailable.")
        return 0
    except (CheckError, OSError, KeyError, ValueError, urllib.error.URLError, TimeoutError, subprocess.TimeoutExpired) as error:
        print(f"Keycloak outage verification failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    finally:
        if stopped:
            start = subprocess.run(
                ["docker", "compose", "-f", "compose.core.yml", "start", "keycloak"], cwd=ROOT,
                check=False, capture_output=True, text=True, timeout=60,
            )
            if start.returncode != 0:
                print("CRITICAL: Keycloak did not restart successfully; run `docker compose -f compose.core.yml start keycloak` in the project.", file=sys.stderr)
            else:
                deadline = time.monotonic() + 150
                while time.monotonic() < deadline:
                    try:
                        with urllib.request.urlopen(f"{KEYCLOAK}/realms/{REALM}", timeout=3) as response:
                            if response.status == 200:
                                print("Outage check: Keycloak restarted and realm endpoint is reachable.")
                                break
                    except (urllib.error.URLError, TimeoutError, OSError):
                        time.sleep(3)
                else:
                    print("CRITICAL: Keycloak restart was issued but readiness was not confirmed within 150 seconds.", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
