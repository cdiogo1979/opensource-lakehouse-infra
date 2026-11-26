"""lakehouse_starrocks.connect(): settings, token renewal, login arguments, no secrets out (AC-17 to AC-21)."""

import base64
import json
import sys
import types
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra/workload-python/python"))
import lakehouse_starrocks as ls  # noqa: E402

SECRET = "SuperSecretValue-123"


def jwt(exp):
    def part(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")
    return f"{part({'alg': 'RS256'})}.{part({'exp': exp, 'sub': 'x'})}.sig"


@pytest.fixture
def ca(tmp_path):
    path = tmp_path / "starrocks-ca.crt"
    path.write_text("cert")
    return str(path)


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.setattr(ls, "_renewed_token", None)


def airflow_env(ca, **extra):
    return {"LAKEHOUSE_TOKEN_PROVIDER": "airflow", "LAKEHOUSE_STARROCKS_USER": "srv-audit-writer", "LAKEHOUSE_STARROCKS_CA": ca, **extra}


def test_airflow_and_jupyter_settings(ca):
    assert ls.connection_settings(airflow_env(ca)) == ls.Settings("airflow", "starrocks-fe", 9030, ca, "srv-audit-writer")
    jupyter = {"JUPYTERHUB_USER": "a36abc37-2649-4e83-9bc8-35a5ea04543d", "LAKEHOUSE_STARROCKS_USER": "maria-owner", "LAKEHOUSE_STARROCKS_CA": ca,
               "LAKEHOUSE_STARROCKS_HOST": "fe", "LAKEHOUSE_STARROCKS_PORT": "9031"}
    assert ls.connection_settings(jupyter) == ls.Settings("jupyter", "fe", 9031, ca, "maria-owner")
    # Never the Hub's user name (the Keycloak ID): without the Hub's username, connect() refuses.
    with pytest.raises(ls.StarRocksConnectionError, match="LAKEHOUSE_STARROCKS_USER"):
        ls.connection_settings({k: v for k, v in jupyter.items() if k != "LAKEHOUSE_STARROCKS_USER"})


@pytest.mark.parametrize(
    "change, message",
    [
        ({"LAKEHOUSE_TOKEN_PROVIDER": None}, "Airflow run or a JupyterHub server"),
        ({"LAKEHOUSE_STARROCKS_USER": ""}, "LAKEHOUSE_STARROCKS_USER"),
        ({"LAKEHOUSE_STARROCKS_USER": "x'@'%"}, "LAKEHOUSE_STARROCKS_USER"),
        ({"LAKEHOUSE_STARROCKS_PORT": "99999"}, "LAKEHOUSE_STARROCKS_PORT"),
        ({"LAKEHOUSE_STARROCKS_HOST": "fe;rm"}, "LAKEHOUSE_STARROCKS_HOST"),
        ({"LAKEHOUSE_STARROCKS_CA": "/nope"}, "LAKEHOUSE_STARROCKS_CA"),
    ],
)
def test_missing_or_invalid_settings_are_refused(ca, change, message):
    environ = {k: v for k, v in {**airflow_env(ca), **change}.items() if v is not None}
    with pytest.raises(ls.StarRocksConnectionError, match=message):
        ls.connection_settings(environ)


def test_the_initial_token_is_used_while_valid_and_renewed_when_close_to_expiry(ca, monkeypatch, tmp_path):
    broker_ca = tmp_path / "broker-ca.crt"
    broker_ca.write_text("cert")
    environ = airflow_env(ca, LAKEHOUSE_INITIAL_ACCESS_TOKEN=jwt(1000), LAKEHOUSE_TOKEN_BROKER_URL="https://broker:8443", LAKEHOUSE_TOKEN_BROKER_CA=str(broker_ca),
                          LAKEHOUSE_RUN_HANDLE="h" * 22, LAKEHOUSE_RUN_CAPABILITY=SECRET)
    assert ls.current_writer_token(environ, clock=lambda: 500) == jwt(1000)
    requests = []

    class Response:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, size):
            return self.body

    def fake_urlopen(request, timeout, context):
        requests.append(request)
        return Response(json.dumps({"access_token": jwt(5000), "expires_at": "x"}).encode())

    monkeypatch.setattr(ls, "urlopen", fake_urlopen)
    monkeypatch.setattr(ls.ssl, "create_default_context", lambda cafile: object())
    assert ls.current_writer_token(environ, clock=lambda: 950) == jwt(5000)
    (request,) = requests
    assert request.full_url == "https://broker:8443/v1/runs/token" and request.get_header("Authorization") == f"Bearer {SECRET}"
    assert json.loads(request.data) == {"run_handle": "h" * 22}
    assert ls.current_writer_token(environ, clock=lambda: 960) == jwt(5000) and len(requests) == 1  # kept in the process


