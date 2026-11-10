# Unit Test Instructions

| Suite | Command | Expected |
|---|---|---|
| Contracts and properties (host) | `PYTHONPATH=infra/jupyter/hub python3 -m pytest -q tests` | 393 passed, 2 skipped, 1 known failure (`test_approved_groups_map_to_exact_airflow_roles`, Airflow role drift, predates this intent) |
| Broker behaviour (broker image) | `scripts/verify/broker-unit-tests.sh` | 11 passed (P4, refusals, renewals, Viewer token cache) |
| Workload repository | in a checkout of `opensource-lakehouse`: `pytest tests && ruff check . && black --check dags notebooks tests` | 61 passed, 1 upstream failure (`test_dag_factory_reuses_spark_container_for_bundle_workloads`, stale since "rename dag"); lint clean |

Properties (Hypothesis, `print_blob=True`): P1, P2, P3, P5 in `tests/products/test_repo_and_bundles.py`; P4 in `tests/airflow/test_token_broker_writers.py`; the bundle prefix property in the workload `tests/workload_foundation/test_product_bundles.py`.
