"""StarRocks connections for workload code, in an Airflow run or a JupyterHub server.

``connect()`` returns a PyMySQL (DB-API) connection to the platform's StarRocks over TLS,
verified with the StarRocks CA:

- **Airflow run** (``LAKEHOUSE_TOKEN_PROVIDER=airflow``): as the product's writer
  (``LAKEHOUSE_STARROCKS_USER``), logged in with the run's Keycloak access token, renewed
  through the run's token broker when it is close to expiry.
- **Jupyter** (``JUPYTERHUB_USER``): as the signed-in user, with their StarRocks (LDAP)
  password, asked with ``getpass`` every time; it is never stored.

The platform sets the host, port and CA (``LAKEHOUSE_STARROCKS_HOST``, ``_PORT``, ``_CA``);
product repositories never configure them. No token, capability or password is printed,
logged, or put in an error message. Functional design: rules AC-17 to AC-21 of intent
``20261125-starrocks-audit-capture``.
"""

from __future__ import annotations

import base64
import getpass
import json
import os
import ssl
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_HOST = "starrocks-fe"
DEFAULT_PORT = 9030
RENEW_MARGIN_SECONDS = 120
CONNECT_TIMEOUT_SECONDS = 15
READ_TIMEOUT_SECONDS = 600
BROKER_TIMEOUT_SECONDS = 10
MAX_BROKER_RESPONSE = 8192

_renewed_token: str | None = None


class StarRocksConnectionError(RuntimeError):
    """A connection can't be made; the message never holds a secret."""


@dataclass(frozen=True)
class Settings:
    mode: str  # "airflow" or "jupyter"
    host: str
    port: int
    ca_file: str
    user: str


