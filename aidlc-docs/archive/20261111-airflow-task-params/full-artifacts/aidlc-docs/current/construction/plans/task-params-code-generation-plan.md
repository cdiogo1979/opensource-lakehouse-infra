# Code Generation Plan — Airflow Task Parameters

- [x] 1. Probe P1 (Airflow 3.3.2 image, throwaway container): object Param serializes; conf overrides params; Airflow does not validate the object's content.
- [x] 2. `infra/airflow/lakehouse_dags/task_args.py` (standard library only): `check_task_args`, `task_values`, `effective_args`, `option_name`.
- [x] 3. `factory.py`: `dag_kwargs` adds `params={"task_args": Param({}, type="object", description=<example and task names>)}`; `_create_spark_container` checks `task_args` first (`_check_run_task_args`); `_submit_spark_job` gets `task_name`, applies the run's values, logs workflow and effective arguments (redacted).
- [x] 4. Tests: `tests/airflow/test_task_args.py` (host: validation messages, rendering, one-token values, property over render-then-parse); `tests/airflow/test_dag_factory.py` (param on every DAG, invalid task_args fail before registration or container, values reach only their task).
- [x] 5. Docs: `docs/reference/airflow.md` (Trigger-time arguments), `docs/journeys/data-product-developer.md`.
