# Requirements — Platform DAG Factory

## Intent Analysis
- **Request**: move the DAG-creation logic out of product repositories. A repository then holds only:
  - workflow JSON (DAG and task definitions);
  - its code (`notebooks/`, all of it, also used by Jupyter);
  - `configs/` (also used by Jupyter);
  - a minimal stub.
- **Type**: refactoring across two repositories, with a security improvement: no product repository code runs in the scheduler's tasks.
- **Scope**:
  - **This workspace**: the platform package, Compose mounts, bundle directories, the validator in Jenkins, docs and tests.
  - **`cdiogo1979/opensource-lakehouse`**: the JSON, the stub, factory removal, `cli.py`, tests, docs, `Jenkinsfile`.
- **Complexity**: moderate.
- **Depth**: standard.
- **Answers**: Q1 to Q10 in `requirement-verification-questions.md`.

## Functional Requirements

### FR-1 Platform package `lakehouse_dags` (Q1 B)
- **Location**: the code lives in this workspace (`infra/airflow/lakehouse_dags/`) and holds today's factory behavior: container lifecycle, broker registration and revocation, `spark-submit`, output redaction, and DAG kwargs.
- **Mount**: read-only into the `airflow-dag-processor` and `airflow-scheduler` containers, and importable there (on `PYTHONPATH`).
- **Validation module**: the JSON validation is standard-library only, so it can also run without Airflow (FR-7).

### FR-2 Repository stub
- **The file**: a repository has exactly one DAG file, `dags/lakehouse.py`, of two lines (import, then `load_workflows(...)`) plus a comment.
  - Airflow's safe-mode discovery parses only files that contain both "airflow" and "DAG", so the stub contains both words.
  - The stub passes its own location, so DAGs stay in the product's bundle.
- **Without workflows**: if `workflows/` is missing or empty, the stub produces no DAG and no error.

### FR-3 Workflow JSON v1 (Q3 A, Q4 C)
- **File**: `workflows/<name>.json`, one DAG per file; the file name must equal `name`.
- **Top-level fields**:
  - `apiVersion` = `lakehouse.local/workflow/v1`
  - `name`: `[a-zA-Z0-9_.-]+`
  - `schedule`: `null` or a string
  - optional `description` and `tags` (list of strings)
  - `tasks`: non-empty
- **Task fields**:
  - `name`: `[a-zA-Z0-9_.-]+`, unique
  - `entrypoint`: a bare `*.py` name that exists in `notebooks/workload/`
  - optional `runs_after` (existing task names, no self-reference, no duplicates, no cycle)
  - optional `args` (list of strings)
  - optional `retries` (integer, 0 to 10)
  - optional `retry_delay_seconds` (integer, 0 to 3600)
  - optional `execution_timeout_seconds` (integer, 1 to 86400)
- **Strictness**: unknown keys, wrong types, and invalid values are refused with a message that names the file and field.
- **Python API**: not supported for repositories (Q3).

### FR-4 Generated DAG
- **Same as today**:
  - DAG ID `<bundle>-<name>`
  - tags `[<bundle>, "spark", *tags]`
  - `start_date` 2024-01-01, `catchup` false, `rerun_with_latest_version` false
  - one reusable Spark container per run
  - `submit_<task>` tasks in `runs_after` order (parallel without predecessors)
  - `stop_cluster` (`ALL_DONE`) and `verify_workloads_succeeded`
  - broker registration, renewal, and revocation
- **Config check in the Spark container (Q2 A)**: `validate_environment` runs inside the run's Spark container as the first command after `create_cluster`. It calls the repository's `notebooks/common/config_loader.load_environment_config(environment, config_dir, product)`. No product repository code is imported or run in the scheduler.
- **Task options**:
  - `retries`, `retry_delay_seconds` and `execution_timeout_seconds` apply to that task's `submit_` task.
  - `args` are appended to the `spark-submit` command after `-- ` (Q5 A).
- **Bundle names (Q6 A)**: only `<product>-main` (environment `prod`) and `<product>-uat` (`uat`). Any other bundle or path raises an import error naming the bundle.

### FR-5 Bundle directories
`sparse_dirs` becomes `dags`, `workflows`, `notebooks`, `configs`, in `data_products.BUNDLE_KWARGS` and the validator's `FIXED_KWARGS`. The fingerprint change recreates Airflow once.

