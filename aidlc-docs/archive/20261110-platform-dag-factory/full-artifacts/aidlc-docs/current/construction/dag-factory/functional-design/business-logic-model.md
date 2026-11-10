# Functional Design — dag-factory

## Domain entities (`lakehouse_dags.spec`, frozen dataclasses)
- `Task(name, entrypoint, runs_after: tuple[str, ...], args: tuple[str, ...], retries: int | None, retry_delay_seconds: int | None, execution_timeout_seconds: int | None)`
- `Workflow(name, schedule: str | None, description: str | None, tags: tuple[str, ...], tasks: tuple[Task, ...], source: str)`
- `Identity(bundle, product, environment)`
- `Problem(path, field, message)`: path relative to the repository root, and a field path such as `tasks[1].runs_after`.

## Business rules
- **BR-1 Workflow file**:
  - **Location**: `workflows/<name>.json`, UTF-8, a JSON object. Only `*.json` files directly in `workflows/` count; other files there are a problem. Files are read in sorted order.
  - **Keys**:
    - `apiVersion` (required, exactly `lakehouse.local/workflow/v1`)
    - `name` (required, `^[a-zA-Z0-9_.-]{1,100}$`, equal to the file stem)
    - `schedule` (required: `null`, or a non-empty string of at most 100 characters)
    - `description` (optional, a printable string of at most 500 characters)
    - `tags` (optional, distinct strings matching `^[a-zA-Z0-9_.:-]{1,50}$`, at most 10; `spark` and the bundle name are added automatically and refused if listed)
    - `tasks` (required, 1 to 50)
  - **Strictness**: unknown keys are refused. JSON `true` and `false` are never accepted as integers.
- **BR-2 Task**:
  - **Keys**:
    - `name` (required, `^[a-zA-Z0-9_.-]{1,100}$`, unique in the workflow)
    - `entrypoint` (required: a bare file name `^[A-Za-z0-9_][A-Za-z0-9_.-]*\.py$` that exists as a file in `notebooks/workload/`)
    - `runs_after` (optional, a list of distinct task names, empty by default)
    - `args` (optional, a list of at most 50 printable strings, each at most 500 characters; empty by default)
    - `retries` (optional, integer from 0 to 10)
    - `retry_delay_seconds` (optional, integer from 0 to 3600, only with `retries` ≥ 1)
    - `execution_timeout_seconds` (optional, integer from 1 to 86400)
  - **Strictness**: unknown keys are refused.
- **BR-3 Graph**: every `runs_after` name exists and isn't the task itself, and the graph has no cycle (Kahn's algorithm). Declaration order is kept.
- **BR-4 Identity**:
  - **Bundle name**: the parent directory of the nearest `tracking_repo` or `versions` ancestor of the stub (Airflow 3 checkout layouts).
  - **Accepted names**: `^([a-z][a-z0-9]{1,19})-(main|uat)$`. `main` maps to environment `prod`, `uat` to `uat`, and the product is the first group.
  - **Anything else** raises `ValueError("lakehouse_dags: bundle <name> is not a data product bundle")`, or `"... is not inside an Airflow bundle checkout"`.
- **BR-5 DAG**:
  - **DAG settings**: `dag_id` is `<bundle>-<workflow.name>`; description is `workflow.description`, or `Run <name> (<task names>) in one Spark container for <bundle>`; `schedule`; `start_date` 2024-01-01 UTC; `catchup` false; tags are `[<bundle>, "spark", *tags]`; `rerun_with_latest_version` false.
  - **Fixed tasks**:
    - `create_cluster` (task 1);
    - `validate_environment` (after `create_cluster`);
    - one `submit_<task.name>` per task;
    - `stop_cluster` (`ALL_DONE`, after every submit);
    - `verify_workloads_succeeded` (after every submit and `stop_cluster`).
  - **Ordering**: a task without `runs_after` runs after `validate_environment`; otherwise it runs after each predecessor's submit.
  - **Task options**: `retries`, `retry_delay` (a `timedelta`) and `execution_timeout` are set only on that task's `submit_`, and only when given.
- **BR-6 Config check (in the container)**: `exec_run(["python3", "-c", VALIDATE_SNIPPET, environment, "/opt/lakehouse-bundle/configs", product], workdir=/opt/lakehouse-bundle)`.
  - **The snippet**: inserts `/opt/lakehouse-bundle/notebooks/common` on `sys.path`, then calls `load_environment_config(argv[1], argv[2], argv[3])`.
  - **On failure**: a non-zero exit fails the task with the redacted output.
  - **The scheduler** imports no repository module.
- **BR-7 Submit**: `spark-submit --master <LAKEHOUSE_SPARK_MASTER> /opt/lakehouse-bundle/notebooks/workload/<entrypoint> --environment <env> --config-dir /opt/lakehouse-bundle/configs`, plus `--` and the `args` when there are any.
  - **No shell**: arguments are passed as a list, so values are never shell-interpreted.
  - **No templates** (added in Code Generation): every platform task is a `LakehouseOperator`, a `PythonOperator` with no `template_fields`. Otherwise Airflow would render `{{ conn.* }}` and `{{ var.* }}` found in `args` inside the scheduler and pass connection and variable values to product code.
  - **Logging**: the output is redacted (`redact_spark_output`) and logged; a non-zero exit fails the task.
