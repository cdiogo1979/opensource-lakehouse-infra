"""Per-product writer selection in the Airflow token broker (FR-4, BR-3, P4).

Keycloak and the Airflow API are faked with an httpx MockTransport. The broker's
dependencies (FastAPI) live only in its image, so the behavioral tests skip
locally; run them with scripts/verify/broker-unit-tests.sh. The contract tests
at the top need only the standard library.
"""

import base64
import importlib.util
import json
import re
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import parse_qs

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "infra/airflow-token-broker/app.py"
SOURCE = APP.read_text(encoding="utf-8")


def test_broker_dag_id_rule_matches_the_product_model():
    sys.path.insert(0, str(ROOT / "infra/products"))
    import data_products

    broker = re.search(r'DAG_ID_PATTERN = re\.compile\(r"(.+)"\)', SOURCE).group(1)
    assert broker == data_products.DAG_ID_PATTERN.pattern


def test_broker_holds_no_fixed_writer():
    assert "srv-default-writer" not in SOURCE and "role-default-writer" not in SOURCE
    assert "KEYCLOAK_WRITER_PASSWORD_FILE" not in SOURCE and "KEYCLOAK_WRITER_USERNAME" not in SOURCE
    compose = (ROOT / "compose.airflow.yml").read_text(encoding="utf-8")
    broker = compose[compose.index("  airflow-token-broker:\n"):]
    assert "./.runtime/container-mounts/airflow-writers:/run/secrets/airflow-writers:ro" in broker
    assert "AIRFLOW_API_URL: http://airflow-api-server:8080" in broker
    assert "srv_default_writer_password" not in compose


def test_refusals_are_logged_without_secrets():
    for line in re.findall(r"LOGGER\.warning\((.+)\)", SOURCE):
        assert "password" not in line and "token" not in line.split(",", 1)[-1]


fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402
from hypothesis import HealthCheck, given, settings, strategies as st  # noqa: E402

ISSUER = "http://keycloak:8080/realms/lakehouse"
CONTROL = "c" * 40
WRITERS = {
    "default": {"username": "srv-default-writer", "group": "role-default-writer", "password_file": "srv-default-writer-password"},
    "sales": {"username": "srv-sales-writer", "group": "role-sales-writer", "password_file": "srv-sales-writer-password"},
}


def jwt(claims):
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"e30.{body}.signature"


class FakeUpstreams:
    """Keycloak password grants and the Airflow API, as the broker sees them."""

    def __init__(self):
        self.dags = {}
        self.airflow_status = None
        self.viewer_logins = 0
        self.first_valid_login = 0
        self.issued_to = []

    def reset(self):
        self.__init__()

    def __call__(self, request):
        path = request.url.path
        if path == "/auth/token":
            self.viewer_logins += 1
            return httpx.Response(201, json={"access_token": jwt({"exp": int(time.time()) + 3600, "login": self.viewer_logins})})
        if path.startswith("/api/v2/dags/"):
            if self.airflow_status:
                return httpx.Response(self.airflow_status)
            # Tokens issued before the Viewer was recreated are refused, as Airflow does.
            payload = request.headers["Authorization"].split(".")[1]
            login = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["login"]
            if login < self.first_valid_login:
                return httpx.Response(403, json={"detail": "Forbidden"})
            dag_id = path.rsplit("/", 1)[1]
            if dag_id not in self.dags:
                return httpx.Response(404, json={"detail": "not found"})
            return httpx.Response(200, json={"dag_id": dag_id, "bundle_name": self.dags[dag_id]})
        if path.endswith("/protocol/openid-connect/token"):
            form = {key: values[0] for key, values in parse_qs(request.content.decode()).items()}
            entry = next(item for item in WRITERS.values() if item["username"] == form["username"])
            assert form["password"] == f"pw-{form['username']}"
            self.issued_to.append(form["username"])
            claims = {"iss": ISSUER, "azp": "lakehouse-writer", "preferred_username": form["username"],
                      "resource_access": {"polaris": {"roles": [entry["group"]]}}, "exp": int(time.time()) + 300}
            return httpx.Response(200, json={"access_token": jwt(claims), "expires_in": 300})
        return httpx.Response(500)


@pytest.fixture(scope="module")
def broker(tmp_path_factory):
    base = tmp_path_factory.mktemp("broker")
    writers = base / "writers"
    writers.mkdir()
    (writers / "writers.json").write_text(json.dumps(WRITERS))
    for entry in WRITERS.values():
        (writers / entry["password_file"]).write_text(f"pw-{entry['username']}")
    secrets = {"AIRFLOW_BROKER_CONTROL_TOKEN_FILE": CONTROL, "KEYCLOAK_WRITER_CLIENT_SECRET_FILE": "s" * 20,
               "AIRFLOW_BROKER_VIEWER_PASSWORD_FILE": "v" * 20}
    patch = pytest.MonkeyPatch()
    for name, value in secrets.items():
        (base / name).write_text(value)
        patch.setenv(name, str(base / name))
    patch.setenv("AIRFLOW_BROKER_WRITERS_DIR", str(writers))
    patch.setenv("AIRFLOW_BROKER_MAX_ACTIVE_RUNS", "100000")
    spec = importlib.util.spec_from_file_location("airflow_token_broker_app", APP)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    fake = FakeUpstreams()
    with TestClient(module.app) as client:
        module.app.state.http = httpx.AsyncClient(transport=httpx.MockTransport(fake))
        yield client, fake
    patch.undo()


