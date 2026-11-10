#!/usr/bin/env python3
"""Read-only checks that RustFS console OIDC login is wired to Keycloak.

Run from the repository root against the running local stack. Prints one
PASS/FAIL line per check and never prints credentials or tokens.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
S3_ENDPOINT = os.environ.get("RUSTFS_S3_ENDPOINT", "http://127.0.0.1:9000")
KEYCLOAK_AUTHORIZE = "http://keycloak.localhost:8080/realms/lakehouse/protocol/openid-connect/auth"


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with opener.open(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read()


def check_provider_listed() -> None:
    status, _, body = fetch(f"{S3_ENDPOINT}/rustfs/admin/v3/oidc/providers")
    providers = json.loads(body) if status == 200 else []
    if not any(item.get("provider_id") == "default" for item in providers):
        raise AssertionError(f"provider 'default' not listed (HTTP {status})")


def check_authorize_redirect(host: str, port: int) -> str:
    status, headers, _ = fetch(f"http://{host}:{port}/rustfs/admin/v3/oidc/authorize/default")
    location = headers.get("Location") or headers.get("location") or ""
    if status != 302 or not location.startswith(KEYCLOAK_AUTHORIZE + "?"):
        raise AssertionError(f"authorize did not redirect to Keycloak (HTTP {status})")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)
    expected_callback = f"http://{host}:{port}/rustfs/admin/v3/oidc/callback/default"
    if query.get("client_id") != ["rustfs"]:
        raise AssertionError("authorize redirect uses an unexpected client_id")
    if query.get("redirect_uri") != [expected_callback]:
        raise AssertionError("authorize redirect uses an unexpected callback")
    if query.get("code_challenge_method") != ["S256"]:
        raise AssertionError("authorize redirect does not use PKCE S256")
    return location


def check_keycloak_accepts(location: str) -> None:
    keycloak_port = os.environ.get("KEYCLOAK_HOST_PORT", "8080")
    split = urllib.parse.urlsplit(location)
    url = urllib.parse.urlunsplit(("http", f"127.0.0.1:{keycloak_port}", split.path, split.query, ""))
    status, _, body = fetch(url, {"Host": "keycloak.localhost:8080"})
    if status != 200 or (b"invalid parameter: redirect_uri" in body.lower()):
        raise AssertionError(f"Keycloak rejected the authorize request (HTTP {status})")


def check_policies(policies, buckets) -> None:
    client = buckets.S3Client(S3_ENDPOINT, buckets.read_secret("rustfs-access-key"), buckets.read_secret("rustfs-secret-key"))
    for name, document in policies.policy_documents().items():
        status, body = client.request("GET", "/rustfs/admin/v3/info-canned-policy", {"name": name})
        if status != 200:
            raise AssertionError(f"policy {name} unavailable (HTTP {status})")
        response = json.loads(body)
        actual = response.get("policy", response)
        if isinstance(actual, str):
            actual = json.loads(actual)
        if policies.canonical_policy(actual) != policies.canonical_policy(document):
            raise AssertionError(f"policy {name} differs from its definition")


def check_secret_not_inspectable() -> None:
    container = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.yml", "ps", "-q", "rustfs"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    if not container:
        raise AssertionError("rustfs container is not running")
    environment = subprocess.run(
        ["docker", "inspect", "--format", "{{json .Config.Env}}", container],
        capture_output=True, text=True, check=True,
    ).stdout
    names = {entry.split("=", 1)[0] for entry in json.loads(environment)}
    if "RUSTFS_IDENTITY_OPENID_CLIENT_SECRET" in names:
        raise AssertionError("client secret is visible in the container configuration")


def main() -> int:
    realm = load("keycloak_bootstrap_realm", "infra/keycloak/bootstrap-realm.py")
    policies = load("rustfs_bootstrap_policies", "infra/rustfs/bootstrap-policies.py")
    buckets = load("rustfs_bootstrap_buckets", "infra/rustfs/bootstrap-buckets.py")
    port = realm.rustfs_console_port()
    locations: dict[str, str] = {}
    checks = [("OIDC provider listed", check_provider_listed)]
    for host in ("localhost", "127.0.0.1"):
        checks.append((f"authorize redirect via {host}:{port}",
                       lambda host=host: locations.__setitem__(host, check_authorize_redirect(host, port))))
        checks.append((f"Keycloak accepts callback for {host}:{port}",
                       lambda host=host: check_keycloak_accepts(locations[host])))
    checks.append(("product-group policies match definitions", lambda: check_policies(policies, buckets)))
    checks.append(("client secret absent from docker inspect", check_secret_not_inspectable))

    failures = 0
    for label, check in checks:
        try:
            check()
            print(f"PASS {label}")
        except Exception as error:  # report every check; never include secrets
            failures += 1
            print(f"FAIL {label}: {error}")
    print("RustFS OIDC verification " + ("passed." if not failures else f"failed ({failures} check(s))."))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
