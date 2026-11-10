# Requirements — Repository Rename

## Intent Analysis
- **Request**: "i renamed the opensource-lakehouse repo to opensource-lakehouse-sample-dp, what is the command i need to run to update my git folder", then "Fix all as a small intent".
- **Found**: the user also renamed this workspace's folder from `opensource-lakehouse-infra-v2` to `opensource-lakehouse-infra`. The scheduler, DAG processor, Jenkins and JupyterHub still bind-mount 6 to 9 paths of the old folder, and absolute host paths of the old folder are in their configuration (for example the broker CA that every Spark run container mounts). Running containers keep working; a restart, and new Spark run containers, would refer to the missing old path. `.runtime/` and `.env` hold no folder path.
- **Type**: configuration and documentation update, plus an operational recreation of the stack. **Depth**: minimal.

## Functional Requirements
- **FR-1 Stack on the new folder**: recreate the stack from `/Users/carlosdiogo/code_repo/opensource-lakehouse-infra` with `./scripts/lakehouse.sh start` and `start-airflow`, when no DAG run is active; afterwards no container mounts or refers to the old folder.
- **FR-2 Product file**: `data-products/default.yaml` `repo.url` becomes `https://github.com/cdiogo1979/opensource-lakehouse-sample-dp.git`. Airflow's `default-main` and `default-uat` bundles and Jenkins' `default_ci`/`default_cd` jobs follow it (bundle and job names are unchanged).
- **FR-3 Platform docs and tests**: the README's example and mentions, and the Jenkins test that asserts the generated repository, use the new name. Test fixtures that only need some URL may keep theirs.
- **FR-4 Workload repository**: the notebooks' Initialization line, the README (clone path, examples) and AGENTS.md use `~/work/opensource-lakehouse-sample-dp`; the structure test follows. Pushed to `main` and `uat` only after approval.
- **FR-5 Clones**: the user's local clone and the scratchpad clone use the new remote URL (`git remote set-url origin https://github.com/cdiogo1979/opensource-lakehouse-sample-dp.git`). The user's Jupyter clone in `~/work` is the user's to rename or re-clone (documented).
- **FR-6 Knowledge**: current knowledge documents use the new names; the knowledge project folder name and the archives stay as they are.

## Change request CR-1 (2026-11-10, during Build and Test): no REST metrics reports
- **Finding**: the user ran `test_environment.py` in Jupyter as `joe-developer`; the table was created and written, but Iceberg logged `WARN RESTMetricsReporter: Failed to report metrics … Table does not exist` (the best-effort metrics report of the creating write reached Polaris before the table was known).
- **Request** (user: "yes proceed"): `lakehouse_spark` sets `rest-metrics-reporting-enabled=false` for the three catalogs (property present in Iceberg 1.10.2's `RESTSessionCatalog`), in Airflow and Jupyter. Polaris then receives no scan or commit metrics; nothing in the stack uses them.

## Change request CR-2 (2026-11-10, during Build and Test): log wording
- **Request** (same answer): `test_environment.py`'s commit message names "Nessie GC"; this stack uses Polaris. The message drops the Nessie reference.

## Change found during Build and Test (FR-1)
- `start` and `start-airflow` did not recreate `keycloak-db`, `polaris-db`, `airflow-postgres` and the `polaris-group-reconciler`, which still bind-mounted password files from the old folder. They were force-recreated from the new folder (named data volumes kept), with no DAG run active; all services were healthy afterwards.

## Non-Functional Requirements
- **NFR-1 Data kept**: no volume is removed (no `--remove-orphans`, no reset).
- **NFR-2 Interruption**: the recreation interrupts running notebook servers and DAG runs; it is done only when no run is active.

## Verification
- No container mount or environment value refers to the old folder; the bundles clone the renamed repository; a UAT run of both DAGs passes; Jenkins `default_ci` builds both branches from the new URL; JupyterHub admits a user; the host and workload suites pass.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis |
| Property-Based Testing | No (no new business logic) | Requirements Analysis |
| Resiliency Baseline | No | Requirements Analysis |
| Workflow Conventions | Yes (always enforced) | Workflow start |