### FR-6 Workload repository change (Q8 A)
- **Add**: `workflows/test_environment.json`, equivalent to today's `dags/test_environment.py`, and the stub.
- **Remove**: `dags/dag_factory.py`, `dag_defaults.py`, `spark_output.py`, `.airflowignore`, and `test_environment.py`.
- **`notebooks/common/cli.py`**: returns the arguments after `--` as `task_args`, empty when absent. Direct and Jupyter use are unchanged.
- **Tests**: factory tests move to the platform. Tests that import `dag_defaults` are removed or ported. A test is added for `cli.py`'s extra arguments.
- **`Jenkinsfile`**: a "Validate workflows" stage runs `lakehouse-validate-workflows .`. The `compileall` list loses `dags/dag_factory.py` (it compiles `dags`, `notebooks`).
- **Docs**: `AGENTS.md` and `AIRFLOW_BUNDLES.md` describe the JSON contract.
- **Delivery**: tested in the scratchpad clone, then pushed to `main` and `uat` only after the user's approval, and after the platform side is live.

### FR-7 Validator in Jenkins (Q7 A)
- **Command**: `lakehouse-validate-workflows <repository root>` is available in the Jenkins container. It applies the FR-3 rules and checks the entry points exist.
- **Fails on**: any `.py` under `dags/` other than the stub (Q3), and a stub that differs from the template.
- **Exit codes**: 0 valid, 1 invalid, with messages that name files and fields.

### FR-8 Cut-over order
1. The platform package, mounts, `sparse_dirs`, and validator go live first. The old repository DAG, which imports its local factory, keeps working.
2. The workload repository change is pushed.
3. After the bundle refresh, `default-main-test_environment` and `default-uat-test_environment` keep their DAG IDs and task IDs.

### FR-9 Documentation and tests
- **README**: Airflow section (repository layout, JSON reference, stub, task arguments, validator, limits).
- **Knowledge docs**: updated at closure.
- **Platform tests**: the ported factory tests (container, broker, and redaction behavior, offline), the JSON validation rules, the graph build, and Hypothesis properties.
- **Live**: both DAGs parse from JSON, a UAT run succeeds end to end, the CI validator passes and refuses an invalid change, and the old DAG keeps working before cut-over.

## Change request CR-1 (2026-11-10, during Functional Design)
- **Request**: "you should update the readme file of the data product repository with all information".
- **README**: `README.md` of the workload repository becomes the complete guide for a data product repository. The full content is listed in BR-12 of the functional design. The stale content goes: Nessie, the `lakehouse-dev`, `lakehouse-uat` and `lakehouse-prod` bundles, the operator bundle client, and Kerberos.
- **Other docs**: `AIRFLOW_BUNDLES.md` is removed, because the README holds everything. `AGENTS.md` is updated and points to the README.
- **Bundle client removed**: `airflow_bundle_client.py`, `airflow_bundle_client.example.yml`, `airflow_bundle_config.example.json` and `tests/jenkins_deployment/test_airflow_bundle_client.py` are deleted. They served the operator-selected dev bundle, which the platform doesn't have (Q6). The `Jenkinsfile`'s `compileall` list drops `airflow_bundle_client.py`.
- **Delivery**: as FR-6, pushed only after approval.

## Non-Functional Requirements
- **NFR-1 Privilege**: no product repository Python runs in scheduler task callables. Parse-time execution of `dags/*.py` remains possible until the enforcing bundle (Q10), and the CI check flags it.
- **NFR-2 Continuity**: same DAG IDs, task IDs (except the moved `validate_environment`), broker contract, and Spark invocation, apart from the `--` extras.
- **NFR-3 No secrets**: no credentials in the JSON, the stub, logs, or the validator output. The existing redaction is kept.
- **NFR-4 Determinism**: the same JSON gives the same DAG structure. Validation is pure and standard-library only.
- **NFR-5 Mount consistency**: the dag-processor and the scheduler mount the same package path, read-only. A package change is applied by restarting both. This is documented, and the parsing processes could otherwise see a change mid-edit.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q9: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q9: A) |
| Resiliency Baseline | No | Requirements Analysis (Q9: A) |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Out of scope
- The enforcing bundle class (Q10).
- A Python DAG API for repositories (Q3).
- Changes to Jupyter, to `notebooks/` beyond `cli.py`, or to `configs/`.
- Per-product Airflow permissions.
- Distributed Spark.
