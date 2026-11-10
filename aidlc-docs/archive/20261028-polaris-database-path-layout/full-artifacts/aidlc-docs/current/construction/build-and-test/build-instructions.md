# Build Instructions — Polaris Database Path Layout

## Prerequisites

- Docker Desktop / Docker Engine with Compose V2; the local `lakehouse-local` provider containers.
- Python 3 and the local Spark image `local/spark-iceberg:3.5.5_1.8.1-krb5`.
- Protected runtime credentials under `.runtime/credentials/`.
- The pinned boto3 dependency in `infra/bucket-init/requirements.txt` for the guarded reset and RustFS preservation probe.

## Build and Static Validation

From the project root:

```sh
python3 -m py_compile infra/polaris/bootstrap-default-catalogs.py infra/polaris/bootstrap-product-authorization.py infra/polaris/reset-default-product-once.py infra/spark-bootstrap/create_smoke_tables.py infra/spark-bootstrap/verify_role_matrix.py
bash -n scripts/bootstrap-default-product.sh scripts/run-bootstrap-smoke-spark.sh
docker compose config --quiet
```

For the local test environment, use an isolated ignored venv:

```sh
python3 -m venv .runtime/aidlc-test-venv
.runtime/aidlc-test-venv/bin/python -m pip install -r infra/bucket-init/requirements.txt
```

## Runtime Build

The runtime consists of Keycloak, Polaris, RustFS, and their PostgreSQL databases. Start and check them with:

```sh
./scripts/lakehouse.sh start
./scripts/lakehouse.sh status
```

The one-time bucket/catalog reset is deliberately separate from this build and the normal bootstrap. See the approved operator sequence in `README.md`.
