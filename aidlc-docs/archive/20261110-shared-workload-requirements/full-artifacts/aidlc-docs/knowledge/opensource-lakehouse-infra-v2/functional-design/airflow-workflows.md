# Functional Design — Airflow Workflows (Platform DAG Factory)

Current functional design of the platform component that turns data product repositories into Airflow DAGs. For architecture, see [`../application-design.md`](../application-design.md). History is in the [Platform DAG Factory intent archive](../../../archive/20261110-platform-dag-factory/intent-summary.md).

## Responsibility
`infra/airflow/lakehouse_dags` builds every data product's DAGs from the product repository's `workflows/*.json`, and supplies all the task code those DAGs run.

| A product repository holds | The platform holds |
|---|---|
| `workflows/<name>.json`, one DAG each | DAG construction, the task callables, and the JSON rules |
| `notebooks/` (workload entry points and the `common/` helpers, also used by Jupyter) | The Spark container lifecycle, the broker registration, renewal and revocation, and redaction |
| `configs/<env>.yml`, optional `configs/<product>/<env>.yml` | The CI validator |
| `dags/lakehouse.py`, the fixed stub (`spec.STUB_TEXT`) | |

**Deployment**:
- `airflow-dag-processor` and `airflow-scheduler` mount `./infra/airflow/lakehouse_dags` read-only at `/opt/lakehouse/python/lakehouse_dags`, with `PYTHONPATH=/opt/lakehouse/python`.
- Jenkins mounts the same package plus `infra/jenkins/bin/lakehouse-validate-workflows`.
- Changes are visible through the mount at once. Apply them with `start-airflow`, after `scripts/verify/dag-factory-tests.sh`.

## Modules
| Module | Dependencies | Role |
|---|---|---|
| `__init__` | lazy | `load_workflows(namespace, stub_file)` |
| `spec` | standard library | Workflow JSON v1: `parse_workflow`, `to_document`, `load_repository`, `check_repository`, `STUB_TEXT` |
| `identity` | standard library | bundle name from the checkout path, then `(bundle, product, environment)` |
| `factory` | Airflow, Docker SDK | `build_dag`, `LakehouseOperator`, and the task callables |
| `redact` | standard library | `redact_spark_output` |
| `validate` | standard library | `python3 -m lakehouse_dags.validate [ROOT]` |

## Rules
- **Workflow file**: `workflows/<name>.json`, a JSON object, in UTF-8. Only `*.json` files belong in `workflows/` (hidden files are ignored).
  - `apiVersion`: exactly `lakehouse.local/workflow/v1`.
  - `name`: `[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,99}`, equal to the file stem.
  - `schedule`: required; `null`, or a string of 1 to 100 printable characters.
  - `description`: optional, 1 to 500 printable characters.
  - `tags`: optional, at most 10 distinct tags matching `[a-zA-Z0-9_.:-]{1,50}`; `spark` is reserved.
  - `tasks`: 1 to 50 tasks.
  - Unknown keys are refused, and booleans are never integers.
- **Task**:
  - `name`: same pattern as the workflow name, unique.
  - `entrypoint`: `[A-Za-z0-9_][A-Za-z0-9_.-]*\.py`, existing in `notebooks/workload/`.
  - `runs_after`: distinct names of existing tasks, no self-reference, no cycle.
  - `args`: at most 50 strings, each 1 to 500 printable characters.
  - `retries` 0 to 10; `retry_delay_seconds` 0 to 3600, only with `retries` ≥ 1; `execution_timeout_seconds` 1 to 86400.
  - Unknown keys are refused.
- **Identity**:
  - **Bundle name**: the parent of the nearest `tracking_repo` or `versions` directory above the stub.
  - **Accepted**: only `<product>-main` (environment `prod`) and `<product>-uat` (`uat`), with the product matching `[a-z][a-z0-9]{1,19}`. Anything else is an import error; legacy `lakehouse-*` and `dev` are not accepted.
- **DAG**:
  - **Settings**: `dag_id` is `<bundle>-<name>`; tags are `{<bundle>, spark, *tags}`; `start_date` 2024-01-01 UTC; `catchup` false; `rerun_with_latest_version` false. The description defaults to the task list.
  - **Tasks**: `create_cluster`, then `validate_environment`, then `submit_<task>` (after its `runs_after` predecessors, or after `validate_environment`), then `stop_cluster` (`ALL_DONE`), then `verify_workloads_succeeded`.
  - **Task options**: `retries`, `retry_delay` and `execution_timeout` are set on that task's `submit_` only.
