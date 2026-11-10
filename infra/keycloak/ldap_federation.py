"""The lakehouse realm's LDAP user storage (writable federation, BR-2).

Users and passwords live in the `ldap` directory; Keycloak creates users and
sets passwords there through the admin API, and keeps groups itself. Keycloak's
default LDAP mappers (uid, cn = first name, sn = last name, mail) are used as
created. ``api`` is any object with ``request(method, path, payload=None, *, query=None)``.
"""

from __future__ import annotations

import urllib.parse

REALM = "lakehouse"
PROVIDER_NAME = "lakehouse-ldap"
PROVIDER_TYPE = "org.keycloak.storage.UserStorageProvider"
CONNECTION_URL = "ldaps://ldap:636"
BIND_DN = "cn=keycloak,ou=services,dc=lakehouse,dc=local"
USERS_DN = "ou=people,dc=lakehouse,dc=local"

# Settings compared on every run; a difference in USERS_DN or EDIT_MODE is a conflict.
MANAGED = {
    "enabled": "true",
    "priority": "0",
    "editMode": "WRITABLE",
    "vendor": "other",
    "connectionUrl": CONNECTION_URL,
    "authType": "simple",
    "bindDn": BIND_DN,
    "usersDn": USERS_DN,
    "searchScope": "1",
    "usernameLDAPAttribute": "uid",
    "rdnLDAPAttribute": "uid",
    "uuidLDAPAttribute": "entryUUID",
    "userObjectClasses": "inetOrgPerson, organizationalPerson",
    "importEnabled": "true",
    "syncRegistrations": "true",
    "usePasswordModifyExtendedOp": "true",
    "trustEmail": "true",
    "pagination": "false",
    "useTruststoreSpi": "always",
    "connectionPooling": "true",
    "validatePasswordPolicy": "false",
}
CONFLICT_KEYS = ("usersDn", "editMode", "usernameLDAPAttribute", "uuidLDAPAttribute")


class LdapFederationError(Exception):
    """Safe operator-facing failure; the bind credential is never included."""


def desired_component(realm_id: str, bind_password: str) -> dict:
    config = {key: [value] for key, value in MANAGED.items()}
    config["bindCredential"] = [bind_password]
    return {"name": PROVIDER_NAME, "providerId": "ldap", "providerType": PROVIDER_TYPE, "parentId": realm_id, "config": config}


def find_provider(api) -> dict | None:
    status, items = api.request("GET", f"/admin/realms/{REALM}/components", query={"type": PROVIDER_TYPE})
    if status != 200:
        raise LdapFederationError(f"User storage lookup failed with HTTP {status}.")
    matches = [item for item in items or [] if item.get("name") == PROVIDER_NAME]
    if len(matches) > 1:
        raise LdapFederationError(f"Ambiguous user storage provider {PROVIDER_NAME!r}.")
    return matches[0] if matches else None


def plan(current: dict | None) -> tuple[str, list[str]]:
    """'create', 'equal', or 'update' with the drifted keys; raises on a conflict."""
    if current is None:
        return "create", []
    config = current.get("config") or {}
    actual = {key: (config.get(key) or [None])[0] for key in MANAGED}
    conflicts = [key for key in CONFLICT_KEYS if actual[key] != MANAGED[key]]
    if conflicts:
        raise LdapFederationError(f"Existing {PROVIDER_NAME!r} differs in {', '.join(conflicts)}; no changes applied.")
    drift = [key for key in MANAGED if actual[key] != MANAGED[key]]
    return ("update", drift) if drift else ("equal", [])


def ensure_ldap_federation(api, realm_id: str, bind_password: str) -> str:
    """Create the provider, or bring drifted settings (and the bind credential) back."""
    current = find_provider(api)
    outcome, drift = plan(current)
    desired = desired_component(realm_id, bind_password)
    if outcome == "create":
        status, _ = api.request("POST", f"/admin/realms/{REALM}/components", desired)
        if status != 201:
            raise LdapFederationError(f"Creating the LDAP user storage failed with HTTP {status}.")
        return "created"
    # The bind credential is write-only (Keycloak returns it masked), so it is
    # always sent with an update and an update always runs when the file may
    # have changed: on drift, or when the connection test below fails.
    if outcome == "update":
        update(api, current, desired)
        return "updated (" + ", ".join(drift) + ")"
    return "unchanged"


def update(api, current: dict, desired: dict) -> None:
    body = dict(current)
    body["config"] = {**(current.get("config") or {}), **desired["config"]}
    status, _ = api.request("PUT", f"/admin/realms/{REALM}/components/{urllib.parse.quote(current['id'], safe='')}", body)
    if status not in (200, 204):
        raise LdapFederationError(f"Updating the LDAP user storage failed with HTTP {status}.")


def test_connection(api, bind_password: str) -> None:
    """Keycloak's own check of the connection and the bind (testAuthentication)."""
    current = find_provider(api)
    if current is None:
        raise LdapFederationError("The LDAP user storage is not configured.")
    payload = {
        "action": "testAuthentication",
        "connectionUrl": CONNECTION_URL,
        "bindDn": BIND_DN,
        "bindCredential": bind_password,
        "useTruststoreSpi": "always",
        "authType": "simple",
        "componentId": current["id"],
    }
    status, _ = api.request("POST", f"/admin/realms/{REALM}/testLDAPConnection", payload)
    if status not in (200, 204):
        raise LdapFederationError(f"Keycloak could not bind to LDAP (HTTP {status}); check the ldap service, its CA, and the bind password.")


def ensure_and_test(api, realm_id: str, bind_password: str) -> str:
    """Ensure the provider; if the bind fails, resend the credential once and retest."""
    outcome = ensure_ldap_federation(api, realm_id, bind_password)
    try:
        test_connection(api, bind_password)
    except LdapFederationError:
        if outcome == "created":
            raise
        update(api, find_provider(api), desired_component(realm_id, bind_password))
        test_connection(api, bind_password)
        outcome += "; bind credential refreshed"
    return outcome
