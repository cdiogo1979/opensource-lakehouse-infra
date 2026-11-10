# Build Instructions

No separate build. `./scripts/lakehouse.sh start-airflow` builds the Airflow images and the token broker image (`infra/airflow-token-broker/Dockerfile`, Python 3.10 with the pinned FastAPI), stages the product writers, generates and validates the bundle list from `data-products/*.yaml`, starts Airflow, waits for DAGs from every product bundle, and records the fingerprint in `.runtime/state/airflow-bundles.json`.

Prerequisites: the core stack running (`./scripts/lakehouse.sh start`); each product with a `repo` applied (its writer password file exists); the bundle repositories public and containing the workload patch (`aidlc-docs/current/deploy/opensource-lakehouse.patch`, upstream `fedf0bc`).
