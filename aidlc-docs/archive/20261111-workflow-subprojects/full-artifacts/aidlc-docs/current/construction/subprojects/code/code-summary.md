# Code Summary — subprojects

| File | Change | Requirement |
|---|---|---|
| `infra/airflow/lakehouse_dags/spec.py` | `PROJECT`; `Workflow.project` and `entrypoint_path`; `workflow_files` returns `(path, project)` for `workflows/` and its subproject folders; `parse_workflow(..., project)` checks entry points in `notebooks/workload/<project>/`; `load_repository` refuses invalid folder names, nested folders, other files, and names used twice; docstring | FR-1 to FR-3 |
| `infra/airflow/lakehouse_dags/factory.py` | `submit_` tasks pass `workflow.entrypoint_path(task)` | FR-2 |
| `tests/airflow/workflow_strategies.py` | `projects`, `workflows(project=...)`, `repositories()`; `write_repository` writes subproject folders | FR-5 |
| `tests/airflow/test_workflow_spec.py` | six tests: loading next to flat workflows, entry point in its folder, unique names, folder rules and hidden entries, the validator, P5 (round-trip of mixed repositories) | FR-1 to FR-5 |
| `tests/airflow/test_dag_factory.py` | a subproject task's command and an unchanged DAG ID | FR-2, FR-3 |
| `README.md` | Airflow section: subprojects; the `entrypoint` field | FR-5 |

**Draft review**: the `spec.py` and `factory.py` edits made before the intent was opened match FR-1 to FR-4 and were kept as drafted, plus the docstring.

**Tests**: host 536 passed, 3 skipped (530 before); Airflow image 58 passed (51 before).
