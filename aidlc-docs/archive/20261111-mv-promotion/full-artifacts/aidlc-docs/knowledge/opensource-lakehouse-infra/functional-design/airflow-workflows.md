# Functional Design — Airflow Workflows (Platform DAG Factory)

Current functional design of the platform component that turns data product repositories into Airflow DAGs. For architecture, see [`../application-design.md`](../application-design.md). History is in the [Platform DAG Factory intent archive](../../../archive/20261110-platform-dag-factory/intent-summary.md); the checkpoint key mount is from the [Spark S3 Checkpoints intent archive](../../../archive/20261111-spark-s3-checkpoints/intent-summary.md).

## Responsibility
`infra/airflow/lakehouse_dags` builds every data product's DAGs from the product repository's `workflows/*.json`, and supplies all the task code those DAGs run.

| A product repository holds | The platform holds |
|---|---|
| `workflows/<project>/<name>.json` (or flat `workflows/<name>.json`), one DAG each | DAG construction, the task callables, and the JSON rules |
| `notebooks/` (workload entry points and the `common/` helpers, also used by Jupyter) | The Spark container lifecycle, the broker registration, renewal and revocation, and redaction |
| `configs/<env>.yml`, optional `configs/<product>/<env>.yml` | The CI validator |
| `dags/lakehouse.py`, the fixed stub (`spec.STUB_TEXT`) | |

**Deployment**:
- `airflow-dag-processor` and `airflow-scheduler` mount `./infra/airflow/lakehouse_dags` read-only at `/opt/lakehouse/python/lakehouse_dags`, with `PYTHONPATH=/opt/lakehouse/python`.
- Jenkins mounts the same package plus `infra/jenkins/bin/lakehouse-validate-workflows`.
- Changes are visible through the mount at once. Apply them with `start-airflow`, after `scripts/verify/dag-factory-tests.sh`.
- `airflow-scheduler` (which runs the tasks, LocalExecutor) also mounts the staged checkpoint keys `.runtime/container-mounts/checkpoint-keys` read-only at `/run/secrets/checkpoint-keys`; every Airflow service gets `LAKEHOUSE_CHECKPOINT_KEYS_HOST_DIR`, the same folder's host path, exported by `scripts/lakehouse.sh`.

## Modules
| Module | Dependencies | Role |
|---|---|---|
| `__init__` | lazy | `load_workflows(namespace, stub_file)` |
| `spec` | standard library | Workflow JSON v1: `parse_workflow`, `to_document`, `load_repository`, `check_repository`, `STUB_TEXT` |
| `identity` | standard library | bundle name from the checkout path, then `(bundle, product, environment)` |
| `factory` | Airflow, Docker SDK | `build_dag`, `LakehouseOperator`, and the task callables |
| `redact` | standard library | `redact_spark_output` |
| `task_args` | standard library | trigger-time task arguments: `check_task_args`, `task_values`, `effective_args`, `option_name` |
| `validate` | standard library | `python3 -m lakehouse_dags.validate [ROOT]` |

