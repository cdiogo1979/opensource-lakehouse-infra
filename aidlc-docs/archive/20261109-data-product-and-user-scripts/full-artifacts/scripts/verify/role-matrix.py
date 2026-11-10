#!/usr/bin/env python3
"""Test a data product's effective access with temporary Keycloak service users.

  scripts/verify/role-matrix.py [--product NAME]     (default: default)

Expected read and write access per role comes from data-products/NAME.yaml;
every role is also checked to be refused in every other product's namespaces.
For a product without smoke tables, the temporary writer creates them first.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra" / "products"))
import data_products  # noqa: E402

REALM = "lakehouse"
ROLES = ("developer", "analyst", "owner", "writer")
KEYCLOAK_BASE = "http://127.0.0.1:8080"
POLARIS_BASE = "http://127.0.0.1:8181"
CLIENTS_FILE = ROOT / ".runtime" / "container-mounts" / "role-matrix-clients.json"
SPARK_IMAGE = "local/lakehouse-spark-runtime:3.5.5_1.10.2"


class CheckError(Exception):
    pass


class Api:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.token: str | None = None

    def call(self, method: str, path: str, payload: object | None = None, *, query: dict | None = None):
        url = self.base + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            return error.code, None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            raise CheckError(f"Provider request failed ({type(error).__name__}).") from None


def product_spec(product, every: list) -> dict:
    """The Spark verifier's view of the product under test (see verify_role_matrix.apply_spec)."""
    levels = product.access
    return {
        "product": {env.catalog: [env.namespace, env.key, env.bucket] for env in product.environments},
        "readable": {role: [e for e in data_products.ENVIRONMENTS if levels[role][e] != "none"] for role in ROLES},
        "writable": {role: [e for e in data_products.ENVIRONMENTS if levels[role][e] in ("write", "manage")] for role in ROLES},
        "foreign": [
            [env.catalog, env.namespace, env.key]
            for other in every if other.name != product.name
            for env in other.environments
        ],
    }


def verify_role_claim(credentials: dict, role: str, group: str) -> None:
    form = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": credentials["client_id"],
        "client_secret": credentials["client_secret"],
    }).encode()
    request = urllib.request.Request(
        f"{KEYCLOAK_BASE}/realms/{REALM}/protocol/openid-connect/token",
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            token = json.loads(response.read())["access_token"]
        parts = token.split(".")
        payload = parts[1] + ("=" * (-len(parts[1]) % 4))
        claims = json.loads(base64.urlsafe_b64decode(payload.encode()))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, IndexError) as error:
        raise CheckError(f"Temporary {role} token could not be inspected ({type(error).__name__}).") from None
    username = claims.get("preferred_username")
    roles = claims.get("resource_access", {}).get("polaris", {}).get("roles", [])
    if not isinstance(username, str) or not username.startswith("service-account-rm-") or group not in roles:
        raise CheckError(f"Temporary {role} identity did not receive its expected Keycloak role claim.")


def verify_polaris_role(polaris: Api, client_id: str, role: str, group: str) -> None:
    principal = f"service-account-{client_id}"
    encoded = urllib.parse.quote(principal, safe="")
    status, body = polaris.call("GET", f"/api/management/v1/principals/{encoded}/principal-roles")
    require(status, (200,), f"Read temporary {role} Polaris role assignment")
    role_items = (body.get("roles") or body.get("principalRoles") or []) if isinstance(body, dict) else []
    if not any(item.get("name") == group for item in role_items if isinstance(item, dict)):
        raise CheckError(f"Polaris did not assign the expected role to the temporary {role} principal.")
    print(f"ROLE_MATRIX_POLARIS: {role} principal role verified.")


def require(status: int, accepted: tuple[int, ...], action: str) -> None:
    if status not in accepted:
        raise CheckError(f"{action} failed with HTTP {status}.")


def read_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise CheckError("A required protected credential is unavailable.")
    value = path.read_text(encoding="utf-8").splitlines()
    if not value or not value[0]:
        raise CheckError("A required protected credential is empty.")
    return value[0]


