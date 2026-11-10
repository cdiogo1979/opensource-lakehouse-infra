#!/usr/bin/env python3
"""Verify Keycloak writer authentication reaches Polaris authorization."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


WRITER = "srv-default-writer"
WRITER_CLIENT = "lakehouse-writer"
WRITER_ROLE = "role-default-writer"


class VerificationError(Exception):
    """A safe operator-facing verification failure."""


def read_secret(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise VerificationError("Protected writer client secret is unavailable.")
    value = path.read_text(encoding="utf-8").splitlines()
    if not value or not value[0]:
        raise VerificationError("Protected writer client secret is empty.")
    return value[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keycloak-url", default="http://127.0.0.1:8080")
    parser.add_argument("--polaris-url", default="http://127.0.0.1:8181")
    parser.add_argument("--secret-file", type=Path, default=Path(".runtime/credentials/keycloak-writer-client-secret"))
    parser.add_argument("--password-file", type=Path, default=Path(".runtime/credentials/srv-default-writer-password"))
    args = parser.parse_args()
    try:
        form = urllib.parse.urlencode({
            "grant_type": "password",
            "client_id": WRITER_CLIENT,
            "client_secret": read_secret(args.secret_file),
            "username": WRITER,
            "password": read_secret(args.password_file),
            "scope": "openid",
        }).encode()
        request = urllib.request.Request(
            f"{args.keycloak_url.rstrip('/')}/realms/lakehouse/protocol/openid-connect/token",
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            raise VerificationError(f"Keycloak writer token request failed ({type(error).__name__}).") from error
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token:
            raise VerificationError("Keycloak response did not contain a writer access token.")

        principal = urllib.parse.quote(WRITER, safe="")
        url = f"{args.polaris_url.rstrip('/')}/api/management/v1/principals/{principal}"

        def polaris_request(access_token: str) -> tuple[int, bytes]:
            request = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Polaris-Realm": "lakehouse",
                    "Accept": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    return response.status, response.read()
            except urllib.error.HTTPError as error:
                return error.code, error.read()
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                raise VerificationError(f"Polaris writer request failed ({type(error).__name__}).") from error

        status, body = polaris_request(token)

        # The writer must authenticate, but GET_PRINCIPAL is deliberately a
        # privileged management operation. Polaris 1.8.0 reports the resolved
        # identity and active role in its 403 response for this expected deny.
        try:
            result = json.loads(body)
            error = result.get("error", {}) if isinstance(result, dict) else {}
            message = error.get("message", "") if isinstance(error, dict) else ""
        except (UnicodeError, json.JSONDecodeError):
            message = ""
            error = {}
        if status != 403 or error.get("type") != "ForbiddenException":
            raise VerificationError(f"Expected authenticated writer to be denied GET_PRINCIPAL; received HTTP {status}.")
        if WRITER not in message or WRITER_ROLE not in message:
            raise VerificationError("Polaris denied the request without confirming the expected writer identity and role.")

        token_parts = token.split(".")
        if len(token_parts) != 3 or not token_parts[2]:
            raise VerificationError("Keycloak returned a token with an unsupported format.")
        signature = token_parts[2]
        token_parts[2] = ("A" if signature[0] != "A" else "B") + signature[1:]
        invalid_status, _ = polaris_request(".".join(token_parts))
        if invalid_status != 401:
            raise VerificationError(f"Polaris did not reject the invalid-signature token; received HTTP {invalid_status}.")
        print("Writer authentication and role resolution verified (expected HTTP 403); invalid-signature token rejected (HTTP 401).")
        return 0
    except VerificationError as error:
        print(f"Keycloak-to-Polaris authentication verification failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