- **BR-8 Container, broker, cleanup**: ported unchanged from `dag_factory.py`:
  - **Container name**: `lakehouse-<dag_id[:40]>-<sha256(run_id)[:12]>`.
  - **Broker**: registration with `{dag_id, run_id}`, and the pinned HTTPS endpoint and CA.
  - **Container**: environment (token, run handle, capability, `LAKEHOUSE_ENVIRONMENT`, `LAKEHOUSE_PRODUCT`, `PYTHONPATH=/opt/lakehouse-bundle`), mounts, and the data network.
  - **Cleanup**: on startup failure, and in `stop_cluster`, the container is removed and the run handle revoked.
- **BR-9 `load_workflows(namespace, stub_file)`**:
  - **No workflows**: if `workflows/` is absent or holds no `*.json`, nothing happens.
  - **Problems**: otherwise every file is validated first. If any problem exists, it raises one `ValueError` listing all of them (`<path>: <field>: <message>`), and builds no DAG.
  - **Success**: otherwise each DAG is built and set as `namespace["dag_<sanitized dag_id>"]`.
  - **Dependencies**: the Airflow and Docker imports happen only here.
- **BR-10 Validator (`check_repository(root)`)**: the problems from BR-1 to BR-3 for all workflows, plus:
  - `dags/lakehouse.py` is missing, or differs from `STUB_TEXT` (line endings normalized);
  - any other file under `dags/` (except `__pycache__`) exists.

  A repository without `workflows/` is valid: no DAGs. The CLI prints the problems sorted, then `N problem(s)`, exits 1 on problems, and otherwise prints `OK: <k> workflow(s)` and exits 0. It never prints file contents beyond names and fields.
- **BR-11 `cli.py`** (workload repository): `parse_args(argv)` splits `argv` at the first `--`. The part before goes through the existing parser; the part after becomes `task_args` (a list, empty by default). Existing callers keep working.

- **BR-12 Workload repository README (CR-1)**: `README.md` is the single guide. It covers:
  1. **Purpose, and what lives where**: the repository holds `workflows/`, `notebooks/` and `configs/`, plus the stub; the platform builds the DAGs, runs Spark, and issues credentials.
  2. **How a run works**: the bundles `<product>-main` (prod branch) and `<product>-uat` (UAT branch) from the product's `repo` block, refreshed every 5 minutes; DAG IDs `<bundle>-<name>`; the task chain; one Spark container per run (`local[*]`); the writer token from the broker. There are no credentials in the repository.
  3. **Repository layout**, file by file.
  4. **Workflow JSON reference**: every field with its type, limits and default; a complete example; validation behavior (one invalid file blocks all DAGs of the bundle).
  5. **The stub**: exact text; never edit it; nothing else in `dags/`.
  6. **Entry point contract**: `--environment`, `--config-dir`, extras after `--` via `cli.parse_args().task_args`; `LAKEHOUSE_ENVIRONMENT` and `LAKEHOUSE_PRODUCT`; the `notebooks/common` helpers.
  7. **Configs**: `configs/<product>/<env>.yml` with fallback to `configs/<env>.yml`, required keys, and the environments `prod`, `uat`, `dev` (`dev` for Jupyter).
  8. **Jupyter**: cloning the repository and running notebooks with the `dev` config, the shared helpers, and no Airflow involvement.
  9. **CI**: the Jenkins `<product>_ci` job (branches `main` and `uat`) and `<product>_cd` job (PR branches), the stages, and the `lakehouse-validate-workflows` stage.
  10. **How-tos**: add a workflow, add a task with arguments and retries, promote from UAT to main, run locally, check before pushing.
  11. **Limits**: no Python DAGs; repository `.py` files under `dags/` are refused by CI; no fork PRs; scans rather than webhooks; single-container Spark; public repository.

  `AIRFLOW_BUNDLES.md` is removed. `AGENTS.md` keeps the agent rules, updated to the JSON contract, and links to the README.

## Testable properties (PBT partial)
| Id | Rule | Property |
|---|---|---|
| P1 (PBT-02) | BR-1, BR-2 | For generated valid workflows, `parse(json.dumps(to_document(w)))` equals `w` (round trip through the JSON form). |
| P2 (PBT-03) | BR-3, BR-5 | For generated valid DAG task graphs: every submit task's upstream is exactly `{validate_environment}` or its predecessors' submits; every submit is upstream of `stop_cluster` and `verify_workloads_succeeded`; the generated order is a topological order of `runs_after`. |
| P3 (PBT-03) | BR-1 to BR-3 | Mutating one field of a valid workflow out of its domain (unknown key, bad name, missing entrypoint, cycle, boolean as an integer, out-of-range number) always gives at least one problem naming that field, and never an exception. |
| P4 (PBT-03) | BR-4 | Generated product bundle paths in both checkout layouts map to `(bundle, product, env)`. Generated non-product names (legacy `lakehouse-*`, `dev`, wrong suffix, bad product) are refused. |
| P5 (PBT-02) | BR-11 | For generated `before` and `after` argument lists, `parse_args(before + ["--"] + after).task_args == after` (workload repository, its own Hypothesis setup). |

Generators (PBT-07) live in `tests/airflow/workflow_strategies.py`: names, entry points, tags, argument strings, and acyclic graphs built by choosing predecessors only among earlier tasks. They use Hypothesis' default shrinking and `print_blob=True` (PBT-08, PBT-09).

## Example and contract tests
- **Ported factory tests**:
  - container naming;
  - the host-path translation;
  - broker endpoint pinning and errors suppressed;
  - the container environment and mounts (fake Docker client);
  - the submit command with and without `args`;
  - the in-container validation command;
  - cleanup on failure;
  - redaction.
- **Golden example**: `test_environment.json` gives exactly today's DAG and task IDs and edges, apart from the moved `validate_environment`.
- **Live**: the stub in a fake bundle parses through `DagBag` in the Airflow image (Build and Test).
