#!/usr/bin/env python3
"""Check Polaris rejects Keycloak tokens with wrong audience or expired claims."""

from __future__ import annotations

import base64
import json
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KEYCLOAK = "http://127.0.0.1:8080"
POLARIS = "http://127.0.0.1:8181"
REALM = "lakehouse"
PRINCIPAL = "service-account-write-service-account"


class CheckError(Exception):
    """Safe verification error without credentials or token content."""


def request(method: str, url: str, *, token: str | None = None, payload: dict | None = None):
    headers = {"Accept": "application/json"}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        return error.code, None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        raise CheckError(f"Provider request failed ({type(error).__name__}).") from None


def read_secret(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise CheckError("Protected Keycloak administrator credential is unavailable.")
    values = path.read_text(encoding="utf-8").splitlines()
    if not values or not values[0]:
        raise CheckError("Protected Keycloak administrator credential is empty.")
    return values[0]


def main() -> int:
    client_id = f"oidc-negative-{uuid.uuid4().hex[:12]}"
    created_client: str | None = None
    admin_token: str | None = None
    try:
        admin_form = urllib.parse.urlencode({
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": "admin",
            "password": read_secret(ROOT / ".runtime/credentials/keycloak-admin-password"),
        }).encode()
        req = urllib.request.Request(
            f"{KEYCLOAK}/realms/master/protocol/openid-connect/token",
            data=admin_form,
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            admin_token = json.loads(response.read())["access_token"]

        status, _ = request("POST", f"{KEYCLOAK}/admin/realms/{REALM}/clients", token=admin_token, payload={
            "clientId": client_id,
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "standardFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "serviceAccountsEnabled": True,
            "fullScopeAllowed": True,
            "clientAuthenticatorType": "client-secret",
            "secret": secrets.token_urlsafe(48),
            "attributes": {"access.token.lifespan": "1"},
        })
        if status != 201:
            raise CheckError(f"Could not create disposable test client (HTTP {status}).")

        status, clients = request(
            "GET", f"{KEYCLOAK}/admin/realms/{REALM}/clients?clientId={urllib.parse.quote(client_id)}",
            token=admin_token,
        )
        matches = [item for item in (clients or []) if item.get("clientId") == client_id]
        if status != 200 or len(matches) != 1:
            raise CheckError("Could not identify the disposable test client for cleanup.")
        created_client = matches[0]["id"]

        credentials_req = urllib.request.Request(
            f"{KEYCLOAK}/admin/realms/{REALM}/clients/{created_client}/client-secret",
            headers={"Authorization": f"Bearer {admin_token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(credentials_req, timeout=15) as response:
            client_secret = json.loads(response.read())["value"]

        def token_request() -> str:
            body = urllib.parse.urlencode({
                "grant_type": "client_credentials", "client_id": client_id,
                "client_secret": client_secret,
            }).encode()
            token_req = urllib.request.Request(
                f"{KEYCLOAK}/realms/{REALM}/protocol/openid-connect/token", data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            )
            with urllib.request.urlopen(token_req, timeout=15) as response:
                return json.loads(response.read())["access_token"]

        def polaris_status(access_token: str) -> int:
            encoded_principal = urllib.parse.quote(PRINCIPAL, safe="")
            status, _ = request(
                "GET", f"{POLARIS}/api/management/v1/principals/{encoded_principal}",
                token=access_token,
            )
            return status

        wrong_audience_token = token_request()
        payload_part = wrong_audience_token.split(".")[1]
        payload_part += "=" * (-len(payload_part) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_part.encode()))
        audiences = claims.get("aud", [])
        if isinstance(audiences, str):
            audiences = [audiences]
        if not isinstance(audiences, list) or "polaris" in audiences:
            raise CheckError("Disposable token did not have the expected non-Polaris audience.")
        wrong_audience_status = polaris_status(wrong_audience_token)
        if wrong_audience_status == 401:
            print("OIDC negative case: token from unrelated client rejected (HTTP 401).")
        elif wrong_audience_status == 403:
            raise CheckError("Polaris accepted an unrelated-client token; audience validation is not enforced (HTTP 403).")
        else:
            raise CheckError(f"Unrelated-client token returned unexpected HTTP {wrong_audience_status}.")

        short_lived_token = token_request()
        time.sleep(3)
        expired_status = polaris_status(short_lived_token)
        if expired_status != 401:
            raise CheckError(f"Expired token was not rejected with HTTP 401 (received HTTP {expired_status}).")
        print("OIDC negative case: expired token rejected (HTTP 401).")
        return 0
    except (CheckError, OSError, KeyError, ValueError, urllib.error.URLError) as error:
        print(f"Polaris OIDC negative-case verification failed: {error}", file=sys.stderr)
        return 1
    finally:
        if created_client and admin_token:
            status, _ = request(
                "DELETE", f"{KEYCLOAK}/admin/realms/{REALM}/clients/{created_client}",
                token=admin_token,
            )
            if status not in (204, 404):
                print("WARNING: disposable Keycloak client cleanup could not be confirmed.", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
