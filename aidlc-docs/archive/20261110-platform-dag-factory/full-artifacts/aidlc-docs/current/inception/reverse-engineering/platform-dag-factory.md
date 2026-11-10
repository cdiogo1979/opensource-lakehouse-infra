# Focused Reverse Engineering — Platform DAG Factory

Intent `20261110-platform-dag-factory`. Scope: where DAG-building logic lives today, which Airflow process runs which code, what the workload repository's notebooks and configs need, and what has to move so a product repository holds only workflow JSON, code (`notebooks/`) and configs. Captured on 2026-11-10 against `cdiogo1979/opensource-lakehouse` `515e403` (`main` = `uat`) and the running platform.

## Where the code runs (Airflow 3.3.2, LocalExecutor)
| Process | Image | Runs | Has |
|---|---|---|---|
| `airflow-dag-processor` | `local/lakehouse-airflow:3.3.2` | **parses** bundle `dags/*.py` (top-level code) | bundle checkouts (rw); `airflow-internal` network only; **no Docker socket** |
| `airflow-scheduler` | same | **executes tasks**: the `PythonOperator` callables | `/var/run/docker.sock`, the broker control token, the broker CA, bundle checkouts |
| `airflow-api-server` | same | UI and API; sign-in mapping | `data_products.py` and `data-products/` (read-only mounts) |

- **Callable source**: the callables come from the bundle's own `dags/dag_factory.py`, so **repository code runs in the scheduler, which holds the Docker socket and the broker token**.
- **`validate_environment`** imports the repository's `notebooks/common/config_loader.py` inside the scheduler.
- **The Airflow image** is `apache/airflow:3.3.2-python3.10` plus four providers (`git`, `docker`, `fab`, `postgres`) and the platform's auth and bootstrap scripts. It has no platform DAG code today.
- **Bundles**: `<product>-main` and `<product>-uat`, a `GitDagBundle` each, with `sparse_dirs: [dags, configs, notebooks]` (in both `data_products.BUNDLE_KWARGS` and `infra/airflow/validate-bundle-config.py`). Checkouts go to `/opt/airflow/dag_bundles/<bundle>/...`, a host path that `create_cluster` mounts into the Spark container.

## Workload repository (`515e403`)
| Path | Lines | Role | After this intent |
|---|---|---|---|
| `dags/dag_factory.py` | 542 | validation of workload declarations, Spark container lifecycle (Docker SDK), broker registration, renewal and revocation, `spark-submit` via `exec_run`, cleanup, task graph | **platform** |
| `dags/dag_defaults.py` | 79 | bundle path to name, DAG ID prefix and environment (`<product>-main` → `prod`, `-uat` → `uat`; legacy `lakehouse-*`; else `dev`); standard DAG kwargs | **platform** |
| `dags/spark_output.py` | 16 | redaction of Spark output in task logs | **platform** |
| `dags/.airflowignore` | 2 | hides the factory modules from DAG parsing | replaced |
| `dags/test_environment.py` | 28 | the only DAG declaration: `create_spark_dag(dag_name, workloads[{task_name, entrypoint_file, runs_after}], schedule)` | **`workflows/test_environment.json`** |
| `notebooks/common/` (`config_loader`, `cli`, `job_runtime`) | | configuration loading (`configs/<product>/<env>.yml` with fallback to `configs/<env>.yml`), `--environment`/`--config-dir` arguments, Spark session runtime | **stays** (Jupyter uses it) |
| `notebooks/workload/` (`test_environment.py`, `count_sample_rows.py`, `jupyter_helper.py`) | | the Spark jobs | **stays** |
| `configs/{dev,uat,prod}.yml` | | storage path, catalog, database per environment | **stays** (Jupyter uses it) |

- **The DAG contract today**:
  - **Entry points**: an entrypoint is a bare `*.py` file name in `notebooks/workload/`. Task names match `[a-zA-Z0-9_.-]+` and are unique.
  - **Dependencies**: `runs_after` names existing tasks, with no self-reference and no cycle. Tasks without predecessors start after `create_cluster`.
  - **DAG ID**: `<bundle>-<dag_name>`, with tags `[<prefix>, "spark"]`, `start_date` 2024-01-01, `catchup` false, `rerun_with_latest_version` false.
  - **Task chain**: `validate_environment`, then `create_cluster`, then `submit_<task>`, with `stop_cluster` (`ALL_DONE`) and `verify_workloads_succeeded` at the end.
  - **Spark invocation**: `spark-submit --master local[*] /opt/lakehouse-bundle/notebooks/workload/<file> --environment <env> --config-dir /opt/lakehouse-bundle/configs`, with `PYTHONPATH=/opt/lakehouse-bundle` and `LAKEHOUSE_ENVIRONMENT` and `LAKEHOUSE_PRODUCT` set.
- **Tests that depend on the factory**:
  - `tests/workload_foundation/test_product_bundles.py` and `test_init_environment.py` (`dag_defaults`);
  - `tests/jenkins_deployment/test_airflow_writer_token_contract.py` and `test_airflow_bundle_client.py` (factory source checks).

  `test_config_loader.py` and `test_properties.py` test `notebooks/common` and stay.
- **Docs that describe the factory**: `AGENTS.md`, `AIRFLOW_BUNDLES.md`.
- **CI**: the `Jenkinsfile` compiles `airflow_bundle_client.py dags notebooks`, then runs lint, flake8, bandit and pytest.
- **Jupyter**: the platform doesn't mount the workload repository. Users clone it and run the notebooks with `configs/` (typically `dev`). Nothing in Jupyter depends on `dags/`.

## Gaps and constraints
1. **A Python file is needed in the bundle**: Airflow 3 discovers DAGs only in Python files inside a bundle, so each repository keeps a minimal stub, for example `dags/lakehouse.py`. A custom bundle class could supply it, but that depends on Airflow internals.
2. **Package placement**: the platform package must be importable in both the dag-processor (parsing) and the scheduler (task execution), so it goes in the Airflow image or a read-only mount used by both.
3. **Keeping the DAG in its product bundle**: the DAG must still be parsed from the product bundle, so the broker check (`bundle_name`), DAG ID prefixes and Git versioning keep working. `bundle_name_for` reads the checkout path, so the stub must pass its own location to the platform (for example `globals()` or `__file__`).
4. **Config check**: to keep repository code out of the scheduler, `validate_environment` should run the repository's `config_loader` inside the Spark container, as the first `exec_run`.
5. **Bundle directories**: add `workflows`, in two places (`BUNDLE_KWARGS` and the validator's `FIXED_KWARGS`). Changing the bundle kwargs changes the fingerprint, so `start-airflow` recreates Airflow.
6. **Cut-over order**: the platform package can ship first. The old repository DAG still imports its local `dag_factory` and keeps working (no name clash, given a distinct package name such as `lakehouse_dags`). Then the repository change goes to `main` and `uat`.
7. **No enforcement**: the stub isn't enforcement. A repository can still add other `.py` files under `dags/` that execute in the scheduler. Full enforcement, a bundle that exposes only `workflows/`, `notebooks/` and `configs/` plus a platform stub, is a possible later phase.
8. **Validation in CI**: the product's `_ci` job should be able to validate `workflows/*.json` against the platform schema. The validator must be available to the repository's CI (for example a published schema file, or the validator in the Jenkins image).
