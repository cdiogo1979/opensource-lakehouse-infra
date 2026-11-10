# Code Summary — dag-factory

## Platform (this workspace)
| File | Change | Rules |
|---|---|---|
| `infra/airflow/lakehouse_dags/__init__.py` | New: `load_workflows(namespace, stub_file)`. Validates everything first, then builds one DAG per workflow; Airflow is imported lazily. | FR-1, BR-9 |
| `infra/airflow/lakehouse_dags/spec.py` | New (standard library only): `Task`, `Workflow`, `Problem`, `WorkflowError`, `parse_workflow`, `to_document`, `load_repository`, `check_repository`, `STUB_TEXT` | FR-3, FR-7, BR-1 to BR-3, BR-10 |
| `infra/airflow/lakehouse_dags/identity.py` | New (standard library only): bundle name from the checkout path; product bundles only | FR-4, BR-4 |
| `infra/airflow/lakehouse_dags/factory.py` | New, ported from the workload `dag_factory.py`: `LakehouseOperator` (no templating), `build_dag`, `dag_kwargs`, the callables (container, in-container config check, submit with `args`, cleanup), and the broker client | FR-4, BR-5 to BR-8 |
| `infra/airflow/lakehouse_dags/redact.py` | Ported `spark_output.py` | BR-7 |
| `infra/airflow/lakehouse_dags/validate.py` | New CLI: `python3 -m lakehouse_dags.validate [ROOT]` | FR-7, BR-10 |
| `infra/jenkins/bin/lakehouse-validate-workflows` | New wrapper | FR-7 |
| `compose.airflow.yml` | `airflow-scheduler` and `airflow-dag-processor`: the package mounted read-only, and `PYTHONPATH=/opt/lakehouse/python` | FR-1, NFR-5 |
| `compose.jenkins.yml` | The package and the wrapper, mounted read-only | FR-7 |
| `infra/products/data_products.py`, `infra/airflow/validate-bundle-config.py` | `sparse_dirs: [dags, workflows, notebooks, configs]` | FR-5 |
| `README.md` | Airflow section: the JSON contract, stub, fields, errors, bundles, factory changes, and the test runner | FR-9 |
| `scripts/verify/dag-factory-tests.sh` | New: runs the factory and spec tests inside the Airflow image | FR-9 |
| `scripts/setup/sync-bundle-checkouts.py`, `scripts/lakehouse.sh` | New in Build and Test: before Airflow starts, `start-airflow` updates existing `tracking_repo` sparse checkouts to the configured `sparse_dirs`; `tests/airflow/test_bundle_checkout_sync.py` | FR-5 |
| `tests/airflow/workflow_strategies.py` | New generators (PBT-07) | PBT |
| `tests/airflow/test_workflow_spec.py` | New: examples, 21 refusal cases, validator, wiring, and package-without-Airflow tests, plus P1, P3 and P4 (host) | FR-3, FR-5, FR-7 |
| `tests/airflow/test_dag_factory.py` | New (Airflow image): golden DAG, platform-only callables, task options, no templating, commands, `load_workflows` errors, the ported container, broker and cleanup tests, plus P2 | FR-4, BR-5 to BR-9 |

## Workload repository (`cdiogo1979/opensource-lakehouse`)
- **Where it is**: local commit `9cbd6f8` on branch `platform-dag-factory` (from `515e403`) in the session's scratchpad clone. **Not pushed.**
- **Patch**: `aidlc-docs/current/deploy/opensource-lakehouse.patch`.

| Change | Files |
|---|---|
| Added | `workflows/test_environment.json`, `dags/lakehouse.py` (stub), `tests/workload_foundation/test_cli.py` (including P5) |
| Removed | `dags/dag_factory.py`, `dags/dag_defaults.py`, `dags/spark_output.py`, `dags/.airflowignore`, `dags/test_environment.py`, `airflow_bundle_client.py`, `airflow_bundle_client.example.yml`, `airflow_bundle_config.example.json`, `AIRFLOW_BUNDLES.md`, `tests/jenkins_deployment/test_airflow_bundle_client.py`, `tests/jenkins_deployment/test_airflow_writer_token_contract.py` |
| Changed | `notebooks/common/cli.py` (`task_args`), `Jenkinsfile` ("Validate workflows" stage; `compileall dags notebooks`), `scripts/code_quality.sh` (targets), `tests/workload_foundation/{conftest,test_init_environment,test_product_bundles}.py` (no `dag_defaults`), `README.md` (complete guide, CR-1), `AGENTS.md` |

## Results
- **Platform, host**: `python3 -m pytest -q tests` gives 456 passed, 3 skipped.
- **Platform, Airflow image**: `scripts/verify/dag-factory-tests.sh` gives 49 passed.
- **Workload**: 36 passed; Ruff, Black, Flake8 and Bandit all PASS; `lakehouse-validate-workflows .` gives `OK: 1 workflow(s)`.

## Found and fixed during Code Generation
- **Templating** (security): `PythonOperator` renders Jinja in `op_kwargs`, so `{{ conn.* }}` or `{{ var.* }}` in workflow `args` would have reached product code. Every platform task is now a `LakehouseOperator` with no template fields. Tested.
- **Names**: workflow names starting with `.` are refused, because they would be hidden files.
- **Imports**: the deprecated Airflow import paths (`airflow.operators.python`, `airflow.utils.trigger_rule`) were replaced.
- **Host test guard**: it now checks `airflow.exceptions`, because `tests/airflow` is a namespace package named `airflow` on the host.

## PBT compliance (partial)
| Rule | Status |
|---|---|
| PBT-02 | P1 (workflow JSON round trip), P5 (`--` split) |
| PBT-03 | P2 (task graph and cleanup order), P3 (single-field mutations are reported and never raise), P4 (bundle identity) |
| PBT-07 | `tests/airflow/workflow_strategies.py`: acyclic graphs, names, entry points, tags, arguments |
| PBT-08 | default shrinking, `print_blob=True`; the workload repository keeps its fixed seed fixture |
| PBT-09 | Hypothesis in both repositories |