def connection_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Host, port, CA, user and mode from the platform's environment (AC-17, AC-18).

    Raises:
        StarRocksConnectionError: Outside an Airflow run or a JupyterHub server, or with a missing or invalid setting.
    """
    environ = os.environ if environ is None else environ
    if environ.get("LAKEHOUSE_TOKEN_PROVIDER") == "airflow":
        mode, user, user_variable = "airflow", environ.get("LAKEHOUSE_STARROCKS_USER", ""), "LAKEHOUSE_STARROCKS_USER"
    elif environ.get("JUPYTERHUB_USER"):
        mode, user, user_variable = "jupyter", environ.get("JUPYTERHUB_USER", ""), "JUPYTERHUB_USER"
    else:
        raise StarRocksConnectionError("lakehouse_starrocks.connect() works in an Airflow run or a JupyterHub server.")
    host = environ.get("LAKEHOUSE_STARROCKS_HOST") or DEFAULT_HOST
    port_text = environ.get("LAKEHOUSE_STARROCKS_PORT") or str(DEFAULT_PORT)
    ca_file = environ.get("LAKEHOUSE_STARROCKS_CA", "")
    if not user or any(ch in user for ch in "\x00\r\n'\"`@"):
        raise StarRocksConnectionError(f"{user_variable} is missing or invalid.")
    if not host.replace("-", "").replace(".", "").isalnum():
        raise StarRocksConnectionError("LAKEHOUSE_STARROCKS_HOST is invalid.")
    if not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
        raise StarRocksConnectionError("LAKEHOUSE_STARROCKS_PORT must be a port number.")
    if not ca_file or os.path.islink(ca_file) or not os.path.isfile(ca_file):
        raise StarRocksConnectionError("LAKEHOUSE_STARROCKS_CA does not name the StarRocks CA certificate.")
    return Settings(mode, host, int(port_text), ca_file, user)


def token_expiry(token: object) -> int | None:
    """The ``exp`` claim of a JWT, read without verification (StarRocks verifies the token)."""
    if not isinstance(token, str) or len(token) > 16384:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        claims = json.loads(base64.urlsafe_b64decode((parts[1] + "=" * (-len(parts[1]) % 4)).encode("ascii")))
    except (ValueError, UnicodeError):
        return None
    expiry = claims.get("exp") if isinstance(claims, dict) else None
    if isinstance(expiry, bool) or not isinstance(expiry, (int, float)):
        return None
    return int(expiry)


def token_expires_soon(token: object, now: float, margin: int = RENEW_MARGIN_SECONDS) -> bool:
    """True when the token has no readable expiry or expires within ``margin`` seconds (AC-19)."""
    expiry = token_expiry(token)
    return expiry is None or expiry - now <= margin


def _renew(environ: Mapping[str, str]) -> str:
    """A fresh writer token from the run's token broker (``POST /v1/runs/token``)."""
    url = (environ.get("LAKEHOUSE_TOKEN_BROKER_URL") or "").rstrip("/")
    ca_file = environ.get("LAKEHOUSE_TOKEN_BROKER_CA") or ""
    handle, capability = environ.get("LAKEHOUSE_RUN_HANDLE") or "", environ.get("LAKEHOUSE_RUN_CAPABILITY") or ""
    if not url.startswith("https://") or not handle or not capability or os.path.islink(ca_file) or not os.path.isfile(ca_file):
        raise StarRocksConnectionError("The run's token broker settings are incomplete.")
    request = Request(
        url + "/v1/runs/token",
        data=json.dumps({"run_handle": handle}).encode("utf-8"),
        headers={"Authorization": f"Bearer {capability}", "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        context = ssl.create_default_context(cafile=ca_file)
        with urlopen(request, timeout=BROKER_TIMEOUT_SECONDS, context=context) as response:  # nosec B310 - https only, checked above
            body = response.read(MAX_BROKER_RESPONSE + 1)
    except (HTTPError, URLError, TimeoutError, OSError, ssl.SSLError) as error:
        raise StarRocksConnectionError("The run's token renewal failed.") from error
    try:
        payload = json.loads(body) if len(body) <= MAX_BROKER_RESPONSE else None
    except (ValueError, UnicodeError):
        payload = None
    token = payload.get("access_token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token:
        raise StarRocksConnectionError("The run's token broker returned an invalid response.")
    return token


def current_writer_token(environ: Mapping[str, str] | None = None, clock: Callable[[], float] = time.time) -> str:
    """The run's access token: the initial one while it is valid long enough, else a renewed one (AC-19)."""
    global _renewed_token
    environ = os.environ if environ is None else environ
    for token in (_renewed_token, environ.get("LAKEHOUSE_INITIAL_ACCESS_TOKEN")):
        if token and not token_expires_soon(token, clock()):
            return token
    _renewed_token = _renew(environ)
    return _renewed_token


class _OpenIdConnect:
    """MySQL's ``authentication_openid_connect_client``: StarRocks' token login (as the platform's MV deploy)."""

    def __init__(self, connection: Any):
        self.connection = connection

    def authenticate(self, packet: Any) -> Any:
        token = self.connection.password
        token = token if isinstance(token, bytes) else token.encode("ascii")
        size = len(token)
        length = bytes([size]) if size < 251 else (bytes([0xFC]) + size.to_bytes(2, "little") if size < 65536 else bytes([0xFD]) + size.to_bytes(3, "little"))
        self.connection.write_packet(bytes([1]) + length + token)
        return self.connection._read_packet()


def connect(*, password_prompt: Callable[[str], str] = getpass.getpass, environ: Mapping[str, str] | None = None) -> Any:
    """A TLS connection to StarRocks: the product writer in an Airflow run, the signed-in user in Jupyter (AC-20).

    Raises:
        StarRocksConnectionError: Missing settings, a failed token renewal, or an empty password.
    """
    import pymysql

    settings = connection_settings(environ)
    options: dict[str, Any] = {}
    if settings.mode == "airflow":
        secret = current_writer_token(environ)
        options["auth_plugin_map"] = {b"authentication_openid_connect_client": _OpenIdConnect}
    else:
        secret = password_prompt(f"StarRocks password for {settings.user}: ")
        if not secret:
            raise StarRocksConnectionError("No StarRocks password was entered.")
    context = ssl.create_default_context(cafile=settings.ca_file)
    return pymysql.connect(
        host=settings.host,
        port=settings.port,
        user=settings.user,
        password=secret,
        ssl=context,
        autocommit=True,
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
        read_timeout=READ_TIMEOUT_SECONDS,
        charset="utf8mb4",
        **options,
    )
