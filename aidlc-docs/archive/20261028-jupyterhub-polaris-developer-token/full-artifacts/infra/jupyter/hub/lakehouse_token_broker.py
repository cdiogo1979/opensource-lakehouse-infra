"""Authenticated, in-process token broker for active JupyterHub servers."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import ssl
import time
import uuid
from collections import Counter
from contextlib import asynccontextmanager
from email.message import Message
from urllib.parse import urlencode

from jupyterhub import orm
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.web import Application, RequestHandler

from lakehouse_policy import eligible_group_names


REFRESH_WINDOW_SECONDS = 60
KEYCLOAK_TIMEOUT_SECONDS = 5
MAX_BROKER_BODY_BYTES = 2048
LOGGER = logging.getLogger("lakehouse.token_broker")


def jwt_expiry(token: object) -> int | None:
    """Read exp from a JWT payload without treating it as a signature check."""
    if not isinstance(token, str) or len(token) > 16384:
        return None
    pieces = token.split(".")
    if len(pieces) != 3:
        return None
    try:
        payload = pieces[1] + ("=" * (-len(pieces[1]) % 4))
        claims = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return None
    expiry = claims.get("exp") if isinstance(claims, dict) else None
    if isinstance(expiry, bool) or not isinstance(expiry, (int, float)):
        return None
    return int(expiry)


def _bearer_token(header: str | None) -> str | None:
    if not header or len(header) > 17000:
        return None
    scheme, separator, token = header.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token or any(c.isspace() for c in token):
        return None
    return token


class BrokerError(Exception):
    """Safe broker failure class, deliberately excluding upstream details."""

    def __init__(self, status: int, code: str):
        super().__init__(code)
        self.status = status
        self.code = code


class LakehouseTokenBroker:
    """Resolve Hub server tokens and issue only the bound user's access JWT."""

    def __init__(self, hub, *, http_client=None, clock=time.time):
        self.hub = hub
        self.http_client = http_client or AsyncHTTPClient()
        self.clock = clock
        self._locks: dict[str, asyncio.Lock] = {}
        self._lock_users: Counter[str] = Counter()
        self.counters = Counter()
        self.latency_buckets = Counter()

    @staticmethod
    def _auth_header(token: str) -> str:
        return f"Bearer {token}"

    def _resolve_active_server(self, token: str):
        """Require the exact current API token stored on an active user spawner."""
        token_record = orm.APIToken.find(self.hub.db, token, kind="user")
        if token_record is None or token_record.user is None:
            raise BrokerError(401, "invalid_server_token")

        hub_user = self.hub.users.get(token_record.user.name)
        if hub_user is None:
            raise BrokerError(401, "invalid_server_token")
        for server_name, spawner in hub_user.spawners.items():
            server_token = getattr(spawner, "api_token", None)
            if (
                getattr(spawner, "active", False)
                and isinstance(server_token, str)
                and token_record.match(server_token)
                and token_record.match(token)
            ):
                return hub_user, server_name or "default"
        raise BrokerError(401, "inactive_server_token")

    async def _load_auth_state(self, user):
        try:
            auth_state = await user.get_auth_state()
        except Exception as error:
            raise BrokerError(503, "auth_state_unavailable") from error
        if not isinstance(auth_state, dict):
            raise BrokerError(401, "reauthentication_required")
        oauth_user = auth_state.get("oauth_user")
        if auth_state.get("_lakehouse_broker_refresh_incomplete") is True:
            raise BrokerError(401, "reauthentication_required")
        if not isinstance(oauth_user, dict) or not eligible_group_names(oauth_user.get("groups")):
            raise BrokerError(403, "current_admission_denied")
        return auth_state

    def _valid_access(self, auth_state: dict) -> tuple[str, int] | None:
        token = auth_state.get("access_token")
        expiry = jwt_expiry(token)
        if expiry is None or expiry - self.clock() <= REFRESH_WINDOW_SECONDS:
            return None
        return token, expiry

    @asynccontextmanager
    async def _user_lock(self, username: str):
        lock = self._locks.setdefault(username, asyncio.Lock())
        self._lock_users[username] += 1
        try:
            async with lock:
                yield
        finally:
            self._lock_users[username] -= 1
            if self._lock_users[username] == 0 and not lock.locked():
                self._locks.pop(username, None)
                self._lock_users.pop(username, None)

    async def issue_for_server_token(self, raw_token: str) -> tuple[str, int, str, str, str]:
        user, server_name = self._resolve_active_server(raw_token)
        auth_state = await self._load_auth_state(user)
        valid = self._valid_access(auth_state)
        if valid:
            self.counters["reused"] += 1
            return valid[0], valid[1], user.name, server_name, "reused"

        async with self._user_lock(user.name):
            auth_state = await self._load_auth_state(user)
            valid = self._valid_access(auth_state)
            if valid:
                self.counters["reused_after_lock"] += 1
                return valid[0], valid[1], user.name, server_name, "reused"
            auth_state = await self._refresh(user, auth_state)
            valid = self._valid_access(auth_state)
            if not valid:
                raise BrokerError(503, "reauthentication_required")
            self.counters["refreshed"] += 1
            return valid[0], valid[1], user.name, server_name, "refreshed"

    def _refresh_params(self, refresh_token: str) -> tuple[bytes, dict[str, str]]:
        authenticator = self.hub.authenticator
        values = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": authenticator.client_id,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
        if authenticator.basic_auth:
            credentials = f"{authenticator.client_id}:{authenticator.client_secret}".encode()
            headers["Authorization"] = "Basic " + base64.b64encode(credentials).decode("ascii")
        else:
            values["client_secret"] = authenticator.client_secret
        return urlencode(values).encode("utf-8"), headers

    async def _fetch_json(self, url: str, *, method: str, headers: dict[str, str], body: bytes | None):
        response_chunks: list[bytes] = []
        response_size = 0

        def collect_response_chunk(chunk: bytes) -> None:
            nonlocal response_size
            response_size += len(chunk)
            if response_size > 65536:
                raise ValueError("identity provider response exceeded the size limit")
            response_chunks.append(chunk)

        request = HTTPRequest(
            url=url,
            method=method,
            headers=headers,
            body=body,
            request_timeout=KEYCLOAK_TIMEOUT_SECONDS,
            connect_timeout=KEYCLOAK_TIMEOUT_SECONDS,
            follow_redirects=False,
            streaming_callback=collect_response_chunk,
        )
        response = await self.http_client.fetch(request, raise_error=False)
        if response.code != 200 or response_size > 65536:
            raise BrokerError(503, "identity_provider_unavailable")
        try:
            content_type = Message()
            content_type["content-type"] = response.headers.get("Content-Type", "")
            if content_type.get_content_type() != "application/json":
                raise ValueError("unexpected content type")
            payload = json.loads(b"".join(response_chunks))
        except (ValueError, UnicodeError, json.JSONDecodeError) as error:
            raise BrokerError(503, "identity_provider_response_invalid") from error
        if not isinstance(payload, dict):
            raise BrokerError(503, "identity_provider_response_invalid")
        return payload

    async def _refresh(self, user, auth_state: dict) -> dict:
        refresh_token = auth_state.get("refresh_token")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise BrokerError(401, "reauthentication_required")

        authenticator = self.hub.authenticator
        url = authenticator.token_url
        body, headers = self._refresh_params(refresh_token)
        started = self.clock()
        try:
            async def refresh_exchange_and_update() -> dict:
                token_info = await self._fetch_json(url, method="POST", headers=headers, body=body)
                if not isinstance(token_info.get("access_token"), str):
                    raise BrokerError(503, "identity_provider_response_invalid")
                rotated_refresh = token_info.get("refresh_token") or refresh_token
                next_state = dict(auth_state)
                next_state["access_token"] = token_info["access_token"]
                next_state["refresh_token"] = rotated_refresh
                if "id_token" in token_info:
                    next_state["id_token"] = token_info["id_token"]
                if "scope" in token_info:
                    next_state["scope"] = token_info["scope"]
                next_state["token_response"] = token_info
                next_state["_lakehouse_broker_refresh_incomplete"] = True
                # Persist rotated credentials before the additional membership check.
                await user.save_auth_state(next_state)

                access = token_info["access_token"]
                info = await self._fetch_json(
                    authenticator.userdata_url,
                    method="GET",
                    headers={"Authorization": self._auth_header(access), "Accept": "application/json"},
                    body=None,
                )
                username = authenticator.normalize_username(info.get(authenticator.username_claim, ""))
                next_state["oauth_user"] = info
                next_state.pop("_lakehouse_broker_refresh_incomplete", None)
                await user.save_auth_state(next_state)
                if username != user.name or not eligible_group_names(info.get("groups")):
                    raise BrokerError(403, "current_admission_denied")
                self.counters["refresh_seconds_millis"] += int((self.clock() - started) * 1000)
                return next_state

            return await asyncio.wait_for(
                refresh_exchange_and_update(), timeout=KEYCLOAK_TIMEOUT_SECONDS
            )
        except BrokerError:
            raise
        except (TimeoutError, asyncio.TimeoutError) as error:
            self.counters["refresh_timeouts"] += 1
            # A refresh token may have rotated despite a lost response. Re-read once;
            # never replay the old token after an ambiguous timeout.
            refreshed = await self._load_auth_state(user)
            valid = self._valid_access(refreshed)
            if valid:
                self.counters["ambiguous_rotation_found"] += 1
                return refreshed
            raise BrokerError(503, "reauthentication_required") from error
        except Exception as error:
            raise BrokerError(503, "identity_provider_unavailable") from error


