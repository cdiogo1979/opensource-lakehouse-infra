# Scripts

Reference: where the commands live. Back to the [README](../../README.md).

| Path | Purpose |
|---|---|
| `scripts/lakehouse.sh` | `start`, `status`, `stop`, `reset`, `reconcile-starrocks`, `rotate-checkpoint-keys`, and the Airflow commands |
| `scripts/bootstrap-default-product.sh` | the product bootstrap (Quick start step 2) |
| `scripts/setup/` | credentials, certificates, and preflight checks used by `start`; `lock-workload-python.sh` regenerates the workload lock |
| `infra/workload-python/` | the shared workload Python packages (`requirements.in`, `requirements.lock`) and `workload_python.py`, their checks and installer |
| `scripts/bootstrap/` | realm users and Spark smoke steps used by the product bootstrap |
| `scripts/operations/` | `create-data-product.sh`, `remove-data-product.sh`, `create-user.sh`, `migrate-users-to-ldap.py` (once, for older stacks), and the full reset |
| `data-products/` | one configuration file per data product |
| `infra/products/` | the product model, template, Jenkins renderer, and `product-cli.py` |
| `scripts/clients/` | `starrocks-login.sh` (username and password over TLS) |
| `scripts/verify/` | verifiers. Most are read-only. `role-matrix.py` creates temporary users and data, and `keycloak-outage.py` stops Keycloak briefly |
| `scripts/aidlc_intent.py` | the AI-DLC closing tool (see [AI-DLC](aidlc.md)) |

Documentation: `python3 scripts/verify/docs-links.py` checks every relative link and anchor in `README.md` and `docs/`.

Tests: `python3 -m pytest -q tests` (`pytest.ini` adds the Hub modules' folder to the import path). The token broker's behavioral tests run inside its image (`scripts/verify/broker-unit-tests.sh`), and the DAG factory's Airflow-side tests inside the Airflow image (`scripts/verify/dag-factory-tests.sh`).