def register(client, dag_id):
    return client.post("/v1/runs", json={"dag_id": dag_id, "run_id": uuid.uuid4().hex},
                       headers={"Authorization": f"Bearer {CONTROL}"})


def subject(token):
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["preferred_username"]


def test_each_product_gets_its_own_writer_and_renewals_keep_it(broker):
    client, fake = broker
    fake.reset()
    fake.dags = {"default-main-test_environment": "default-main", "sales-uat-load": "sales-uat"}
    first = register(client, "default-main-test_environment")
    second = register(client, "sales-uat-load")
    assert (first.status_code, second.status_code) == (201, 201)
    assert subject(first.json()["access_token"]) == "srv-default-writer"
    assert subject(second.json()["access_token"]) == "srv-sales-writer"
    renewed = client.post("/v1/runs/token", json={"run_handle": second.json()["run_handle"]},
                          headers={"Authorization": f"Bearer {second.json()['renewal_capability']}"})
    assert renewed.status_code == 200 and subject(renewed.json()["access_token"]) == "srv-sales-writer"
    assert fake.viewer_logins == 1  # the Viewer token is cached


@pytest.mark.parametrize("dag_id", ["main-test_environment", "nobody-main-load", "default-dev-load", "Default-main-x"])
def test_dag_ids_without_a_product_writer_are_refused_before_any_call(broker, dag_id):
    client, fake = broker
    fake.reset()
    response = register(client, dag_id)
    assert response.status_code == 403 and response.json()["code"] == "unknown_product"
    assert fake.issued_to == [] and fake.viewer_logins == 0


def test_unknown_dag_and_wrong_bundle_are_refused_without_a_token(broker):
    client, fake = broker
    fake.reset()
    fake.dags = {"sales-main-load": "default-main", "default-uat-load": "default-main"}
    assert register(client, "default-main-missing").json()["code"] == "unknown_dag"
    for dag_id in fake.dags:
        response = register(client, dag_id)
        assert response.status_code == 403 and response.json()["code"] == "bundle_mismatch"
    assert fake.issued_to == []


def test_a_refused_cached_viewer_token_is_replaced_once(broker):
    """start-airflow recreates the Viewer; the cached token then gets 403 and is replaced (CR-3)."""
    client, fake = broker
    fake.reset()
    client.app.state.viewer_token = None  # the module-scoped broker may cache an earlier test's token
    fake.dags = {"default-main-test_environment": "default-main"}
    assert register(client, "default-main-test_environment").status_code == 201
    logins = fake.viewer_logins
    fake.first_valid_login = logins + 1  # the Viewer was recreated: earlier tokens are refused
    assert register(client, "default-main-test_environment").status_code == 201
    assert fake.viewer_logins == logins + 1
    assert register(client, "default-main-test_environment").status_code == 201
    assert fake.viewer_logins == logins + 1  # the new token is cached again


def test_a_viewer_refused_even_with_a_new_token_is_unavailable_after_one_retry(broker):
    client, fake = broker
    fake.reset()
    fake.airflow_status = 403
    response = register(client, "default-main-test_environment")
    assert response.status_code == 503 and response.json()["code"] == "service_unavailable"
    assert fake.viewer_logins == 1 and fake.issued_to == []  # the retry signed in once; no writer token


def test_airflow_failure_is_unavailable_not_permitted(broker):
    client, fake = broker
    fake.reset()
    fake.airflow_status = 500
    response = register(client, "default-main-test_environment")
    assert response.status_code == 503 and response.json()["code"] == "service_unavailable"
    assert fake.issued_to == []


@settings(print_blob=True, max_examples=60, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(product=st.sampled_from(["default", "sales", "nobody"]), env=st.sampled_from(["main", "uat"]),
       bundle=st.sampled_from(["default-main", "default-uat", "sales-main", "sales-uat", None]),
       workload=st.from_regex(r"[a-z0-9_]{1,20}", fullmatch=True))
def test_p4_a_token_is_issued_only_to_the_writer_of_the_dags_own_bundle(broker, product, env, bundle, workload):
    client, fake = broker
    fake.reset()
    dag_id = f"{product}-{env}-{workload}"
    if bundle:
        fake.dags = {dag_id: bundle}
    response = register(client, dag_id)
    if product in WRITERS and bundle == f"{product}-{env}":
        assert response.status_code == 201
        assert fake.issued_to == [WRITERS[product]["username"]]
    else:
        assert response.status_code == 403
        assert fake.issued_to == []