## Rules
- **Workflow file**: `workflows/<name>.json` or, per subproject, `workflows/<project>/<name>.json` (`<project>` matching `[A-Za-z0-9][A-Za-z0-9_-]{0,49}`, one level), a JSON object, in UTF-8. Only `*.json` files belong in `workflows/` and its subproject folders; invalid folder names, deeper folders and other files are problems; hidden entries are ignored. A workflow name is unique across the repository (DAG IDs don't include the subproject); a repeated name is a problem naming both files.
  - `apiVersion`: exactly `lakehouse.local/workflow/v1`.
  - `name`: `[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,99}`, equal to the file stem.
  - `schedule`: required; `null`, or a string of 1 to 100 printable characters.
  - `description`: optional, 1 to 500 printable characters.
  - `tags`: optional, at most 10 distinct tags matching `[a-zA-Z0-9_.:-]{1,50}`; `spark` is reserved.
  - `tasks`: 1 to 50 tasks.
  - Unknown keys are refused, and booleans are never integers.
- **Task**:
  - `name`: same pattern as the workflow name, unique.
  - `entrypoint`: `[A-Za-z0-9_][A-Za-z0-9_.-]*\.py`, optionally prefixed by a layer folder `bronze/`, `silver/`, `gold/`, `ops/`, `deploy/` or `other/` (one level, no `..`), existing in the workflow's code folder: `notebooks/workload/<project>/` for a subproject workflow, `notebooks/workload/` for a flat one (`Workflow.entrypoint_path`).
  - `runs_after`: distinct names of existing tasks, no self-reference, no cycle.
  - `args`: at most 50 strings, each 1 to 500 printable characters.
  - `retries` 0 to 10; `retry_delay_seconds` 0 to 3600, only with `retries` ≥ 1; `execution_timeout_seconds` 1 to 86400.
  - Unknown keys are refused.
- **Identity**:
  - **Bundle name**: the parent of the nearest `tracking_repo` or `versions` directory above the stub.
  - **Accepted**: only `<product>-main` (environment `prod`) and `<product>-uat` (`uat`), with the product matching `[a-z][a-z0-9]{1,19}`. Anything else is an import error; legacy `lakehouse-*` and `dev` are not accepted.
- **DAG**:
  - **Settings**: `dag_id` is `<bundle>-<name>`; tags are `{<bundle>, spark, *tags}`; `start_date` 2024-01-01 UTC; `catchup` false; `rerun_with_latest_version` false. The description defaults to the task list.
  - **Tasks**: `create_cluster`, then `install_requirements` (2 retries, 30 s apart), then `validate_environment`, then `submit_<task>` (after its `runs_after` predecessors, or after `validate_environment`), then `stop_cluster` (`ALL_DONE`), then `verify_workloads_succeeded`.
  - **Task options**: `retries`, `retry_delay` and `execution_timeout` are set on that task's `submit_` only.
  - **Trigger-time task arguments**: every DAG has one param, `task_args` (`Param({}, type="object")`, description with an example and the task names): `{"<task>": {"<argument>": "<value>"}}`. Task names must be the workflow's; argument names `[a-z][a-z0-9_]{0,49}`; values printable strings of 1 to 500 characters; at most 20 per task. Airflow doesn't check the object's content (probe P1), so the factory does.
- **Task code**:
  - **Templates**: every task is a `LakehouseOperator` (`template_fields = ()`), so `{{ conn.* }}` and `{{ var.* }}` in `args` are never rendered.
  - **Checkpoint key** (`_checkpoint_key_volume`, before the broker registration): the bucket of the run's product and environment comes from `/run/secrets/checkpoint-keys/.buckets.json` (product → environment → bucket, no secrets, written by the RustFS checkpoint key bootstrap, because the scheduler has no product model). The staged file must be a regular file, not a symlink; the host folder must be absolute and named `checkpoint-keys`. It becomes the one read-only mount `/run/secrets/lakehouse-checkpoints/<bucket>`, so a `-main` run holds only the `prod` key and a `-uat` run only the `uat` key. Any problem fails `create_cluster` before a run is registered or a container exists.
  - **`create_cluster`**: first checks the run's `task_args` (all problems in one error, before the checkpoint key, the broker registration or any container); then registers `{dag_id, run_id}` with the broker over the pinned endpoint and CA. It starts `lakehouse-<dag_id[:40]>-<sha256(run_id)[:12]>` with the run's bundle checkout at `/opt/lakehouse-bundle` (read-only), the broker CA and the checkpoint key. The environment holds the token, run handle and capability, `LAKEHOUSE_ENVIRONMENT`, `LAKEHOUSE_PRODUCT`, and `PYTHONPATH=/opt/lakehouse-bundle`. If startup fails, it removes the container and revokes the run.
  - **`install_requirements`**: an `exec_run` in that container of `/opt/lakehouse/venv/bin/python /opt/lakehouse/workload_python.py install-extras /opt/lakehouse-bundle/requirements.txt --lock /opt/lakehouse/requirements.lock`: nothing without the file; otherwise the extras, constrained by the lock, into the container's venv, with the output redacted (rules in `workload-python-environment.md`).
  - **`validate_environment`**: an `exec_run` in that container of `/opt/lakehouse/venv/bin/python -c` with the repository's `notebooks/common/config_loader.load_environment_config(env, /opt/lakehouse-bundle/configs, product)`.
  - **`submit_<task>`**: `spark-submit --master <LAKEHOUSE_SPARK_MASTER> /opt/lakehouse-bundle/notebooks/workload/[<project>/]<entrypoint> --environment <env> --config-dir /opt/lakehouse-bundle/configs`, then `--` and the effective arguments when there are any: the workflow `args` with the run's `task_args` for this task applied (each value one `--<name>=<value>` token appended; the same option, as `--opt value` or `--opt=value`, removed from the workflow `args` first). Both lists are logged (redacted). Arguments are passed as a list, and the output is redacted.
  - **`stop_cluster`**: removes the container and revokes the broker run.
- **Repository code never runs in the scheduler**: it runs only inside the run's Spark container. At parse time, the dag-processor imports only files under `dags/` (the bundles' `subdir`): the stub, and any other `.py` file a repository might add there, which CI refuses.
- **Loading**: `load_workflows` validates every file first.
  - **Problems**: any problem raises one `WorkflowError` listing `<path>: <field>: <message>` for all of them, so no DAG of that bundle loads.
  - **No workflows**: without `workflows/`, or with no workflow files, nothing is built and nothing fails.
