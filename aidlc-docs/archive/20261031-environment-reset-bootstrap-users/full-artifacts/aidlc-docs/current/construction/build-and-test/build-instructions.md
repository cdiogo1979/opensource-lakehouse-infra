# Build Instructions — Environment Reset and Bootstrap Users

## Prerequisites
- Docker with Compose V2 (tested on Rancher Desktop, Docker 29.5.3) and Python 3.
- No new dependencies. The images are rebuilt by the operator script: Airflow 3.3.2, token broker, JupyterHub, Jenkins, and Polaris group reconciler.

## Code analysis
No linter or formatter is configured in this repository, and no CI quality script exists. The static checks run were:
- `bash -n` on the changed shell scripts
- `python3 -m py_compile` on the changed Python files
- `docker compose -f docker-compose.yml -f docker-compose.airflow.yml config -q`

## Build and run from nothing
```sh
./scripts/lakehouse.sh reset --yes      # destroys all local platform state
./scripts/bootstrap-default-product.sh  # runs start, then realm, users, storage, catalogs, grants, smoke checks
./scripts/lakehouse.sh start-airflow    # optional
```

## Expected output
- `Keycloak realm bootstrap verified (... writer-client=lakehouse-writer; ... groups=5; bootstrap-users-created=5)` on the first run.
- `Bootstrap users match their defaults (...; users=5)`.
- `Default product bootstrap and smoke verification completed.`
- `Airflow is ready at http://127.0.0.1:8085; production and UAT Bundles are registered`.
- Expected notice after a reset: `no legacy Jenkins home found; started lakehouse-local_jenkins-home empty`.
