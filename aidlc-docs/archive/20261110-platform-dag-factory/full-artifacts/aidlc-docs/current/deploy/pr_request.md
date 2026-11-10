# PR Request — Platform DAG factory

_Proposed PR description for this infrastructure repository. No pull request has been created, because this workspace has no git metadata. The companion workload change is already on `main` and `uat` of `cdiogo1979/opensource-lakehouse` (`9cbd6f8`), pushed on the user's approval._

## Problem
- **Logic in every repository**: each product repository carried its own Airflow DAG factory (542 lines: Spark container lifecycle, Docker calls, token broker calls).
- **Privileged code**: that code ran in the scheduler, which holds the Docker socket and the broker control token. A product repository could change how containers start or how the broker is called.

## Solution
- **Platform package `infra/airflow/lakehouse_dags`**, mounted read-only into the dag-processor and the scheduler:
  - `spec`, `identity` and `validate` use only the standard library;
  - `factory` is the ported container, broker and submit logic.
- **Product repositories** declare DAGs in `workflows/<name>.json` (workflow JSON v1):
  - DAG fields: `name`, `schedule`, `description` and `tags`;
  - task fields: `name`, `entrypoint`, `runs_after`, `args`, `retries`, `retry_delay_seconds` and `execution_timeout_seconds`.

  They keep `notebooks/` and `configs/`, which Jupyter also uses, and a fixed two-line stub, `dags/lakehouse.py`.
- **DAG shape**: the same DAG and task IDs as before.
  - `validate_environment` now runs the repository's `config_loader` **inside the Spark container**, after `create_cluster`, so no repository code runs in the scheduler.
  - `args` follow `--` as a list.
  - No task renders templates, so `{{ conn.* }}` and `{{ var.* }}` cannot leak Airflow connections or variables into product code.
- **Errors**: strict validation; one invalid file gives a single import error listing every problem by file and field.
- **Bundles**: only `<product>-main` (environment prod) and `<product>-uat` are accepted. `sparse_dirs` now includes `workflows`, and `sync-bundle-checkouts.py` updates existing checkouts, because Airflow applies `sparse_dirs` only on the first clone.
- **CI**: Jenkins provides `lakehouse-validate-workflows`, which also refuses extra `.py` files in `dags/` and a modified stub.
- **Decisions**: Q1 mount; Q2 config check in the container; Q3 JSON only; Q4 args, retries and timeouts; Q5 args after `--`; Q6 product bundles only; Q7 validator in Jenkins; Q8 push after approval; Q9 partial property-based testing; Q10 the enforcing bundle class later. CR-1: the workload README is the complete guide.

## Main changes
| Area | Paths |
|---|---|
| Package | `infra/airflow/lakehouse_dags/{__init__,spec,identity,factory,redact,validate}.py` |
| Wiring | `compose.airflow.yml`, `compose.jenkins.yml`, `infra/jenkins/bin/lakehouse-validate-workflows`, `infra/products/data_products.py`, `infra/airflow/validate-bundle-config.py`, `scripts/setup/sync-bundle-checkouts.py`, `scripts/lakehouse.sh` |
| Docs and tests | `README.md`; `tests/airflow/{workflow_strategies,test_workflow_spec,test_dag_factory,test_bundle_checkout_sync}.py`; `scripts/verify/dag-factory-tests.sh` |
| Workload reference | `aidlc-docs/current/deploy/opensource-lakehouse.patch` (= `515e403..9cbd6f8`) |

## Verification
- **Suites**: host 458 passed and 3 skipped; Airflow image 49 passed; workload repository 36 passed, lint clean, validator OK.
- **Live**:
  - the old DAGs kept working with the platform side live;
  - after the push, both DAGs come from the stub with unchanged IDs;
  - a UAT run succeeded with 7 of 7 tasks;
  - Jenkins `default_ci` `main` #2 and `uat` #2 succeeded with the validation stage.
- **Open**: one transient "dubious ownership" failure at a task's bundle refresh, in the first UAT run.

## Risks and limitations
- **Parse-time code**: a repository could still add `.py` files under `dags/`; CI refuses them, but Airflow would parse them. The enforcing bundle class is a later phase.
- **Shared factory**: a factory change affects every product at once.
- **Mount**: changes are visible through the mount immediately; apply them with `start-airflow`.
- **No templates in `args`**: a job that needs a run date works it out itself.
- **Packages**: entry points use the Spark image's packages only. Shared requirements for Airflow and Jupyter are the next intent.
