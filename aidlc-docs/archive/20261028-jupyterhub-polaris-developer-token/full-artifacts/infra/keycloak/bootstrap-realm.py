#!/usr/bin/env python3
"""Explicit, additive bootstrap for the lakehouse Keycloak realm."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlsplit


ROLES = (
    "role-default-developer",
    "role-default-analyst",
    "role-default-owner",
    "role-default-writer",
)
REALM = "lakehouse"
CLIENTS = ("polaris", "lakehouse-cli", "write-service-account")
JUPYTERHUB_REDIRECT_URI = "http://jupyterhub.localhost:8000/hub/oauth_callback"


class BootstrapError(Exception):
    """Safe operator-facing failure; response bodies are deliberately omitted."""


class KeycloakAdmin:
    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token: str | None = None

    def request(self, method: str, path: str, payload: object | None = None, *, query: dict | None = None):
        url = f"{self.base}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read()
                return response.status, json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            return error.code, None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise BootstrapError(f"Keycloak request failed ({type(error).__name__}).") from error

    def login(self) -> None:
        form = urllib.parse.urlencode({
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": self.username,
            "password": self.password,
        }).encode()
        request = urllib.request.Request(
            f"{self.base}/realms/master/protocol/openid-connect/token",
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                self.token = json.loads(response.read())["access_token"]
        except urllib.error.HTTPError as error:
            raise BootstrapError(f"Could not authenticate to the Keycloak master realm (HTTP {error.code}).") from error
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as error:
            raise BootstrapError("Could not authenticate to the Keycloak master realm.") from error


def checked(status: int, expected: tuple[int, ...], action: str) -> None:
    if status not in expected:
        raise BootstrapError(f"{action} failed with HTTP {status}.")


def read_secret(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise BootstrapError("A required protected credential file is unavailable.")
    value = path.read_text(encoding="utf-8").splitlines()
    if not value or not value[0]:
        raise BootstrapError("A required protected credential file is empty.")
    return value[0]


def find_group(api: KeycloakAdmin, name: str) -> dict | None:
    status, items = api.request("GET", f"/admin/realms/{REALM}/groups", query={"search": name, "briefRepresentation": "true"})
    checked(status, (200,), "Group lookup")
    matches = [item for item in items or [] if item.get("name") == name]
    if len(matches) > 1:
        raise BootstrapError(f"Ambiguous Keycloak group {name!r}.")
    return matches[0] if matches else None


def ensure_group(api: KeycloakAdmin, name: str) -> dict:
    current = find_group(api, name)
    if current:
        return current
    status, _ = api.request("POST", f"/admin/realms/{REALM}/groups", {"name": name, "attributes": {}})
    checked(status, (201,), f"Create group {name}")
    current = find_group(api, name)
    if not current:
        raise BootstrapError(f"Created group {name!r} could not be read back.")
    return current


def find_client(api: KeycloakAdmin, client_id: str) -> dict | None:
    status, items = api.request("GET", f"/admin/realms/{REALM}/clients", query={"clientId": client_id})
    checked(status, (200,), f"Client lookup {client_id}")
    matches = [item for item in items or [] if item.get("clientId") == client_id]
    if len(matches) > 1:
        raise BootstrapError(f"Ambiguous Keycloak client {client_id!r}.")
    return matches[0] if matches else None


def ensure_client(api: KeycloakAdmin, representation: dict) -> dict:
    client_id = representation["clientId"]
    current = find_client(api, client_id)
    if current:
        update_client = False
        for key in ("publicClient", "standardFlowEnabled", "serviceAccountsEnabled", "protocol"):
            if current.get(key, False if key != "protocol" else "openid-connect") != representation.get(key, False if key != "protocol" else "openid-connect"):
                raise BootstrapError(f"Existing client {client_id!r} conflicts on {key}; no changes applied.")
        for key in ("redirectUris", "webOrigins"):
            if key in representation and set(current.get(key) or []) != set(representation[key]):
                if client_id == "lakehouse-cli" and not (current.get(key) or []) and representation[key]:
                    current[key] = representation[key]
                    update_client = True
                elif client_id == "jupyterhub" and _is_local_jupyter_callback_change(
                    key, current.get(key) or [], representation[key]
                ):
                    current[key] = representation[key]
                    update_client = True
                else:
                    raise BootstrapError(f"Existing client {client_id!r} conflicts on {key}; no changes applied.")
        for key, value in representation.get("attributes", {}).items():
            if (current.get("attributes") or {}).get(key) != value:
                raise BootstrapError(f"Existing client {client_id!r} conflicts on {key}; no changes applied.")
        if "secret" in representation:
            status, current_secret = api.request("GET", f"/admin/realms/{REALM}/clients/{current['id']}/client-secret")
            checked(status, (200,), f"Verify client secret for {client_id}")
            if not isinstance(current_secret, dict) or current_secret.get("value") != representation["secret"]:
                raise BootstrapError(f"Existing client {client_id!r} does not match its protected secret file; no changes applied.")
        if update_client:
            status, _ = api.request("PUT", f"/admin/realms/{REALM}/clients/{current['id']}", current)
            checked(status, (204,), f"Set exact callback for {client_id}")
        return current
    status, _ = api.request("POST", f"/admin/realms/{REALM}/clients", representation)
    checked(status, (201,), f"Create client {client_id}")
    current = find_client(api, client_id)
    if not current:
        raise BootstrapError(f"Created client {client_id!r} could not be read back.")
    return current


def _is_local_jupyter_callback_change(key: str, current: list[str], desired: list[str]) -> bool:
    if len(current) != 1 or len(desired) != 1:
        return False
    old, new = urlsplit(current[0]), urlsplit(desired[0])
    expected_path = "/hub/oauth_callback" if key == "redirectUris" else ""
    return (
        old.scheme == new.scheme == "http"
        and old.hostname == new.hostname == "jupyterhub.localhost"
        and old.path == new.path == expected_path
        and not old.username
        and not old.password
        and not old.query
        and not old.fragment
        and not new.username
        and not new.password
        and not new.query
        and not new.fragment
    )


def jupyterhub_client_configuration(
    secret: str, redirect_uri: str = JUPYTERHUB_REDIRECT_URI
) -> dict:
    return {
        "clientId": "jupyterhub",
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False,
        "clientAuthenticatorType": "client-secret",
        "attributes": {"pkce.code.challenge.method": "S256"},
        "secret": secret,
        "redirectUris": [redirect_uri],
        "webOrigins": [redirect_uri.rsplit("/hub/oauth_callback", 1)[0]],
    }


def ensure_mapper(api: KeycloakAdmin, client_uuid: str, polaris_client_uuid: str) -> None:
    path = f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models"
    status, mappers = api.request("GET", path)
    checked(status, (200,), "Protocol mapper lookup")
    id_mapper_name = "lakehouse-polaris-principal-id"
    for mapper in mappers or []:
        if mapper.get("name") == id_mapper_name:
            status, _ = api.request("DELETE", f"{path}/{mapper['id']}")
            checked(status, (204,), "Remove obsolete Polaris ID mapper")
            break
    status, mappers = api.request("GET", path)
    checked(status, (200,), "Protocol mapper lookup")
    name = "lakehouse-polaris-roles"
    desired = {
        "name": name,
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
    existing = [item for item in mappers or [] if item.get("name") == name]
    if existing:
        actual_config = existing[0].get("config") or {}
        if existing[0].get("protocolMapper") != desired["protocolMapper"] or any(
            actual_config.get(key) != value for key, value in desired["config"].items()
        ):
            raise BootstrapError("An existing Polaris role mapper conflicts; no changes applied.")
    else:
        status, _ = api.request("POST", path, desired)
        checked(status, (201,), "Create Polaris role mapper")
    status, mappers = api.request("GET", path)
    checked(status, (200,), "Protocol mapper lookup")
def ensure_jupyterhub_group_mapper(api: KeycloakAdmin, client_uuid: str) -> None:
    path = f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models"
    status, mappers = api.request("GET", path)
    checked(status, (200,), "JupyterHub mapper lookup")
    desired = {
        "name": "lakehouse-jupyterhub-groups",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-group-membership-mapper",
        "consentRequired": False,
        "config": {
            "claim.name": "groups",
            "full.path": "false",
            "id.token.claim": "false",
            "access.token.claim": "true",
            "userinfo.token.claim": "true",
        },
    }
    existing = [item for item in mappers or [] if item.get("name") == desired["name"]]
    if existing:
        mapper = existing[0]
        if mapper.get("protocolMapper") != desired["protocolMapper"] or any(
            (mapper.get("config") or {}).get(key) != value
            for key, value in desired["config"].items()
        ):
            raise BootstrapError("An existing JupyterHub group mapper conflicts; no changes applied.")
        return
    status, _ = api.request("POST", path, desired)
    checked(status, (201,), "Create JupyterHub group mapper")


def ensure_role(api: KeycloakAdmin, polaris_uuid: str, role_name: str) -> dict:
    path = f"/admin/realms/{REALM}/clients/{polaris_uuid}/roles"
    status, roles = api.request("GET", path)
    checked(status, (200,), "Polaris client-role lookup")
    matches = [role for role in roles or [] if role.get("name") == role_name]
    if len(matches) > 1:
        raise BootstrapError(f"Ambiguous client role {role_name!r}.")
    if matches:
        return matches[0]
    status, _ = api.request("POST", path, {"name": role_name, "description": "Lakehouse product entitlement"})
    checked(status, (201,), f"Create client role {role_name}")
    status, role = api.request("GET", f"{path}/{urllib.parse.quote(role_name, safe='')}")
    checked(status, (200,), f"Verify client role {role_name}")
    return role


def add_client_role_to_group(api: KeycloakAdmin, group_id: str, polaris_uuid: str, role: dict) -> None:
    path = f"/admin/realms/{REALM}/groups/{group_id}/role-mappings/clients/{polaris_uuid}"
    status, current = api.request("GET", path)
    checked(status, (200,), "Group role lookup")
    if any(item.get("id") == role.get("id") for item in current or []):
        return
    status, _ = api.request("POST", path, [role])
    checked(status, (204,), "Assign product role to group")


def find_user(api: KeycloakAdmin, username: str) -> dict | None:
    status, users = api.request("GET", f"/admin/realms/{REALM}/users", query={"username": username, "exact": "true"})
    checked(status, (200,), "User lookup")
    matches = [item for item in users or [] if item.get("username") == username]
    if len(matches) > 1:
        raise BootstrapError(f"Expected one Keycloak user named {username!r}; found {len(matches)}.")
    return matches[0] if matches else None


def ensure_owner_user(api: KeycloakAdmin, username: str, password: str) -> dict:
    current = find_user(api, username)
    if current:
        return current
    status, _ = api.request("POST", f"/admin/realms/{REALM}/users", {
        "username": username,
        "enabled": True,
        "emailVerified": False,
        "requiredActions": ["UPDATE_PASSWORD"],
        "credentials": [{"type": "password", "value": password, "temporary": True}],
    })
    checked(status, (201, 409), "Create initial platform-admin identity")
    current = find_user(api, username)
    if not current:
        raise BootstrapError("Initial platform-admin identity could not be read back.")
    return current


def add_user_to_group(api: KeycloakAdmin, user_id: str, group: dict) -> None:
    status, memberships = api.request("GET", f"/admin/realms/{REALM}/users/{user_id}/groups")
    checked(status, (200,), "User group lookup")
    if any(item.get("id") == group.get("id") for item in memberships or []):
        return
    status, _ = api.request("PUT", f"/admin/realms/{REALM}/users/{user_id}/groups/{group['id']}")
    checked(status, (204,), "Add user to product group")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-username", help="Existing lakehouse-realm username to receive product-owner membership")
    parser.add_argument("--owner-password-file", type=Path, default=Path(".runtime/credentials/platform-admin-password"))
    parser.add_argument("--redirect-uri", help="Exact local OAuth callback URI for the human PKCE client")
    parser.add_argument("--admin-password-file", type=Path, default=Path(".runtime/credentials/keycloak-admin-password"))
    parser.add_argument("--writer-secret-file", type=Path, default=Path(".runtime/credentials/keycloak-writer-client-secret"))
    parser.add_argument("--jupyterhub-secret-file", type=Path, default=Path(".runtime/credentials/jupyterhub-oidc-client-secret"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    args = parser.parse_args()
    callback_origin = None
    if args.redirect_uri:
        callback = urlsplit(args.redirect_uri)
        if callback.scheme != "http" or callback.hostname not in {"localhost", "127.0.0.1"} or not callback.path or callback.username or callback.password or callback.fragment or "*" in args.redirect_uri:
            parser.error("--redirect-uri must be an exact http://localhost or http://127.0.0.1 callback URL without wildcard or fragment")
        callback_origin = f"{callback.scheme}://{callback.netloc}"
    operation_id = str(uuid.uuid4())
    try:
        password = read_secret(args.admin_password_file)
        writer_secret = read_secret(args.writer_secret_file)
        jupyterhub_secret = read_secret(args.jupyterhub_secret_file)
        api = KeycloakAdmin(args.base_url, os.environ.get("KEYCLOAK_ADMIN_USERNAME", "admin"), password)
        api.login()
        realm_payload = {"realm": REALM, "enabled": True, "sslRequired": "none"}
        status, _ = api.request("POST", "/admin/realms", realm_payload)
        if status == 409:
            status, existing = api.request("GET", f"/admin/realms/{REALM}")
            checked(status, (200,), "Verify existing realm")
            if existing.get("enabled") is not True:
                raise BootstrapError("Existing lakehouse realm is disabled; no changes applied.")
        else:
            checked(status, (201,), "Create lakehouse realm")

        polaris = ensure_client(api, {"clientId": "polaris", "enabled": True, "protocol": "openid-connect", "publicClient": False, "bearerOnly": False, "standardFlowEnabled": False, "directAccessGrantsEnabled": False, "serviceAccountsEnabled": False})
        human = ensure_client(api, {"clientId": "lakehouse-cli", "enabled": True, "protocol": "openid-connect", "publicClient": True, "standardFlowEnabled": True, "directAccessGrantsEnabled": False, "serviceAccountsEnabled": False, "redirectUris": [args.redirect_uri] if args.redirect_uri else [], "webOrigins": [callback_origin] if callback_origin else [], "attributes": {"pkce.code.challenge.method": "S256", "access.token.lifespan": "300"}})
        writer = ensure_client(api, {"clientId": "write-service-account", "enabled": True, "protocol": "openid-connect", "publicClient": False, "standardFlowEnabled": False, "directAccessGrantsEnabled": False, "serviceAccountsEnabled": True, "clientAuthenticatorType": "client-secret", "secret": writer_secret})
        hub_port = os.environ.get("JUPYTERHUB_HOST_PORT", "8000")
        if not hub_port.isdecimal() or not (1 <= int(hub_port) <= 65535):
            raise BootstrapError("JUPYTERHUB_HOST_PORT must be a valid TCP port.")
        hub_callback = f"http://jupyterhub.localhost:{hub_port}/hub/oauth_callback"
        jupyterhub = ensure_client(api, jupyterhub_client_configuration(jupyterhub_secret, hub_callback))
        ensure_mapper(api, human["id"], polaris["id"])
        ensure_mapper(api, writer["id"], polaris["id"])
        ensure_mapper(api, jupyterhub["id"], polaris["id"])
        ensure_jupyterhub_group_mapper(api, jupyterhub["id"])

        groups = {role: ensure_group(api, role) for role in ROLES}
        roles = {role: ensure_role(api, polaris["id"], role) for role in ROLES}
        for role in ROLES:
            add_client_role_to_group(api, groups[role]["id"], polaris["id"], roles[role])
        owner_username = args.owner_username or "platform-admin"
        owner_password = read_secret(args.owner_password_file)
        owner = ensure_owner_user(api, owner_username, owner_password)
        add_user_to_group(api, owner["id"], groups["role-default-owner"])
        status, service_user = api.request("GET", f"/admin/realms/{REALM}/clients/{writer['id']}/service-account-user")
        checked(status, (200,), "Writer service-account lookup")
        add_user_to_group(api, service_user["id"], groups["role-default-writer"])
        owner_state = f"owner={owner_username}"
        callback_state = "callback=configured" if args.redirect_uri else "callback=not-configured"
        print(f"Keycloak realm bootstrap verified (operation_id={operation_id}; {owner_state}; {callback_state}; groups={len(groups)}).")
        return 0
    except BootstrapError as error:
        print(f"Keycloak bootstrap failed (operation_id={operation_id}): {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