def keycloak_admin() -> Api:
    api = Api(KEYCLOAK_BASE)
    body = urllib.parse.urlencode({
        "grant_type": "password",
        "client_id": "admin-cli",
        "username": os.environ.get("KEYCLOAK_ADMIN_USERNAME", "admin"),
        "password": read_file(ROOT / ".runtime/credentials/keycloak-admin-password"),
    }).encode()
    request = urllib.request.Request(
        f"{KEYCLOAK_BASE}/realms/master/protocol/openid-connect/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            api.token = json.loads(response.read())["access_token"]
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as error:
        raise CheckError(f"Keycloak administrator authentication failed ({type(error).__name__}).") from None
    return api


def polaris_admin() -> Api:
    api = Api(POLARIS_BASE)
    path = ROOT / ".runtime/credentials/polaris-bootstrap-credentials"
    if path.is_symlink() or not path.is_file():
        raise CheckError("Protected Polaris bootstrap credentials are unavailable.")
    try:
        entry = json.loads(path.read_text(encoding="utf-8"))[REALM]
        client_id, secret = entry["client-id"], entry["client-secret"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise CheckError("Protected Polaris bootstrap credentials are invalid.") from None
    form = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": "PRINCIPAL_ROLE:ALL"}).encode()
    basic = base64.b64encode(f"{client_id}:{secret}".encode()).decode("ascii")
    request = urllib.request.Request(
        f"{POLARIS_BASE}/api/catalog/v1/oauth/tokens",
        data=form,
        headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded", "Polaris-Realm": REALM},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            api.token = json.loads(response.read())["access_token"]
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as error:
        raise CheckError(f"Polaris bootstrap authentication failed ({type(error).__name__}).") from None
    return api


def exact_items(api: Api, path: str, query_key: str, query_value: str, name_key: str = "name") -> list[dict]:
    status, items = api.call("GET", path, query={query_key: query_value})
    require(status, (200,), "Read provider objects")
    return [item for item in (items or []) if item.get(name_key) == query_value]


def create_test_client(
    api: Api,
    client_id: str,
    role: str,
    group_id: str,
    polaris_id: str,
    created: list[tuple[str, str]],
) -> dict:
    secret = secrets.token_urlsafe(48)
    representation = {
        "clientId": client_id,
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "bearerOnly": False,
        "standardFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": True,
        "fullScopeAllowed": True,
        "clientAuthenticatorType": "client-secret",
        "secret": secret,
    }
    status, _ = api.call("POST", f"/admin/realms/{REALM}/clients", representation)
    require(status, (201,), f"Create temporary {role} client")
    matches = exact_items(api, f"/admin/realms/{REALM}/clients", "clientId", client_id, "clientId")
    require(len(matches), (1,), f"Find temporary {role} client")
    client_uuid = matches[0]["id"]
    created.append((client_uuid, client_id))

    status, service_account = api.call("GET", f"/admin/realms/{REALM}/clients/{client_uuid}/service-account-user")
    require(status, (200,), f"Read temporary {role} service identity")
    status, _ = api.call("PUT", f"/admin/realms/{REALM}/users/{service_account['id']}/groups/{group_id}")
    require(status, (204,), f"Assign temporary {role} identity to product group")

    mapper = {
        "name": "temporary-polaris-role-matrix",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-client-role-mapper",
        "consentRequired": False,
        "config": {
            "usermodel.clientRoleMapping.clientId": "polaris",
            "claim.name": "resource_access.polaris.roles",
            "jsonType.label": "String",
            "multivalued": "true",
            "access.token.claim": "true",
            "id.token.claim": "false",
            "userinfo.token.claim": "false",
        },
    }
    status, _ = api.call("POST", f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models", mapper)
    require(status, (201,), f"Add temporary {role} role claim mapper")
    return {"client_id": client_id, "client_secret": secret}


def run_reconcile() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "infra/polaris/reconcile-keycloak-groups.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode:
        raise CheckError("Keycloak-to-Polaris membership reconciliation failed.")


def run_spark(mode: str, role: str = "") -> list[str]:
    command = [
        "docker", "run", "--rm", "--network", "lakehouse-local_core",
        "--env", f"ROLE_MATRIX_MODE={mode}",
        "--env", f"ROLE_MATRIX_ROLE={role}",
        "--mount", f"type=bind,src={CLIENTS_FILE},dst=/run/secrets/role-matrix-clients.json,readonly",
        "--mount", f"type=bind,src={ROOT / 'infra/spark-bootstrap/verify_role_matrix.py'},dst=/opt/lakehouse/verify_role_matrix.py,readonly",
        "--entrypoint", "/opt/spark/bin/spark-submit", SPARK_IMAGE,
        "/opt/lakehouse/verify_role_matrix.py",
    ]
    result = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True, timeout=900)
    safe_prefixes = ("ROLE_MATRIX_FAILURE:", "ROLE_MATRIX_RESULT:", "ROLE_MATRIX_CLEANUP:")
    safe_lines = [line for line in (result.stdout + "\n" + result.stderr).splitlines() if line.startswith(safe_prefixes)]
    if result.returncode and not any(line.startswith("ROLE_MATRIX_FAILURE:") for line in safe_lines):
        safe_lines.append(f"ROLE_MATRIX_FAILURE: {mode}/{role} exited with status {result.returncode}; diagnostic unavailable")
    for line in safe_lines:
        print(line)
    return safe_lines


def cleanup(api: Api, polaris: Api, created: list[tuple[str, str]], prefix: str) -> None:
    problems = []
    clients_to_remove = {client_uuid: client_id for client_uuid, client_id in created}
    for role in ROLES:
        client_id = f"{prefix}-{role}"
        try:
            matches = exact_items(api, f"/admin/realms/{REALM}/clients", "clientId", client_id, "clientId")
        except CheckError:
            problems.append(f"could not inspect temporary Keycloak client {client_id}")
            continue
        for client in matches:
            clients_to_remove[client["id"]] = client_id
    for client_uuid, client_id in reversed(list(clients_to_remove.items())):
        status, _ = api.call("DELETE", f"/admin/realms/{REALM}/clients/{client_uuid}")
        if status not in (204, 404):
            problems.append(f"could not remove temporary Keycloak client {client_id}")
    if created:
        try:
            run_reconcile()
        except CheckError:
            problems.append("could not reconcile temporary Polaris assignments away")
    for role in ROLES:
        principal_name = f"service-account-{prefix}-{role}"
        status, _ = polaris.call("DELETE", f"/api/management/v1/principals/{urllib.parse.quote(principal_name, safe='')}")
        if status not in (204, 404):
            problems.append(f"could not remove temporary Polaris principal for {role}")
    try:
        CLIENTS_FILE.unlink(missing_ok=True)
    except OSError:
        problems.append("could not remove temporary role credential file")
    if problems:
        raise CheckError("Temporary identity cleanup incomplete: " + "; ".join(problems))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--product", default=data_products.DEFAULT_PRODUCT)
    args = parser.parse_args(argv)
    try:
        every = data_products.load_all()
        product = data_products.load_product(data_products.product_file(args.product))
    except data_products.ProductError as error:
        print(f"Role-matrix verification refused: {error}", file=sys.stderr)
        return 2
    prefix = f"rm-{uuid.uuid4().hex[:12]}"
    keycloak = keycloak_admin()
    polaris = polaris_admin()
    created: list[tuple[str, str]] = []
    identities: dict[str, dict] = {}
    exit_code = 0
    try:
        polaris_clients = exact_items(keycloak, f"/admin/realms/{REALM}/clients", "clientId", "polaris", "clientId")
        require(len(polaris_clients), (1,), "Find Polaris role-claim client")
        polaris_id = polaris_clients[0]["id"]
        for role in ROLES:
            group_name = product.groups[role]
            groups = exact_items(keycloak, f"/admin/realms/{REALM}/groups", "search", group_name)
            require(len(groups), (1,), f"Find {role} group")
            client_id = f"{prefix}-{role}"
            credentials = create_test_client(keycloak, client_id, role, groups[0]["id"], polaris_id, created)
            identities[role] = credentials
            verify_role_claim(credentials, role, group_name)
            print(f"ROLE_MATRIX_IDENTITY: {role} role claim verified.")
        identities["probe_id_base"] = int(time.time() * 1000) * 100
        identities["spec"] = product_spec(product, every)
        CLIENTS_FILE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        CLIENTS_FILE.write_text(json.dumps(identities), encoding="utf-8")
        CLIENTS_FILE.chmod(0o600)
        run_reconcile()
        for role in ROLES:
            verify_polaris_role(polaris, identities[role]["client_id"], role, product.groups[role])
        if not product.protected:
            lines = run_spark("setup")
            if any(line.startswith("ROLE_MATRIX_FAILURE:") for line in lines):
                raise CheckError("The product's smoke tables could not be prepared.")
        for role in ROLES:
            try:
                lines = run_spark("test", role)
                if any(line.startswith("ROLE_MATRIX_FAILURE:") for line in lines):
                    exit_code = 1
            except (CheckError, subprocess.TimeoutExpired) as error:
                print(f"Role-matrix verification failed for {role}: {type(error).__name__}.", file=sys.stderr)
                exit_code = 1
    except (CheckError, OSError, KeyError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"Role-matrix verification failed: {error}", file=sys.stderr)
        exit_code = 1

    # Run cleanup while the temporary writer identity still exists, even if a role check failed.
    if CLIENTS_FILE.is_file() and not CLIENTS_FILE.is_symlink():
        try:
            cleanup_lines = run_spark("cleanup")
            if any(line.startswith("ROLE_MATRIX_FAILURE:") for line in cleanup_lines):
                exit_code = 1
            else:
                print("Temporary probe rows removed; smoke tables restored to their original single rows.")
        except (CheckError, subprocess.TimeoutExpired) as error:
            print(f"WARNING: probe-row cleanup could not be confirmed ({type(error).__name__}).", file=sys.stderr)
            exit_code = 1
    try:
        cleanup(keycloak, polaris, created, prefix)
        print("Temporary identity cleanup completed.")
    except CheckError as error:
        print(f"WARNING: {error}", file=sys.stderr)
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
