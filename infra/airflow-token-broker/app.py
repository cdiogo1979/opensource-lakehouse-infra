"""Private run-scoped Keycloak token broker for Airflow Spark jobs.

Each data product with a repo has its own writer. A run's DAG ID starts with its
bundle name (``<product>-main-...`` or ``<product>-uat-...``), so it names the
product; the broker confirms through the Airflow API (as a read-only Viewer)
that the DAG really comes from that product's bundle, and only then issues and
renews tokens for that product's writer. DAG code never sees a credential.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict, Field

LOGGER = logging.getLogger("airflow_token_broker")
UTC = timezone.utc
RUNS = Counter("airflow_broker_runs_total", "Run registrations", ["outcome"])
RENEWALS = Counter("airflow_broker_renewals_total", "Token renewals", ["outcome"])
REJECTIONS = Counter("airflow_broker_rejections_total", "Rejected requests", ["reason"])
REQUESTS = Histogram("airflow_broker_request_seconds", "Broker request latency", ["operation"])
# Same rule as infra/products/data_products.DAG_ID_PATTERN (checked by a contract test).
DAG_ID_PATTERN = re.compile(r"^(?P<product>[a-z][a-z0-9]{1,19})-(?P<env>main|uat)-(?P<workload>.+)$")
REFUSALS = ("unknown_product", "unknown_dag", "bundle_mismatch")


@dataclass(frozen=True)
class Writer:
    username: str
    group: str
    password: str


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dag_id: str = Field(min_length=1, max_length=250, pattern=r"^[A-Za-z0-9_.-]+$")
    run_id: str = Field(min_length=1, max_length=512, pattern=r"^[A-Za-z0-9_.:+-]+$")


class RenewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_handle: str = Field(min_length=22, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


@dataclass
class Registration:
    run_handle: str
    run_key: tuple[str, str]
    verifier: bytes
    encrypted_capability: bytes
    expires_at: datetime
    status: str = "ACTIVE"
    terminal_at: datetime | None = None
    product: str = ""


def _read_secret(path_text: str, minimum_length: int = 1) -> str:
    path = Path(path_text)
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("Required protected broker credential is unavailable.")
    value = path.read_text(encoding="utf-8").strip()
    if len(value) < minimum_length:
        raise RuntimeError("Required protected broker credential is invalid.")
    return value


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("malformed token")
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    result = json.loads(base64.urlsafe_b64decode(payload))
    if not isinstance(result, dict):
        raise ValueError("invalid token payload")
    return result


def load_writers(directory: str) -> dict[str, Writer]:
    """Product -> writer, from writers.json and the password files staged beside it."""
    base = Path(directory)
    try:
        listing = json.loads((base / "writers.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError("The staged writer list is unavailable.") from error
    writers = {}
    for product, entry in listing.items():
        name = Path(entry["password_file"]).name
        writers[product] = Writer(entry["username"], entry["group"], _read_secret(str(base / name), 8))
    return writers


def problem(status: int, code: str, title: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={"type": "about:blank", "title": title, "status": status, "code": code, "detail": detail},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.control_token = _read_secret(os.environ["AIRFLOW_BROKER_CONTROL_TOKEN_FILE"], 32)
    app.state.writer_secret = _read_secret(os.environ["KEYCLOAK_WRITER_CLIENT_SECRET_FILE"], 16)
    app.state.writers = load_writers(os.environ.get("AIRFLOW_BROKER_WRITERS_DIR", "/run/secrets/airflow-writers"))
    app.state.airflow_url = os.getenv("AIRFLOW_API_URL", "http://airflow-api-server:8080").rstrip("/")
    app.state.viewer_username = os.getenv("AIRFLOW_BROKER_VIEWER_USERNAME", "lakehouse-broker")
    app.state.viewer_password = _read_secret(os.environ["AIRFLOW_BROKER_VIEWER_PASSWORD_FILE"], 16)
    app.state.viewer_token = None
    app.state.viewer_token_expires = 0.0
    app.state.encryption_key = AESGCM.generate_key(bit_length=256)
    app.state.registrations_by_key = {}
    app.state.registrations_by_handle = {}
    app.state.state_lock = asyncio.Lock()
    app.state.max_active = int(os.getenv("AIRFLOW_BROKER_MAX_ACTIVE_RUNS", "10"))
    app.state.max_run_seconds = int(os.getenv("AIRFLOW_BROKER_MAX_RUN_SECONDS", "86400"))
    if app.state.max_active < 10 or app.state.max_run_seconds < 1:
        raise RuntimeError("Broker active-run capacity and maximum run duration are invalid.")
    app.state.keycloak_url = os.getenv("KEYCLOAK_URL", "http://keycloak:8080").rstrip("/")
    app.state.realm = os.getenv("KEYCLOAK_REALM", "lakehouse")
    app.state.keycloak_issuer = os.getenv(
        "KEYCLOAK_ISSUER", f"{app.state.keycloak_url}/realms/{app.state.realm}"
    ).rstrip("/")
    app.state.client_id = os.getenv("KEYCLOAK_WRITER_CLIENT_ID", "lakehouse-writer")
    app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=1.5))
    try:
        yield
    finally:
        await app.state.http.aclose()
        app.state.encryption_key = b""


app = FastAPI(title="Airflow Writer Token Broker", version="1.0.0", lifespan=lifespan, docs_url=None, redoc_url=None)


@app.middleware("http")
async def request_metrics(request: Request, call_next):
    operation = "register" if request.url.path == "/v1/runs" else "renew" if request.url.path == "/v1/runs/token" else "revoke" if request.method == "DELETE" else "other"
    started = time.monotonic()
    try:
        response = await call_next(request)
        return response
    finally:
        REQUESTS.labels(operation).observe(time.monotonic() - started)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, _exc: RequestValidationError):
    REJECTIONS.labels("invalid_request").inc()
    return problem(400, "invalid_request", "Invalid request", "The request did not match the broker contract.")


async def require_control(authorization: str | None = Header(default=None)) -> None:
    expected = "Bearer " + app.state.control_token
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(401, detail="invalid_control_credential")


def _problem_for_http_error(error: HTTPException) -> JSONResponse:
    if error.status_code == 401:
        code, title, detail = "invalid_control_credential", "Unauthorized", "A valid broker credential is required."
    elif error.status_code == 403 and error.detail in REFUSALS:
        code, title = error.detail, "Forbidden"
        detail = {
            "unknown_product": "The DAG ID does not name a data product with an Airflow writer.",
            "unknown_dag": "Airflow does not know this DAG.",
            "bundle_mismatch": "The DAG does not come from its product's bundle.",
        }[code]
    elif error.status_code == 404:
        code, title, detail = "run_not_found", "Not found", "The run authorization is unavailable."
    elif error.status_code == 409:
        code, title, detail = "run_terminal", "Conflict", "The run authorization is no longer active."
    elif error.status_code == 429:
        code, title, detail = "capacity_exhausted", "Capacity exhausted", "The broker has reached its active run capacity."
    elif error.status_code == 502:
        code, title, detail = "identity_provider_failure", "Identity provider failure", "The writer token could not be issued."
    else:
        code, title, detail = "service_unavailable", "Service unavailable", "The broker cannot complete the request."
    REJECTIONS.labels(code).inc()
    return problem(error.status_code, code, title, detail)


@app.exception_handler(HTTPException)
async def http_error_handler(_request: Request, exc: HTTPException):
    return _problem_for_http_error(exc)


def _purge_expired() -> None:
    now = datetime.now(UTC)
    for run_key, item in list(app.state.registrations_by_key.items()):
        if item.status == "ACTIVE" and item.expires_at <= now:
            item.status = "EXPIRED"
            item.terminal_at = now
            item.encrypted_capability = b""
            app.state.registrations_by_handle.pop(item.run_handle, None)
        elif item.status != "ACTIVE" and item.terminal_at is not None and item.terminal_at + timedelta(seconds=app.state.max_run_seconds) <= now:
            del app.state.registrations_by_key[run_key]


def _decrypt_capability(item: Registration) -> str:
    if not item.encrypted_capability:
        raise ValueError("replay data unavailable")
    nonce, ciphertext = item.encrypted_capability[:12], item.encrypted_capability[12:]
    raw = AESGCM(app.state.encryption_key).decrypt(nonce, ciphertext, item.run_handle.encode())
    return raw.decode("ascii")


def _jwt_expiry(token: str, expires_in: Any, writer: Writer) -> datetime:
    claims = _decode_jwt_payload(token)
    if claims.get("iss") != app.state.keycloak_issuer:
        raise ValueError("unexpected token issuer")
    if claims.get("azp") != app.state.client_id:
        raise ValueError("unexpected token client")
    if claims.get("preferred_username") != writer.username:
        raise ValueError("unexpected token user")
    role_claim = claims.get("resource_access", {}).get("polaris", {}).get("roles", [])
    if writer.group not in role_claim:
        raise ValueError("writer role missing")
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)) or not isinstance(expires_in, (int, float)) or expires_in <= 0:
        raise ValueError("invalid expiry")
    expiry = datetime.fromtimestamp(exp, UTC)
    now = datetime.now(UTC)
    if expiry <= now or expiry > now + timedelta(seconds=3605):
        raise ValueError("unexpected token lifetime")
    if abs((expiry - now).total_seconds() - float(expires_in)) > 15:
        raise ValueError("inconsistent expiry")
    return expiry


async def _issue_token(writer: Writer) -> tuple[str, datetime]:
    url = f"{app.state.keycloak_url}/realms/{app.state.realm}/protocol/openid-connect/token"
    try:
        response = await app.state.http.post(
            url,
            data={
                "grant_type": "password",
                "client_id": app.state.client_id,
                "client_secret": app.state.writer_secret,
                "username": writer.username,
                "password": writer.password,
                "scope": "openid",
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        body = response.json()
        token = body.get("access_token")
        expiry = _jwt_expiry(token, body.get("expires_in"), writer) if isinstance(token, str) else None
        if expiry is None:
            raise ValueError("invalid access token")
        return token, expiry
    except (httpx.HTTPError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        LOGGER.warning("Keycloak writer-token request failed (%s).", type(error).__name__)
        raise HTTPException(502, detail="identity_provider_failure") from None


def _resolve_writer(dag_id: str) -> tuple[str, str, Writer]:
    """(product, env, writer) named by the DAG ID, or 403 unknown_product."""
    match = DAG_ID_PATTERN.fullmatch(dag_id)
    writer = app.state.writers.get(match.group("product")) if match else None
    if writer is None:
        LOGGER.warning("Refused run registration: DAG %s names no product with a writer.", dag_id)
        raise HTTPException(403, detail="unknown_product")
    return match.group("product"), match.group("env"), writer


async def _airflow_token() -> str:
    """The Viewer's Airflow API token, cached until 60 s before it expires."""
    if app.state.viewer_token and time.monotonic() < app.state.viewer_token_expires:
        return app.state.viewer_token
    response = await app.state.http.post(
        f"{app.state.airflow_url}/auth/token",
        json={"username": app.state.viewer_username, "password": app.state.viewer_password},
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    try:
        lifetime = int(_decode_jwt_payload(token).get("exp", 0)) - int(time.time())
    except (ValueError, TypeError):
        lifetime = 0
    app.state.viewer_token = token
    app.state.viewer_token_expires = time.monotonic() + max(lifetime - 60, 0)
    return token


async def _verify_bundle(dag_id: str, product: str, env: str) -> None:
    """The DAG must come from <product>-<env>; Airflow answers which bundle holds it."""
    try:
        for attempt in (1, 2):
            token = await _airflow_token()
            response = await app.state.http.get(
                f"{app.state.airflow_url}/api/v2/dags/{dag_id}", headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code not in (401, 403):
                break
            # start-airflow recreates the Viewer, so a cached token can outlive its user
            # (Airflow then answers 403): drop it and retry once with a new one.
            app.state.viewer_token = None
            if attempt == 1:
                LOGGER.info("Airflow refused the cached Viewer token (%s); signing in again.", response.status_code)
        if response.status_code == 404:
            LOGGER.warning("Refused run registration: Airflow does not know DAG %s.", dag_id)
            raise HTTPException(403, detail="unknown_dag")
        response.raise_for_status()
        bundle = response.json().get("bundle_name")
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        LOGGER.warning("Airflow bundle check failed (%s).", type(error).__name__)
        raise HTTPException(503, detail="service_unavailable") from None
    if bundle != f"{product}-{env}":
        LOGGER.warning("Refused run registration: DAG %s is in bundle %s, not %s-%s.", dag_id, bundle, product, env)
        raise HTTPException(403, detail="bundle_mismatch")


def _run_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=app.state.max_run_seconds)


@app.get("/health/live", include_in_schema=False)
async def live():
    return {"status": "live"}


@app.get("/health/ready", include_in_schema=False)
async def ready():
    if not app.state.encryption_key or not app.state.control_token or not app.state.writer_secret or not app.state.viewer_password:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/runs", dependencies=[Depends(require_control)])
async def register_run(body: RegisterRequest, response: Response):
    product, env, writer = _resolve_writer(body.dag_id)
    await _verify_bundle(body.dag_id, product, env)
    async with app.state.state_lock:
        _purge_expired()
        key = (body.dag_id, body.run_id)
        existing = app.state.registrations_by_key.get(key)
        if existing and existing.status != "ACTIVE":
            raise HTTPException(409, detail="run_terminal")
        if not existing and len(app.state.registrations_by_handle) >= app.state.max_active:
            raise HTTPException(429, detail="capacity_exhausted")
        if existing:
            try:
                capability = _decrypt_capability(existing)
            except (ValueError, TypeError):
                raise HTTPException(503, detail="service_unavailable") from None
            token, token_expiry = await _issue_token(writer)
            RUNS.labels("replayed").inc()
            response.status_code = 200
            return {"run_handle": existing.run_handle, "renewal_capability": capability, "token_type": "Bearer", "access_token": token, "expires_at": token_expiry.isoformat()}

        token, token_expiry = await _issue_token(writer)
        run_handle = _b64(secrets.token_bytes(16))
        capability_bytes = secrets.token_bytes(32)
        capability = _b64(capability_bytes)
        nonce = secrets.token_bytes(12)
        encrypted = nonce + AESGCM(app.state.encryption_key).encrypt(nonce, capability.encode("ascii"), run_handle.encode())
        registration = Registration(run_handle, key, hashlib.sha256(capability.encode("ascii")).digest(), encrypted, _run_expiry(), product=product)
        app.state.registrations_by_key[key] = registration
        app.state.registrations_by_handle[run_handle] = registration
        RUNS.labels("created").inc()
        response.status_code = 201
        return {"run_handle": run_handle, "renewal_capability": capability, "token_type": "Bearer", "access_token": token, "expires_at": token_expiry.isoformat()}


@app.post("/v1/runs/token")
async def renew_run_token(body: RenewRequest, authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, detail="invalid_run_capability")
    supplied = authorization[7:]
    async with app.state.state_lock:
        _purge_expired()
        registration = app.state.registrations_by_handle.get(body.run_handle)
        if registration is None:
            raise HTTPException(404, detail="run_not_found")
        if registration.status != "ACTIVE" or registration.expires_at <= datetime.now(UTC):
            raise HTTPException(409, detail="run_terminal")
        supplied_hash = hashlib.sha256(supplied.encode("utf-8")).digest()
        if not hmac.compare_digest(registration.verifier, supplied_hash):
            raise HTTPException(401, detail="invalid_run_capability")
        try:
            writer = app.state.writers.get(registration.product)
            if writer is None:
                raise HTTPException(503, detail="service_unavailable")
            token, expiry = await _issue_token(writer)
        except HTTPException:
            RENEWALS.labels("failure").inc()
            raise
        RENEWALS.labels("success").inc()
        return {"token_type": "Bearer", "access_token": token, "expires_at": expiry.isoformat()}


@app.delete("/v1/runs/{run_handle}", status_code=204, dependencies=[Depends(require_control)])
async def revoke_run(run_handle: str):
    async with app.state.state_lock:
        _purge_expired()
        registration = app.state.registrations_by_handle.pop(run_handle, None)
        if registration is None:
            return Response(status_code=204)
        registration.status = "REVOKED"
        registration.terminal_at = datetime.now(UTC)
        registration.encrypted_capability = b""
    return Response(status_code=204)
