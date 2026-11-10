# Build Instructions — rustfs-keycloak-oidc

## Prerequisites
- **Runtime**: Docker with Compose V2 and Python 3 (host). The core stack uses pinned images: RustFS 1.0.4, Keycloak 26.8.1.
- **Test dependencies**: `tests/requirements-pbt.txt` (pytest 9.2.0, Hypothesis 6.170.12). The JupyterHub suite also needs `jupyterhub` importable and `PYTHONPATH=infra/jupyter/hub`; that is pre-existing and not part of this intent.
- **Environment variables**: optional `RUSTFS_CONSOLE_HOST_PORT` (default 9001) and `KEYCLOAK_HOST_PORT` (default 8080).

## Build Steps

### 1. Install test dependencies
```bash
python3 -m venv .venv-ci
.venv-ci/bin/python -m pip install -r tests/requirements-pbt.txt
```

### 2. Code analysis
No formatter, linter, or code-quality script is configured in this repository (no `pyproject.toml`, lint config, or quality script; the Jenkinsfile runs pytest only). The applicable checks are:
```bash
python3 -m py_compile infra/rustfs/bootstrap-policies.py infra/rustfs/bootstrap-buckets.py \
  infra/keycloak/bootstrap-realm.py scripts/prepare-lakehouse-runtime.py scripts/verify-rustfs-oidc.py
sh -n infra/rustfs/rustfs-entrypoint.sh
bash -n scripts/bootstrap-default-product.sh
python3 -m json.tool infra/keycloak/realm-contract.json >/dev/null
```

### 3. Validate Compose configuration
```bash
docker compose -f docker-compose.yml config -q
# Airflow overlay (variables normally exported by scripts/lakehouse.sh)
AIRFLOW_UID=$(id -u) DOCKER_GID=102 LAKEHOUSE_PROJECT_ROOT=/tmp LAKEHOUSE_BUNDLE_HOST_ROOT=/tmp \
  LAKEHOUSE_BUNDLE_CONTAINER_ROOT=/opt LAKEHOUSE_BROKER_CA_HOST_PATH=/tmp/x LAKEHOUSE_BUNDLE_CONFIG_LIST='[]' \
  docker compose -f docker-compose.yml -f docker-compose.airflow.yml --profile airflow config -q
```

### 4. Apply to the local stack
```bash
python3 scripts/prepare-lakehouse-runtime.py           # creates rustfs-oidc-client-secret once
docker compose -f docker-compose.yml up -d keycloak rustfs   # recreates both with new config; volumes preserved
python3 infra/keycloak/bootstrap-realm.py              # rustfs client + groups mapper
python3 infra/rustfs/bootstrap-policies.py             # four group-named policies
```
A full fresh start uses `scripts/lakehouse.sh start` followed by `scripts/bootstrap-default-product.sh`, which include these steps.

### 5. Verify build success
- `docker inspect` health shows `keycloak` and `rustfs` as healthy.
- `rustfs` is attached to `lakehouse-local_rustfs-identity`; `docker exec lakehouse-local-rustfs-1 getent hosts keycloak.localhost` returns a private Keycloak address, not `127.0.0.1`.

## Troubleshooting
- **RustFS exits at start with "client secret file is unavailable/empty"**: run `scripts/prepare-lakehouse-runtime.py`, then restart RustFS.
- **Provider not listed**: check `RUSTFS_OUTBOUND_ALLOW_ORIGINS` and the network alias. RustFS retries discovery in the background, so if the realm did not exist yet, retry after `bootstrap-realm.py`.
