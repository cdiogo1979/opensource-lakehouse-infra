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
CLIENTS = ("polaris", "lakehouse-cli", "lakehouse-writer", "srv-starrocks", "starrocks")
# Each realm group carries one Polaris product role; the platform administrator
# is owner-equivalent rather than a separate Polaris role.
GROUP_PRODUCT_ROLES = {role: role for role in ROLES} | {"role-platform-admin": "role-default-owner"}
BOOTSTRAP_USERS_FILE = Path(__file__).with_name("bootstrap-users.json")
# The platform administrator also administers this realm (not the master realm).
REALM_ADMIN_GROUP = "role-platform-admin"
REALM_MANAGEMENT_CLIENT_ID = "realm-management"
REALM_ADMIN_ROLE = "realm-admin"
WRITER_CLIENT_ID = "lakehouse-writer"
# StarRocks reaches Polaris as this service account; people log in to StarRocks
# with tokens from the login client, whose audience StarRocks requires.
STARROCKS_SERVICE_CLIENT_ID = "srv-starrocks"
STARROCKS_SERVICE_GROUP = "role-default-writer"
STARROCKS_LOGIN_CLIENT_ID = "starrocks"
STARROCKS_AUDIENCE_MAPPER_NAME = "lakehouse-starrocks-audience"
JUPYTERHUB_REDIRECT_URI = "http://jupyterhub.localhost:8000/hub/oauth_callback"
AIRFLOW_LEGACY_REDIRECT_URI = "http://127.0.0.1:8085/oauth-authorized/keycloak"
AIRFLOW_REDIRECT_URIS = (
    "http://localhost:8085/auth/oauth-authorized/keycloak",
    "http://127.0.0.1:8085/auth/oauth-authorized/keycloak",
)
AIRFLOW_GROUP_MAPPER_NAME = "lakehouse-airflow-groups"
POST_LOGOUT_ATTRIBUTE = "post.logout.redirect.uris"
RUSTFS_CALLBACK_PATH = "/rustfs/admin/v3/oidc/callback/default"
RUSTFS_POST_LOGOUT_PATH = "/rustfs/console/auth/login"
RUSTFS_POST_LOGOUT_ATTRIBUTE = POST_LOGOUT_ATTRIBUTE
RUSTFS_DEFAULT_CONSOLE_PORT = 9001
RUSTFS_GROUP_MAPPER_NAME = "lakehouse-rustfs-groups"
JENKINS_CALLBACK_PATH = "/securityRealm/finishLogin"
JENKINS_POST_LOGOUT_PATH = "/"
JENKINS_DEFAULT_PORT = 8090
JENKINS_GROUP_MAPPER_NAME = "lakehouse-jenkins-groups"


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
        defaults = {
            "enabled": True,
            "publicClient": False,
            "bearerOnly": False,
            "standardFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "serviceAccountsEnabled": False,
            "protocol": "openid-connect",
            "clientAuthenticatorType": "client-secret",
        }
        for key, default in defaults.items():
            if key in representation and current.get(key, default) != representation[key]:
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
                elif client_id == "airflow" and _is_airflow_callback_correction(
                    key, current.get(key) or [], representation[key]
                ):
                    current[key] = representation[key]
                    update_client = True
                elif client_id in PORT_MOVABLE_CLIENTS and key == "redirectUris" and PORT_MOVABLE_CLIENTS[client_id](
                    current.get(key) or [], representation[key]
                ):
                    current[key] = representation[key]
                    update_client = True
                else:
                    raise BootstrapError(f"Existing client {client_id!r} conflicts on {key}; no changes applied.")
        desired_attributes = representation.get("attributes", {})
        attributes = dict(current.get("attributes") or {})
        update_attributes = False
        for key, value in desired_attributes.items():
            actual = attributes.get(key)
            if actual == value:
                continue
            if client_id == WRITER_CLIENT_ID and key == "access.token.lifespan" and actual in (None, ""):
                attributes[key] = value
                update_attributes = True
                continue
            if client_id in PORT_MOVABLE_CLIENTS and key == POST_LOGOUT_ATTRIBUTE and PORT_MOVABLE_CLIENTS[client_id](
                (actual or "").split("##"), value.split("##")
            ):
                attributes[key] = value
                update_attributes = True
                continue
            raise BootstrapError(f"Existing client {client_id!r} conflicts on {key}; no changes applied.")
        if "secret" in representation:
            status, current_secret = api.request("GET", f"/admin/realms/{REALM}/clients/{current['id']}/client-secret")
            checked(status, (200,), f"Verify client secret for {client_id}")
            if not isinstance(current_secret, dict) or current_secret.get("value") != representation["secret"]:
                raise BootstrapError(f"Existing client {client_id!r} does not match its protected secret file; no changes applied.")
        if update_attributes:
            current["attributes"] = attributes
            update_client = True
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


