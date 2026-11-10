"""Strict HTTPS client for the user's own Hub token broker binding."""

from __future__ import annotations

import base64
import json
import os
import ssl
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True, repr=False)
class BrokerToken:
    access_token: str
    expires_at: int


class BrokerClientError(RuntimeError):
    """Safe client error that never carries response bodies or token values."""


def _jwt_expiry(token: object) -> int | None:
    if not isinstance(token, str) or len(token) > 16384:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        payload = parts[1] + ("=" * (-len(parts[1]) % 4))
        claims = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return None
    expiry = claims.get("exp") if isinstance(claims, dict) else None
    if isinstance(expiry, bool) or not isinstance(expiry, (int, float)):
        return None
    return int(expiry)


def request_user_token(
    *,
    broker_url: str | None = None,
    ca_path: str | None = None,
    hub_api_token: str | None = None,
    timeout_seconds: float = 5.0,
    clock=time.time,
) -> BrokerToken:
    """Request the server-bound user's current access JWT over verified TLS."""
    broker_url = broker_url or os.environ.get(
        "LAKEHOUSE_TOKEN_BROKER_URL", "https://jupyterhub:8443/api/v1/token"
    )
    ca_path = ca_path or os.environ.get(
        "LAKEHOUSE_TOKEN_BROKER_CA", "/run/certs/jupyterhub-broker-ca.crt"
    )
    hub_api_token = hub_api_token or os.environ.get("JUPYTERHUB_API_TOKEN")
    if not broker_url.startswith("https://") or not hub_api_token:
        raise BrokerClientError("The internal token broker is not configured.")
    if os.path.islink(ca_path) or not os.path.isfile(ca_path):
        raise BrokerClientError("The internal token broker trust certificate is unavailable.")

    try:
        tls_context = ssl.create_default_context(cafile=ca_path)
    except (OSError, ssl.SSLError) as error:
        raise BrokerClientError("The internal token broker trust certificate is invalid.") from error
    request = Request(
        broker_url,
        data=b"{}",
        headers={
            "Authorization": f"Bearer {hub_api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds, context=tls_context) as response:
            body = response.read(4097)
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise BrokerClientError("The internal token broker request failed.") from error
    if len(body) > 4096:
        raise BrokerClientError("The internal token broker response is too large.")
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError, json.JSONDecodeError) as error:
        raise BrokerClientError("The internal token broker response is invalid.") from error
    if not isinstance(payload, dict) or set(payload) != {"access_token", "expires_at"}:
        raise BrokerClientError("The internal token broker response is invalid.")
    token = payload["access_token"]
    expiry = _jwt_expiry(token)
    response_expiry = payload["expires_at"]
    if (
        expiry is None
        or isinstance(response_expiry, bool)
        or not isinstance(response_expiry, int)
        or expiry != response_expiry
        or expiry - clock() <= 60
    ):
        raise BrokerClientError("The internal token broker returned an unusable token.")
    return BrokerToken(token, expiry)
