# Code Generation Plan — subprojects

- [x] **Step 1 — Review the drafts**: `infra/airflow/lakehouse_dags/spec.py` (`PROJECT`, `Workflow.project`, `Workflow.entrypoint_path`, `workflow_files` with subproject folders, `load_repository` with unique names, `parse_workflow(..., project)`) and `factory.py` (`entrypoint_path` for `submit_` tasks) against FR-1 to FR-4; fix what the review or tests find.
- [x] **Step 2 — Tests** in `tests/airflow/test_workflow_spec.py` (host): subproject loading, entry points in `notebooks/workload/<project>/`, a missing entry point named with its folder, duplicate names across folders, invalid and nested folders, other files, hidden entries, flat layouts unchanged; a Hypothesis round-trip over generated repositories mixing flat and subproject workflows (PBT-02, 07, 08).
- [x] **Step 3 — Factory test** in `tests/airflow/test_dag_factory.py` (Airflow image): a subproject workflow's `submit_` command runs `/opt/lakehouse-bundle/notebooks/workload/<project>/<entrypoint>`; the DAG ID is `<bundle>-<name>`.
- [x] **Step 4 — README**: the Airflow section's workflow fields and errors.
- [x] **Step 5 — Code summary**.