def _is_airflow_callback_correction(
    key: str, current: list[str], desired: list[str]
) -> bool:
    return (
        key == "redirectUris"
        and current
        in (
            [AIRFLOW_LEGACY_REDIRECT_URI],
            [AIRFLOW_REDIRECT_URIS[0]],
        )
        and desired == list(AIRFLOW_REDIRECT_URIS)
    )


def loopback_uris(port: int, path: str) -> list[str]:
    return [f"http://{host}:{port}{path}" for host in ("localhost", "127.0.0.1")]


def _loopback_uri_port(uris: list[str], path: str) -> int | None:
    if len(uris) != 2:
        return None
    try:
        port = urlsplit(uris[0]).port
    except ValueError:
        return None
    if port is None or sorted(uris) != sorted(loopback_uris(port, path)):
        return None
    return port


def _is_loopback_port_change(current: list[str], desired: list[str], paths: tuple[str, ...]) -> bool:
    """Accept only an exact loopback URI pair for one of ``paths`` moving to another port."""
    for path in paths:
        old = _loopback_uri_port(current, path)
        new = _loopback_uri_port(desired, path)
        if old is not None and new is not None:
            return old != new
    return False


def host_port(variable: str, default: int, env_file: Path = Path(".env")) -> int:
    """Resolve a published host port: environment, then .env, then the Compose default."""
    value = os.environ.get(variable)
    if value is None and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, separator, item = line.partition("=")
            if separator and key.strip() == variable:
                value = item.strip()
    value = value or str(default)
    if not value.isdecimal() or not 1 <= int(value) <= 65535:
        raise BootstrapError(f"{variable} must be a valid TCP port.")
    return int(value)


def rustfs_console_uris(port: int, path: str) -> list[str]:
    return loopback_uris(port, path)


def _is_rustfs_console_port_change(current: list[str], desired: list[str]) -> bool:
    return _is_loopback_port_change(current, desired, (RUSTFS_CALLBACK_PATH, RUSTFS_POST_LOGOUT_PATH))


def rustfs_console_port(env_file: Path = Path(".env")) -> int:
    return host_port("RUSTFS_CONSOLE_HOST_PORT", RUSTFS_DEFAULT_CONSOLE_PORT, env_file)


def _is_jenkins_port_change(current: list[str], desired: list[str]) -> bool:
    return _is_loopback_port_change(current, desired, (JENKINS_CALLBACK_PATH, JENKINS_POST_LOGOUT_PATH))


def jenkins_port(env_file: Path = Path(".env")) -> int:
    return host_port("JENKINS_HOST_PORT", JENKINS_DEFAULT_PORT, env_file)


# Clients whose exact loopback URI pairs may follow a changed published port.
PORT_MOVABLE_CLIENTS = {"rustfs": _is_rustfs_console_port_change, "jenkins": _is_jenkins_port_change}


def jenkins_client_configuration(secret: str, port: int) -> dict:
    return {
        "clientId": "jenkins",
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "bearerOnly": False,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False,
        "clientAuthenticatorType": "client-secret",
        "attributes": {
            "pkce.code.challenge.method": "S256",
            POST_LOGOUT_ATTRIBUTE: "##".join(loopback_uris(port, JENKINS_POST_LOGOUT_PATH)),
        },
        "secret": secret,
        "redirectUris": loopback_uris(port, JENKINS_CALLBACK_PATH),
        "webOrigins": [],
    }


def rustfs_client_configuration(secret: str, port: int) -> dict:
    return {
        "clientId": "rustfs",
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "bearerOnly": False,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False,
        "clientAuthenticatorType": "client-secret",
        "attributes": {
            "pkce.code.challenge.method": "S256",
            RUSTFS_POST_LOGOUT_ATTRIBUTE: "##".join(rustfs_console_uris(port, RUSTFS_POST_LOGOUT_PATH)),
        },
        "secret": secret,
        "redirectUris": rustfs_console_uris(port, RUSTFS_CALLBACK_PATH),
        "webOrigins": [],
    }


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