class BrokerHandler(RequestHandler):
    def initialize(self, broker: LakehouseTokenBroker, *, is_health: bool = False):
        self.broker = broker
        self.is_health = is_health

    def set_default_headers(self):
        self.set_header("Cache-Control", "no-store")
        self.set_header("Pragma", "no-cache")
        self.set_header("X-Content-Type-Options", "nosniff")

    async def get(self):
        if self.is_health and self.broker is not None:
            self.set_status(200)
            self.write({"status": "ready"})
            self.finish()
            return
        self.set_status(405)
        self.finish()

    async def post(self):
        correlation_id = uuid.uuid4().hex
        started = time.monotonic()
        username = "-"
        server_name = "-"
        decision = "denied"
        outcome = "denied"
        self.set_header("X-Correlation-ID", correlation_id)
        try:
            if len(self.request.body) > MAX_BROKER_BODY_BYTES:
                raise BrokerError(413, "request_too_large")
            token = _bearer_token(self.request.headers.get("Authorization"))
            if token is None:
                raise BrokerError(401, "invalid_server_token")
            access_token, expires_at, username, server_name, decision = await self.broker.issue_for_server_token(token)
            outcome = "issued"
            self.set_status(200)
            self.write({"access_token": access_token, "expires_at": expires_at})
            self.finish()
        except BrokerError as error:
            outcome = error.code
            self.set_status(error.status)
            self.write({"error": error.code, "correlation_id": correlation_id})
            self.finish()
        except Exception:
            outcome = "internal_error"
            self.set_status(503)
            self.write({"error": "broker_unavailable", "correlation_id": correlation_id})
            self.finish()
        finally:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            bucket = "lt_100ms" if elapsed_ms < 100 else "lt_1s" if elapsed_ms < 1000 else "gte_1s"
            self.broker.latency_buckets[bucket] += 1
            self.broker.counters["requests"] += 1
            self.broker.counters[f"outcome_{outcome}"] += 1
            LOGGER.info(
                "token_broker_request correlation_id=%s user=%s server=%s decision=%s outcome=%s elapsed_ms=%d",
                correlation_id,
                username,
                server_name,
                decision,
                outcome,
                elapsed_ms,
            )


def broker_application(broker: LakehouseTokenBroker) -> Application:
    return Application(
        [(r"/api/v1/token", BrokerHandler, {"broker": broker}),
         (r"/healthz", BrokerHandler, {"broker": broker, "is_health": True})],
        debug=False,
    )


def broker_ssl_context(cert_path: str, key_path: str) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    return context
