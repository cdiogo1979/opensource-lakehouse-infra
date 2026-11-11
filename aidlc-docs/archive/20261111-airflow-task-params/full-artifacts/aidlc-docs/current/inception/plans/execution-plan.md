# Execution Plan — Airflow Task Parameters

| Stage | Decision | Reason |
|---|---|---|
| Reverse Engineering, User Stories, Application Design, Units | Skip | Inside the existing lakehouse_dags component; one unit |
| Functional Design | Skip | Rules fully stated in FR-1 to FR-5 |
| Probe | Execute | Confirm in the running Airflow 3.3.2 that an object `Param` shows in the trigger form and reaches the task through `context["params"]` |
| Code Generation | Execute | `lakehouse_dags/task_args.py` (validate, render), factory wiring, docs |
| Build and Test | Execute | DAG factory tests, property test, a live UAT trigger of `default-uat-tpch_medallion` with one task value |
| Deploy | Execute | `start-airflow`; PR description |

## Steps
1. Probe (read-only DAG parse in the Airflow image; no live trigger).
2. `infra/airflow/lakehouse_dags/task_args.py`: `check_task_args(value, task_names)` and `effective_args(workflow_args, values)`.
3. `factory.py`: the DAG gets `params={"task_args": Param({}, type="object", description=...)}`; `create_cluster` checks `task_args` first; each submit computes and logs its effective arguments.
4. Tests in `tests/airflow/` (unit and property).
5. Docs: `docs/reference/airflow.md`, `docs/journeys/data-product-developer.md`, `docs/reference/limitations.md` if needed.

## Canonical knowledge impact
| Path | Class | Reason |
|---|---|---|
| `aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/airflow-workflows.md` | UPDATE | Trigger-time task arguments, validation and rendering rules |
| `aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md` | RETAIN | No component boundary change |