def airflow_client_configuration(secret: str) -> dict:
    return {
        "clientId": "airflow",
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "bearerOnly": False,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False,
        "clientAuthenticatorType": "client-secret",
        "secret": secret,
        "redirectUris": list(AIRFLOW_REDIRECT_URIS),
        "webOrigins": [],
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


def ensure_airflow_group_mapper(api: KeycloakAdmin, client_uuid: str) -> None:
    path = f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models"
    status, mappers = api.request("GET", path)
    checked(status, (200,), "Airflow mapper lookup")
    desired = {
        "name": AIRFLOW_GROUP_MAPPER_NAME,
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
    if len(existing) > 1:
        raise BootstrapError("Multiple Airflow group mappers exist; no changes applied.")
    if existing:
        mapper = existing[0]
        if mapper.get("protocolMapper") != desired["protocolMapper"] or any(
            (mapper.get("config") or {}).get(key) != value
            for key, value in desired["config"].items()
        ):
            raise BootstrapError("An existing Airflow group mapper conflicts; no changes applied.")
        return
    status, _ = api.request("POST", path, desired)
    checked(status, (201,), "Create Airflow group mapper")


def ensure_rustfs_group_mapper(api: KeycloakAdmin, client_uuid: str) -> None:
    _ensure_id_token_group_mapper(api, client_uuid, RUSTFS_GROUP_MAPPER_NAME, "RustFS")


def ensure_jenkins_group_mapper(api: KeycloakAdmin, client_uuid: str) -> None:
    _ensure_id_token_group_mapper(api, client_uuid, JENKINS_GROUP_MAPPER_NAME, "Jenkins")


def _ensure_id_token_group_mapper(api: KeycloakAdmin, client_uuid: str, name: str, label: str) -> None:
    path = f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models"
    status, mappers = api.request("GET", path)
    checked(status, (200,), f"{label} mapper lookup")
    # RustFS and Jenkins read group membership from the ID token, unlike Airflow.
    desired = {
        "name": name,
        "protocol": "openid-connect",
        "protocolMapper": "oidc-group-membership-mapper",
        "consentRequired": False,
        "config": {
            "claim.name": "groups",
            "full.path": "false",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "userinfo.token.claim": "true",
        },
    }
    existing = [item for item in mappers or [] if item.get("name") == desired["name"]]
    if len(existing) > 1:
        raise BootstrapError(f"Multiple {label} group mappers exist; no changes applied.")
    if existing:
        mapper = existing[0]
        if mapper.get("protocolMapper") != desired["protocolMapper"] or any(
            (mapper.get("config") or {}).get(key) != value
            for key, value in desired["config"].items()
        ):
            raise BootstrapError(f"An existing {label} group mapper conflicts; no changes applied.")
        return
    status, _ = api.request("POST", path, desired)
    checked(status, (201,), f"Create {label} group mapper")


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


def grant_realm_admin(api: KeycloakAdmin, group_id: str) -> None:
    """Give a group the built-in realm-admin role of this realm's realm-management client."""
    client = find_client(api, REALM_MANAGEMENT_CLIENT_ID)
    if client is None:
        raise BootstrapError("The realm-management client is missing.")
    status, role = api.request("GET", f"/admin/realms/{REALM}/clients/{client['id']}/roles/{REALM_ADMIN_ROLE}")
    checked(status, (200,), "Realm-admin role lookup")
    add_client_role_to_group(api, group_id, client["id"], role)


def find_user(api: KeycloakAdmin, username: str) -> dict | None:
    status, users = api.request("GET", f"/admin/realms/{REALM}/users", query={"username": username, "exact": "true"})
    checked(status, (200,), "User lookup")
    matches = [item for item in users or [] if item.get("username") == username]
    if len(matches) > 1:
        raise BootstrapError(f"Expected one Keycloak user named {username!r}; found {len(matches)}.")
    return matches[0] if matches else None


def load_bootstrap_identities(path: Path = BOOTSTRAP_USERS_FILE) -> dict:
    """Read the default groups, users, and password (the single source of truth)."""
    try:
        identities = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BootstrapError("The bootstrap identity file is unavailable or invalid.") from error
    groups = identities.get("groups") or []
    if set(groups) != set(GROUP_PRODUCT_ROLES) or not identities.get("default_password"):
        raise BootstrapError("The bootstrap identity file does not match the approved groups.")
    for user in identities.get("users") or []:
        if user.get("group") not in groups or not user.get("username"):
            raise BootstrapError("A bootstrap user has an unknown group.")
    return identities


def bootstrap_user_representation(user: dict, password: str, email_domain: str) -> dict:
    return {
        "username": user["username"],
        "enabled": True,
        "emailVerified": True,
        "firstName": user["firstName"],
        "lastName": user["lastName"],
        "email": f"{user['username']}@{email_domain}",
        "requiredActions": [],
        "credentials": [{"type": "password", "value": password, "temporary": False}],
    }


def create_missing_bootstrap_user(api: KeycloakAdmin, user: dict, password: str, email_domain: str) -> dict | None:
    """Create a bootstrap user only if absent; existing users are never changed here."""
    if find_user(api, user["username"]):
        return None
    status, _ = api.request("POST", f"/admin/realms/{REALM}/users", bootstrap_user_representation(user, password, email_domain))
    checked(status, (201,), f"Create bootstrap user {user['username']}")
    created = find_user(api, user["username"])
    if not created:
        raise BootstrapError(f"Bootstrap user {user['username']!r} could not be read back.")
    return created


def writer_client_configuration(secret: str) -> dict:
    return {
        "clientId": WRITER_CLIENT_ID,
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "bearerOnly": False,
        "standardFlowEnabled": False,
        "directAccessGrantsEnabled": True,
        "serviceAccountsEnabled": False,
        "clientAuthenticatorType": "client-secret",
        "attributes": {"access.token.lifespan": "3600"},
        "secret": secret,
    }


def starrocks_service_client_configuration(secret: str) -> dict:
    return {
        "clientId": STARROCKS_SERVICE_CLIENT_ID,
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "bearerOnly": False,
        "standardFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": True,
        "clientAuthenticatorType": "client-secret",
        "secret": secret,
    }


def starrocks_login_client_configuration() -> dict:
    return {
        "clientId": STARROCKS_LOGIN_CLIENT_ID,
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": True,
        "bearerOnly": False,
        "standardFlowEnabled": False,
        "directAccessGrantsEnabled": True,
        "serviceAccountsEnabled": False,
    }


def ensure_audience_mapper(api: KeycloakAdmin, client_uuid: str, audience: str) -> None:
    path = f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models"
    status, mappers = api.request("GET", path)
    checked(status, (200,), "Audience mapper lookup")
    desired = {
        "name": STARROCKS_AUDIENCE_MAPPER_NAME,
        "protocol": "openid-connect",
        "protocolMapper": "oidc-audience-mapper",
        "consentRequired": False,
        "config": {
            "included.client.audience": audience,
            "id.token.claim": "false",
            "access.token.claim": "true",
        },
    }
    existing = [item for item in mappers or [] if item.get("name") == desired["name"]]
    if existing:
        actual = existing[0].get("config") or {}
        if existing[0].get("protocolMapper") != desired["protocolMapper"] or any(
            actual.get(key) != value for key, value in desired["config"].items()
        ):
            raise BootstrapError("An existing StarRocks audience mapper conflicts; no changes applied.")
        return
    status, _ = api.request("POST", path, desired)
    checked(status, (201,), "Create StarRocks audience mapper")


def ensure_service_account_group(api: KeycloakAdmin, client_uuid: str, group: dict) -> None:
    status, user = api.request("GET", f"/admin/realms/{REALM}/clients/{client_uuid}/service-account-user")
    checked(status, (200,), "Service account lookup")
    if not isinstance(user, dict) or not user.get("id"):
        raise BootstrapError("The StarRocks service account could not be read.")
    add_user_to_group(api, user["id"], group)


def add_user_to_group(api: KeycloakAdmin, user_id: str, group: dict) -> None:
    status, memberships = api.request("GET", f"/admin/realms/{REALM}/users/{user_id}/groups")
    checked(status, (200,), "User group lookup")
    if any(item.get("id") == group.get("id") for item in memberships or []):
        return
    status, _ = api.request("PUT", f"/admin/realms/{REALM}/users/{user_id}/groups/{group['id']}")
    checked(status, (204,), "Add user to product group")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--redirect-uri", help="Exact local OAuth callback URI for the human PKCE client")
    parser.add_argument("--admin-password-file", type=Path, default=Path(".runtime/credentials/keycloak-admin-password"))
    parser.add_argument("--writer-secret-file", type=Path, default=Path(".runtime/credentials/keycloak-writer-client-secret"))
    parser.add_argument("--jupyterhub-secret-file", type=Path, default=Path(".runtime/credentials/jupyterhub-oidc-client-secret"))
    parser.add_argument("--airflow-secret-file", type=Path, help="Protected Airflow OIDC client secret; enables Airflow client bootstrap")
    parser.add_argument("--rustfs-secret-file", type=Path, default=Path(".runtime/credentials/rustfs-oidc-client-secret"))
    parser.add_argument("--jenkins-secret-file", type=Path, default=Path(".runtime/credentials/jenkins-oidc-client-secret"))
    parser.add_argument("--starrocks-secret-file", type=Path, default=Path(".runtime/credentials/srv-starrocks-client-secret"))
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
        airflow_secret = read_secret(args.airflow_secret_file) if args.airflow_secret_file else None
        rustfs_secret = read_secret(args.rustfs_secret_file)
        rustfs_port = rustfs_console_port()
        jenkins_secret = read_secret(args.jenkins_secret_file)
        jenkins_host_port = jenkins_port()
        starrocks_secret = read_secret(args.starrocks_secret_file)
        identities = load_bootstrap_identities()
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
        writer = ensure_client(api, writer_client_configuration(writer_secret))
        hub_port = os.environ.get("JUPYTERHUB_HOST_PORT", "8000")
        if not hub_port.isdecimal() or not (1 <= int(hub_port) <= 65535):
            raise BootstrapError("JUPYTERHUB_HOST_PORT must be a valid TCP port.")
        hub_callback = f"http://jupyterhub.localhost:{hub_port}/hub/oauth_callback"
        jupyterhub = ensure_client(api, jupyterhub_client_configuration(jupyterhub_secret, hub_callback))
        ensure_mapper(api, human["id"], polaris["id"])
        ensure_mapper(api, writer["id"], polaris["id"])
        ensure_mapper(api, jupyterhub["id"], polaris["id"])
        ensure_jupyterhub_group_mapper(api, jupyterhub["id"])
        if airflow_secret is not None:
            airflow = ensure_client(api, airflow_client_configuration(airflow_secret))
            ensure_airflow_group_mapper(api, airflow["id"])
        rustfs = ensure_client(api, rustfs_client_configuration(rustfs_secret, rustfs_port))
        ensure_rustfs_group_mapper(api, rustfs["id"])
        jenkins = ensure_client(api, jenkins_client_configuration(jenkins_secret, jenkins_host_port))
        ensure_jenkins_group_mapper(api, jenkins["id"])
        starrocks_service = ensure_client(api, starrocks_service_client_configuration(starrocks_secret))
        ensure_mapper(api, starrocks_service["id"], polaris["id"])
        starrocks_login = ensure_client(api, starrocks_login_client_configuration())
        ensure_audience_mapper(api, starrocks_login["id"], STARROCKS_LOGIN_CLIENT_ID)

        groups = {name: ensure_group(api, name) for name in GROUP_PRODUCT_ROLES}
        roles = {role: ensure_role(api, polaris["id"], role) for role in ROLES}
        for name, role in GROUP_PRODUCT_ROLES.items():
            add_client_role_to_group(api, groups[name]["id"], polaris["id"], roles[role])
        grant_realm_admin(api, groups[REALM_ADMIN_GROUP]["id"])
        ensure_service_account_group(api, starrocks_service["id"], groups[STARROCKS_SERVICE_GROUP])
        created = 0
        for user in identities["users"]:
            new_user = create_missing_bootstrap_user(api, user, identities["default_password"], identities["email_domain"])
            if new_user:
                add_user_to_group(api, new_user["id"], groups[user["group"]])
                created += 1
        callback_state = "callback=configured" if args.redirect_uri else "callback=not-configured"
        airflow_state = "airflow-client=configured" if airflow_secret is not None else "airflow-client=not-requested"
        print(f"Keycloak realm bootstrap verified (operation_id={operation_id}; {callback_state}; {airflow_state}; writer-client={WRITER_CLIENT_ID}; rustfs-client=configured; jenkins-client=configured; starrocks-clients=configured; groups={len(groups)}; realm-admin-group={REALM_ADMIN_GROUP}; bootstrap-users-created={created}).")
        return 0
    except BootstrapError as error:
        print(f"Keycloak bootstrap failed (operation_id={operation_id}): {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
