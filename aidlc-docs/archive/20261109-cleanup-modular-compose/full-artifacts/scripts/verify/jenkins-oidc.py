#!/usr/bin/env python3
"""Read-only checks that the v2 Jenkins is migrated, pinned, and wired to Keycloak.

Run from the repository root against the running stack. Prints one PASS/FAIL
line per check and never prints credentials.
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


ROOT = Path(__file__).resolve().parents[2]
KEYCLOAK_AUTHORIZE = "http://keycloak.localhost:8080/realms/lakehouse/protocol/openid-connect/auth"
JOB = "jobs/opensource-lakehouse-dp/jobs/opensource-lakehouse-ci/config.xml"


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
    try:
        with opener.open(urllib.request.Request(url, headers=headers or {}), timeout=15) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read()


def container() -> str:
    cid = subprocess.run(["docker", "compose", "-f", "compose.core.yml", "-f", "compose.jenkins.yml", "ps", "-q", "jenkins"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    if not cid:
        raise AssertionError("jenkins container is not running")
    return cid


def in_container(script: str) -> str:
    return subprocess.run(["docker", "exec", container(), "sh", "-c", script],
                          capture_output=True, text=True, check=True).stdout


def check_healthy() -> None:
    state = subprocess.run(["docker", "inspect", "--format", "{{.State.Health.Status}}", container()],
                           capture_output=True, text=True, check=True).stdout.strip()
    if state != "healthy":
        raise AssertionError(f"jenkins is {state}")


def check_anonymous_denied(port: int) -> None:
    status, headers, _ = fetch(f"http://127.0.0.1:{port}/api/json")
    if status not in (401, 403):
        raise AssertionError(f"anonymous API access returned HTTP {status}")


def check_login_redirect(host: str, port: int) -> str:
    status, headers, _ = fetch(f"http://{host}:{port}/securityRealm/commenceLogin?from=%2F")
    location = headers.get("Location") or headers.get("location") or ""
    if status != 302 or not location.startswith(KEYCLOAK_AUTHORIZE + "?"):
        raise AssertionError(f"login did not redirect to Keycloak (HTTP {status})")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)
    if query.get("client_id") != ["jenkins"]:
        raise AssertionError("unexpected client_id")
    if query.get("redirect_uri") != [f"http://{host}:{port}/securityRealm/finishLogin"]:
        raise AssertionError("unexpected callback")
    if query.get("code_challenge_method") != ["S256"]:
        raise AssertionError("PKCE S256 is not used")
    return location


def check_keycloak_accepts(location: str) -> None:
    split = urllib.parse.urlsplit(location)
    url = urllib.parse.urlunsplit(("http", f"127.0.0.1:{os.environ.get('KEYCLOAK_HOST_PORT', '8080')}", split.path, split.query, ""))
    status, _, body = fetch(url, {"Host": "keycloak.localhost:8080"})
    if status != 200 or b"invalid parameter: redirect_uri" in body.lower():
        raise AssertionError(f"Keycloak rejected the authorize request (HTTP {status})")


def check_plugins_match() -> None:
    expected = {}
    for line in (ROOT / "infra/jenkins/plugins.txt").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            name, version = line.split(":", 1)
            expected[name] = version
    output = in_container(
        'cd /var/jenkins_home/plugins && for d in */; do n=${d%/}; '
        'printf "%s:%s\\n" "$n" "$(grep -m1 "^Plugin-Version:" "$d/META-INF/MANIFEST.MF" | cut -d" " -f2 | tr -d "\\r")"; done')
    actual = dict(line.split(":", 1) for line in output.split())
    if actual != expected:
        diff = sorted(set(actual.items()) ^ set(expected.items()))[:5]
        raise AssertionError(f"running plugins differ from plugins.txt (e.g. {diff})")


def check_realm_and_job() -> None:
    config = in_container("cat /var/jenkins_home/config.xml")
    if "org.jenkinsci.plugins.oic.OicSecurityRealm" not in config:
        raise AssertionError("security realm is not OIDC")
    if "GlobalMatrixAuthorizationStrategy" not in config:
        raise AssertionError("authorization strategy is not the global matrix")
    if "opensource-lakehouse" not in in_container(f"cat /var/jenkins_home/{JOB} 2>/dev/null || true"):
        raise AssertionError("workload CI job is missing")


def check_secret_not_inspectable() -> None:
    environment = subprocess.run(["docker", "inspect", "--format", "{{json .Config.Env}}", container()],
                                 capture_output=True, text=True, check=True).stdout
    secrets = [(ROOT / ".runtime/credentials" / name).read_text(encoding="utf-8").strip()
               for name in ("jenkins-oidc-client-secret", "jenkins-break-glass-password")]
    if any(secret and secret in environment for secret in secrets):
        raise AssertionError("a Jenkins secret is visible in the container configuration")
    if any(entry.split("=", 1)[0] in ("JENKINS_OIDC_CLIENT_SECRET", "CLIENT_SECRET") for entry in json.loads(environment)):
        raise AssertionError("a client-secret variable is set on the container")


def main() -> int:
    port = load("keycloak_bootstrap_realm", "infra/keycloak/bootstrap-realm.py").jenkins_port()
    locations: dict[str, str] = {}
    checks = [("jenkins healthy", check_healthy), ("anonymous access denied", lambda: check_anonymous_denied(port))]
    for host in ("localhost", "127.0.0.1"):
        checks.append((f"login redirect via {host}:{port}",
                       lambda host=host: locations.__setitem__(host, check_login_redirect(host, port))))
        checks.append((f"Keycloak accepts callback for {host}:{port}",
                       lambda host=host: check_keycloak_accepts(locations[host])))
    checks += [
        ("running plugins equal plugins.txt", check_plugins_match),
        ("OIDC realm, matrix, and workload CI job", check_realm_and_job),
        ("secrets absent from docker inspect", check_secret_not_inspectable),
    ]
    failures = 0
    for label, check in checks:
        try:
            check()
            print(f"PASS {label}")
        except Exception as error:  # report every check; never include secrets
            failures += 1
            print(f"FAIL {label}: {error}")
    print("Jenkins OIDC verification " + ("passed." if not failures else f"failed ({failures} check(s))."))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
