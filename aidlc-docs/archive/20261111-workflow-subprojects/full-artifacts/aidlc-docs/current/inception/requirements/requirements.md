# Requirements — Workflow Subprojects

## Intent Analysis
- **Request**: "take the "subproject logic" from the test_aidlc folder AGENTS.md and bake it into the sample-dp project AGENTS.md. you can move the exiting workflows and workload notebooks to a worklows/sample and workload/sample. do not start an intent for this", then "if you need to make changes in infra project create a small intent for it".
- **Why the platform changes**: the platform's workflow rules (`lakehouse_dags.spec`) accept only `workflows/<name>.json` and an `entrypoint` file name in `notebooks/workload/`; moved files would be refused by CI and Airflow.
- **Answers** (interactive, 2026-11-11): DAG IDs stay `<bundle>-<name>`; notebooks flat in `notebooks/workload/<project>/`; AGENTS.md documents per-subproject knowledge docs (the latter two concern the workload repository, outside this intent).
- **Scope of this intent**: the platform only (`infra/airflow/lakehouse_dags`, tests, README, knowledge). The workload repository's move and AGENTS.md are done outside an intent, as the user asked.
- **Depth**: minimal.

## Functional Requirements
- **FR-1 Subproject workflows**: a workflow file may be `workflows/<name>.json` (unchanged) or `workflows/<project>/<name>.json`, with `<project>` matching `[A-Za-z0-9][A-Za-z0-9_-]{0,49}`. Hidden entries are ignored; deeper folders, other files in a subproject folder, and invalid folder names are problems.
- **FR-2 Entry points**: a subproject workflow's `entrypoint` stays a file name and must exist in `notebooks/workload/<project>/`; flat workflows keep `notebooks/workload/`. The Spark task runs `/opt/lakehouse-bundle/notebooks/workload/<project>/<entrypoint>`.
- **FR-3 Names**: DAG IDs stay `<bundle>-<name>`; a workflow name used twice in the repository (in any folders) is a problem naming both files.
- **FR-4 Compatibility**: repositories with flat workflows behave exactly as before (same DAGs, tasks and commands).
- **FR-5 Docs and tests**: README and the canonical `airflow-workflows.md`; example and Hypothesis tests for the new layout (round-trip of rendered repositories, duplicate names, entry-point paths).

## Change request CR-1 (2026-11-11, during Build and Test): medallion layer folders
- **Request**: "on the sample dp readme file , you missed the subproject + bronze/silver/gold .. logic inside workflows and workload"; answers: "workload only , workflows will be by subproject only"; "Keep them flat in sample/".
- **Decision**: an `entrypoint` is a file name, or `<layer>/<file>.py` with `<layer>` one of `bronze`, `silver`, `gold`, `ops`, `deploy`; it resolves under the workflow's code folder (`notebooks/workload/<project>/`, or `notebooks/workload/` for flat workflows). No other folder, no deeper nesting, no `..`. Workflows stay in `workflows/<project>/` (no layer folders). The Spark task runs `notebooks/workload/<project>/<layer>/<file>.py`.

## Change request CR-2 (2026-11-11, during Build and Test): an "other" folder
- **Request**: "on the sample-dp agents file put the tree sample workloads insde sample/other folder"; answer: "A real 6th folder, files moved".
- **Decision**: `other` joins the notebook layer folders (`bronze`, `silver`, `gold`, `ops`, `deploy`, `other`) for notebooks that fit no medallion layer. In the workload repository (outside this intent), `sample`'s three notebooks move to `notebooks/workload/sample/other/` and the workflows name `other/<file>.py`; DAG IDs unchanged.

## Non-Functional Requirements
- **NFR-1**: no change to the stub, the Jenkins wrapper, Airflow configuration or images; the package is mounted, so `start-airflow` applies it.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09) | Requirements Analysis |
| Resiliency Baseline | No | Requirements Analysis |
| Workflow Conventions | Yes (always enforced) | Workflow start |
