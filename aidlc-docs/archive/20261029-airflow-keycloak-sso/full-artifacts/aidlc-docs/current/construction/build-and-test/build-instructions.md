# Build Instructions — Airflow Keycloak SSO

## Prerequisites

- Python 3.11 or newer, matching the repository Jenkins pipeline.
- Docker Engine and Docker Compose V2 for the Airflow image build and merged Compose validation.
- `pytest` and `hypothesis` from `tests/requirements-pbt.txt`.
- JupyterHub's pinned runtime packages from `infra/jupyter/hub/requirements.txt` for the existing Hub token-broker test.
- No live Keycloak credentials are needed for these steps.

## Build Steps

### 1. Prepare test dependencies if missing

```bash
python3 -m venv .venv-ci
.venv-ci/bin/python -m pip install -r tests/requirements-pbt.txt
.venv-ci/bin/python -m pip install -r infra/jupyter/hub/requirements.txt
```

The repository Jenkins pipeline runs pytest. This workspace has no configured `code_quality.sh`, `requirements-dev.txt`, or `pyproject.toml`, so do not install additional analysis tools for this change. The Hub test also needs its runtime package manifest and module path when run outside the Hub container.

### 2. Validate source and configuration syntax

```bash
python3 -c 'import ast, json; from pathlib import Path; files = [Path("infra/keycloak/bootstrap-realm.py"), Path("infra/airflow/airflow_sso_roles.py"), Path("infra/airflow/airflow_oauth_security_manager.py"), Path("infra/airflow/airflow_auth_views.py"), Path("infra/airflow/webserver_config.py"), Path("tests/airflow/test_keycloak_sso_contract.py"), Path("tests/keycloak/test_airflow_client_contract.py")]; [ast.parse(path.read_text(encoding="utf-8"), filename=str(path)) for path in files]; json.loads(Path("infra/keycloak/realm-contract.json").read_text(encoding="utf-8"))'
bash -n scripts/lakehouse.sh
```

### 3. Validate merged Compose configuration

Use non-secret placeholder values so Compose can resolve required runtime paths without reading credential files:

```bash
AIRFLOW_UID="$(id -u)" \
LAKEHOUSE_BUNDLE_CONFIG_LIST='[]' \
LAKEHOUSE_PROJECT_ROOT=/tmp/lakehouse-project \
LAKEHOUSE_BUNDLE_HOST_ROOT=/tmp/lakehouse-bundles \
LAKEHOUSE_BROKER_CA_HOST_PATH=/tmp/airflow-token-broker-ca.crt \
docker compose -f docker-compose.yml -f docker-compose.airflow.yml --profile airflow config --quiet
```

### 4. Build the Airflow API-server image without starting services

```bash
AIRFLOW_UID="$(id -u)" \
LAKEHOUSE_BUNDLE_CONFIG_LIST='[]' \
LAKEHOUSE_PROJECT_ROOT=/tmp/lakehouse-project \
LAKEHOUSE_BUNDLE_HOST_ROOT=/tmp/lakehouse-bundles \
LAKEHOUSE_BROKER_CA_HOST_PATH=/tmp/airflow-token-broker-ca.crt \
docker compose -f docker-compose.yml -f docker-compose.airflow.yml --profile airflow build airflow-api-server
```

The API server and other Airflow processes share the same image. This build validates that the pinned Airflow image can package the generated FAB modules. It does not start Airflow or Keycloak, provision the client, or apply realm changes.

### 5. Verify the custom modules against the pinned Airflow/FAB runtime

```bash
docker run --rm --network none --workdir /opt/airflow \
  --entrypoint python local/lakehouse-airflow:3.3.2 \
  -c 'from airflow.providers.fab.auth_manager.security_manager.override import FabAirflowSecurityManagerOverride; from airflow_oauth_security_manager import LakehouseSecurityManager; from airflow_auth_views import LakehouseAuthOAuthView; assert issubclass(LakehouseSecurityManager, FabAirflowSecurityManagerOverride); assert LakehouseSecurityManager.authoauthview is LakehouseAuthOAuthView'
```

This isolated import check does not start the API server or require the client secret.

## Verify Build Success

- Source syntax, JSON, shell syntax, and Compose rendering complete successfully.
- The Airflow API-server image builds successfully.
- Build output contains no client-secret value.

## Troubleshooting

- If Compose reports a missing required interpolation variable, supply only the placeholder values above; do not read secrets into shell variables.
- If Docker cannot reach the pinned base image or Python package index, record the build as blocked by the environment and do not substitute a different image or provider version.
