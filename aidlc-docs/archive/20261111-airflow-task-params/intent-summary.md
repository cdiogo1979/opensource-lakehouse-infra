# Intent Summary: Airflow Task Parameters

## Intent
Airflow Task Parameters (`20261111-airflow-task-params`)

## Objective
Enable task parameters in Airflow: values chosen when a DAG is triggered reach the workflow's tasks as task arguments.

## Date
2026-11-11

## Scope
Included: lakehouse_dags task_args module and factory wiring, tests, Airflow reference and developer journey docs, live UAT checks. Excluded: the sample repository's switch from a temporary workflow edit to a trigger value (separate intent), workflow JSON changes.

## Units / workstreams
task-params

## Major requirements
- FR-1/FR-2: one task_args object param per DAG, values per task name, checked shape and limits.
- FR-3: each value one --name=value token after the task's args, replacing the same option; other tasks unchanged.
- FR-4/FR-5: validation in create_cluster before anything starts; workflow and effective arguments logged.
- NFR: no Jinja or shell; anyone who may trigger may set values (documented).

## Architecture and design decisions
- Per-task values at trigger time with nothing declared in the workflow (user clarification), in the same shape as a notebook's TASK_ARGS_VALUES.
- Trigger values replace the same workflow option; the job's own parser still decides which options it accepts.
- Values are resolved in Python by the factory; LakehouseOperator keeps template_fields empty.

## Implementation decisions
- task_args.py uses only the standard library (host-testable) and reuses spec._printable.
- Probe P1: object Param round-trips and conf overrides params, but Airflow doesn't validate the object's content.

## Deviations
- Requirements needed a follow-up question after the first answer asked for per-task trigger values.

## Verification
construction/build-and-test/build-and-test-summary.md: host 608 passed, 3 skipped; Airflow image 81 passed; property test; live UAT run with one task value succeeded with the expected effective arguments; invalid task_args failed at create_cluster with no container.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/airflow-workflows.md

## Superseded decisions
- Task arguments only from the workflow file (a one-off value needed a temporary workflow edit).

## Archived artifacts
- aidlc-docs/archive/20261111-airflow-task-params/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261111-airflow-task-params/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261111-airflow-task-params/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261111-airflow-task-params/full-artifacts/infra/airflow/lakehouse_dags/task_args.py
- aidlc-docs/archive/20261111-airflow-task-params/full-artifacts/infra/airflow/lakehouse_dags/factory.py
- aidlc-docs/archive/20261111-airflow-task-params/full-artifacts/tests/airflow/test_task_args.py
- aidlc-docs/archive/20261111-airflow-task-params/full-artifacts/tests/airflow/test_dag_factory.py
- aidlc-docs/archive/20261111-airflow-task-params/full-artifacts/docs/reference/airflow.md
- aidlc-docs/archive/20261111-airflow-task-params/full-artifacts/docs/journeys/data-product-developer.md
- aidlc-docs/archive/20261111-airflow-task-params/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/airflow-workflows.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261111-airflow-task-params/full-artifacts/`