- **Validator** (`check_repository`): the workflow rules, plus `dags/lakehouse.py` must equal `STUB_TEXT` (line endings normalized) and `dags/` may hold nothing else (`__pycache__` excepted). Exit 0 prints `OK: <n> workflow(s)`; exit 1 prints the problems and `N problem(s)`; exit 2 means a usage error. The Jenkins wrapper `lakehouse-validate-workflows` then checks a root `requirements.txt`, when present, with `workload_python.py check-extras`; it exits 1 if either check fails.
- **Bundle checkouts**: `sparse_dirs` is `dags`, `workflows`, `notebooks`, `configs`; Git's cone mode also checks out every root file, such as `requirements.txt`. `subdir` is `dags`, so Airflow's DAG folder is `dags/`, while the stub still takes the repository root from its own path. Airflow applies `sparse_dirs` only at the first clone, so `scripts/setup/sync-bundle-checkouts.py`, run by `start-airflow` before Airflow starts, updates each configured bundle's `tracking_repo` when its sparse list differs.
- **Repository-side contract** (`opensource-lakehouse-sample-dp` from `42de0f3`):
  - `notebooks/common/config_loader.py` provides `load_environment_config(environment, config_dir, product)`; configs are repository-owned and free-form, every key reaches the job; `configs/<product>/<env>.yml` is used in Airflow only.
  - Entry points accept `--environment` and `--config-dir`; `notebooks.common.job_runtime.start_spark_job(app_name)` returns `(spark, config)` through the platform's `lakehouse_spark` (see `workload-python-environment.md`).
  - Task arguments: `notebooks.common.cli.parse_task_args(declaration)`; names map to options (`scale_factor` → `--scale-factor`, `--opt value` or `--opt=value`); spec `required` or a string `default`; values are strings, never checked by the parser; structural problems are reported together with the usage and exit 2 (Airflow) or raise `TaskArgumentError` (Jupyter). In Jupyter the values come from the notebook's widgets (`notebooks/common/jupyter_input_widget_helper.py`, from `WIDGET_LIST`), else its `TASK_ARGS`; `task_args()` returns the raw list.
  - `opensource-lakehouse-sample-dp` (from `f8c13e0`) uses subproject `sample`: `workflows/sample/`, notebooks in `notebooks/workload/sample/other/`, entry points `other/<file>.py`; its AGENTS.md describes the subproject and layer layout.
  - Notebooks have the sections Initialization (`# !lakehouse-install-requirements ~/work/opensource-lakehouse-sample-dp`, `# %run ../../../common/jupyter_environment_resolver.py` from a layer folder), Imports, their own sections, and Execution (only the `if __name__ == "__main__":` block, so importing a notebook runs nothing). The resolver uses `dev` unless `LAKEHOUSE_ENVIRONMENT` is `uat` or `prod`, and names the Spark application `<env>-<notebook>`.