- **Task code**:
  - **Templates**: every task is a `LakehouseOperator` (`template_fields = ()`), so `{{ conn.* }}` and `{{ var.* }}` in `args` are never rendered.
  - **`create_cluster`**: registers `{dag_id, run_id}` with the broker over the pinned endpoint and CA. It starts `lakehouse-<dag_id[:40]>-<sha256(run_id)[:12]>` with the run's bundle checkout at `/opt/lakehouse-bundle` (read-only) and the broker CA. The environment holds the token, run handle and capability, `LAKEHOUSE_ENVIRONMENT`, `LAKEHOUSE_PRODUCT`, and `PYTHONPATH=/opt/lakehouse-bundle`. If startup fails, it removes the container and revokes the run.
  - **`validate_environment`**: an `exec_run` in that container of `python3 -c` with the repository's `notebooks/common/config_loader.load_environment_config(env, /opt/lakehouse-bundle/configs, product)`.
  - **`submit_<task>`**: `spark-submit --master <LAKEHOUSE_SPARK_MASTER> /opt/lakehouse-bundle/notebooks/workload/<entrypoint> --environment <env> --config-dir /opt/lakehouse-bundle/configs`, then `--` and the `args` when there are any. Arguments are passed as a list, and the output is redacted.
  - **`stop_cluster`**: removes the container and revokes the broker run.
- **Repository code never runs in the scheduler**: it runs only inside the run's Spark container. At parse time, the dag-processor imports the stub, and any other `.py` file a repository might add under `dags/`; CI refuses those.
- **Loading**: `load_workflows` validates every file first.
  - **Problems**: any problem raises one `WorkflowError` listing `<path>: <field>: <message>` for all of them, so no DAG of that bundle loads.
  - **No workflows**: without `workflows/`, or with no workflow files, nothing is built and nothing fails.
- **Validator** (`check_repository`): the workflow rules, plus `dags/lakehouse.py` must equal `STUB_TEXT` (line endings normalized) and `dags/` may hold nothing else (`__pycache__` excepted). Exit 0 prints `OK: <n> workflow(s)`; exit 1 prints the problems and `N problem(s)`; exit 2 means a usage error.
- **Bundle checkouts**: `sparse_dirs` is `dags`, `workflows`, `notebooks`, `configs`. Airflow applies it only at the first clone, so `scripts/setup/sync-bundle-checkouts.py`, run by `start-airflow` before Airflow starts, updates each configured bundle's `tracking_repo` when its sparse list differs.
- **Repository-side contract**:
  - `notebooks/common/config_loader.py` provides `load_environment_config(environment, config_dir, product)`.
  - Entry points accept `--environment` and `--config-dir`; `notebooks.common.cli.task_args()` returns the arguments after `--` (an empty list in Jupyter).

## Failure behavior
- **Invalid workflow**: an import error naming every problem; the bundle has no DAGs until it's fixed.
- **Non-product bundle**: an import error.
- **Config check fails**: `validate_environment` fails with redacted output, then `stop_cluster` cleans up.
- **Broker refusal**: `create_cluster` fails (`unknown_product`, `unknown_dag`, `bundle_mismatch`), with no fallback identity.
- **Observed once (2026-11-10)**: Airflow's per-task bundle refresh hit "detected dubious ownership" on `tracking_repo` when two tasks started together. It did not repeat, and the cause is not established.

## Verification and limits
- **Verified 2026-11-10**:
  - host suite 458 passed (P1, P3, P4; spec, validator, wiring, checkout sync);
  - 49 passed in the Airflow image (golden DAG, platform-only callables, no templating, ported container, broker and cleanup tests, P2);
  - workload repository 36 passed (P5);
  - live: both `default` DAGs built from the stub with unchanged IDs, a UAT run 7 of 7 (after one transient failure), and Jenkins `default_ci` with the validation stage.
- **Not run**: a production run; a CI refusal on a pushed invalid branch; interactive `task_args()` in Jupyter.
- **Limits**:
  - parse-time execution of extra repository `.py` files until an enforcing bundle class exists (later phase);
  - single-container `local[*]` Spark;
  - no templating in `args`;
  - only the Spark image's packages; shared Airflow and Jupyter requirements are the next intent.