def test_a_failed_renewal_raises_without_secrets(ca, monkeypatch, tmp_path):
    broker_ca = tmp_path / "broker-ca.crt"
    broker_ca.write_text("cert")
    environ = airflow_env(ca, LAKEHOUSE_INITIAL_ACCESS_TOKEN=jwt(1), LAKEHOUSE_TOKEN_BROKER_URL="https://broker:8443", LAKEHOUSE_TOKEN_BROKER_CA=str(broker_ca),
                          LAKEHOUSE_RUN_HANDLE="h" * 22, LAKEHOUSE_RUN_CAPABILITY=SECRET)
    monkeypatch.setattr(ls, "urlopen", lambda *a, **k: (_ for _ in ()).throw(ls.URLError(SECRET)))
    monkeypatch.setattr(ls.ssl, "create_default_context", lambda cafile: object())
    with pytest.raises(ls.StarRocksConnectionError) as error:
        ls.current_writer_token(environ, clock=lambda: 100)
    assert SECRET not in str(error.value)
    with pytest.raises(ls.StarRocksConnectionError, match="settings are incomplete"):
        ls.current_writer_token({**environ, "LAKEHOUSE_TOKEN_BROKER_URL": "http://broker"}, clock=lambda: 100)


def fake_pymysql(monkeypatch):
    calls = []
    module = types.SimpleNamespace(connect=lambda **kwargs: calls.append(kwargs) or "connection")
    monkeypatch.setitem(sys.modules, "pymysql", module)
    monkeypatch.setattr(ls.ssl, "create_default_context", lambda cafile: ("context", cafile))
    return calls


def test_airflow_login_uses_the_token_and_the_oidc_client_over_verified_tls(ca, monkeypatch):
    calls = fake_pymysql(monkeypatch)
    token = jwt(10**10)
    assert ls.connect(environ=airflow_env(ca, LAKEHOUSE_INITIAL_ACCESS_TOKEN=token)) == "connection"
    (kwargs,) = calls
    assert kwargs["user"] == "srv-audit-writer" and kwargs["password"] == token and kwargs["ssl"] == ("context", ca)
    assert kwargs["auth_plugin_map"] == {b"authentication_openid_connect_client": ls._OpenIdConnect}
    assert kwargs["autocommit"] is True and kwargs["connect_timeout"] == 15 and kwargs["host"] == "starrocks-fe" and kwargs["port"] == 9030


def test_jupyter_login_asks_the_password_every_time_and_keeps_nothing(ca, monkeypatch):
    calls = fake_pymysql(monkeypatch)
    prompts = []
    environ = {"JUPYTERHUB_USER": "a36abc37-2649-4e83-9bc8-35a5ea04543d", "LAKEHOUSE_STARROCKS_USER": "maria-owner", "LAKEHOUSE_STARROCKS_CA": ca}
    for _ in range(2):
        ls.connect(environ=environ, password_prompt=lambda text: prompts.append(text) or SECRET)
    assert prompts == ["StarRocks password for maria-owner: "] * 2
    assert all(call["password"] == SECRET and "auth_plugin_map" not in call for call in calls)
    assert SECRET not in json.dumps({k: v for k, v in vars(ls).items() if isinstance(v, str)})
    with pytest.raises(ls.StarRocksConnectionError, match="No StarRocks password"):
        ls.connect(environ=environ, password_prompt=lambda text: "")


# --- Properties (PBT-03, PBT-07) ---------------------------------------------------------


@settings(max_examples=200, deadline=None)
@given(st.integers(0, 10**10), st.integers(0, 10**10), st.integers(0, 3600))
def test_expiry_check_is_exact(exp, now, margin):
    assert ls.token_expires_soon(jwt(exp), now, margin) == (exp - now <= margin)


@settings(max_examples=100, deadline=None)
@given(st.text(max_size=40))
def test_unreadable_tokens_always_count_as_expiring(text):
    if ls.token_expiry(text) is None:
        assert ls.token_expires_soon(text, 0)


@settings(max_examples=100, deadline=None)
@given(st.dictionaries(st.sampled_from(["LAKEHOUSE_TOKEN_PROVIDER", "LAKEHOUSE_STARROCKS_USER", "JUPYTERHUB_USER", "LAKEHOUSE_STARROCKS_HOST", "LAKEHOUSE_STARROCKS_PORT", "LAKEHOUSE_STARROCKS_CA", "LAKEHOUSE_INITIAL_ACCESS_TOKEN"]), st.text(max_size=12)))
def test_settings_are_complete_or_refused_without_echoing_values(environ):
    environ = {**environ, "LAKEHOUSE_INITIAL_ACCESS_TOKEN": SECRET}
    try:
        result = ls.connection_settings(environ)
    except ls.StarRocksConnectionError as error:
        assert SECRET not in str(error)
        return
    assert result.user and 1 <= result.port <= 65535 and Path(result.ca_file).is_file()