## Failure behavior
- **Invalid workflow**: an import error naming every problem; the bundle has no DAGs until it's fixed.
- **Non-product bundle**: an import error.
- **Config check fails**: `validate_environment` fails with redacted output, then `stop_cluster` cleans up.
- **Invalid `task_args`**: `create_cluster` fails naming every problem; nothing is registered or started.
- **Broker refusal**: `create_cluster` fails (`unknown_product`, `unknown_dag`, `bundle_mismatch`), with no fallback identity.
- **Checkpoint key missing or unsafe** (no index entry, missing or symlinked file, bad host folder or bucket name): `create_cluster` fails naming the bucket and the product bootstrap; nothing is registered or started. `start-airflow` refuses to start while any product bucket lacks a staged key.
- **Observed once (2026-11-10)**: Airflow's per-task bundle refresh hit "detected dubious ownership" on `tracking_repo` when two tasks started together. It did not repeat, and the cause is not established.

## Verification and limits
- **Verified 2026-11-11 (task parameters)**: host 608 passed, Airflow image 81 passed (param on every DAG; invalid `task_args` fail before registration or container; values reach only their task; property: render-then-parse gives trigger values once, workflow values otherwise). Live UAT: `{"tpch_region_load": {"silver_lookback_days": "1"}}` gave that task `--silver-lookback-days=1` (`lookback_days` 1), others unchanged; an unknown task and a non-string value failed at `create_cluster` with no container.
- **Verified 2026-11-11 (Spark S3 checkpoints)**: host `tests/airflow` 71 passed (one key per environment; missing, symlinked, unindexed, unknown-product, bad host folder and bad bucket cases fail before registration); `default-uat-test_environment` 8/8 with only `/run/secrets/lakehouse-checkpoints/bucket-default-uat` (ro) mounted.
- **Verified 2026-11-10 (shared workload requirements)**: Airflow image 51 passed (the `install_requirements` task, its command and retries, redaction); `default-uat-test_environment` 8/8 without extras; `default-uat-generate_tpch` 13/13 with extras; with `subdir`, only `dags/lakehouse.py` is parsed per bundle.
- **Verified 2026-11-10 (DAG factory)**:
  - host suite 458 passed (P1, P3, P4; spec, validator, wiring, checkout sync);
  - 49 passed in the Airflow image (golden DAG, platform-only callables, no templating, ported container, broker and cleanup tests, P2);
  - workload repository 36 passed (P5);
  - live: both `default` DAGs built from the stub with unchanged IDs, a UAT run 7 of 7 (after one transient failure), and Jenkins `default_ci` with the validation stage.
- **Verified 2026-11-11 (workflow subprojects)**: host 547 and Airflow image 71 passed (P5: round-trip of mixed flat and subproject repositories; layer entry points); flat, subproject and `other/` layouts each loaded the same four DAGs; UAT 8/8 and 13/13 on `1b83568` and `f8c13e0`; Jenkins `default_ci` #11 and #12.
- **Verified 2026-11-10 (Spark session helper)**: UAT runs on `ad1ca8d`, `41ee812`, `42de0f3` (8/8, 13/13 each; `--entity` through `parse_task_args`; application `uat-test_environment`); Jenkins `default_ci` for each.
- **User-confirmed after closure (2026-11-10)**: an interactive JupyterHub run of the notebooks on the new image.
- **Not run**: a production run; a CI refusal on a pushed invalid branch.
- **Limits**:
  - parse-time execution of extra repository `.py` files until an enforcing bundle class exists (later phase);
  - single-container `local[*]` Spark;
  - no templating in `args` or `task_args`;
  - anyone who may trigger a DAG may set `task_args` (Airflow roles are platform-wide);
  - workload code runs on the shared Python 3.10 environment plus the repository's `requirements.txt` (see `workload-python-environment.md`).
