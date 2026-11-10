# Intent Summary: Workflow Subprojects

## Intent
Workflow Subprojects (`20261111-workflow-subprojects`)

## Objective
Let product repositories group workflows by subproject (workflows/<project>/) with code in notebooks/workload/<project>/ and its medallion layer folders, keeping DAG IDs <bundle>-<name>.

## Date
2026-11-11

## Scope
Included: lakehouse_dags spec and factory, tests, README. Outside the intent at the user's request: the sample-dp move to workflows/sample and notebooks/workload/sample/other, its AGENTS.md subproject and layer layout, README and tests (1b83568, f10156f, f8c13e0). Excluded: layer folders for workflows, the subproject in DAG IDs.

## Units / workstreams
subprojects

## Major requirements
- FR-1/FR-2: workflows/<project>/<name>.json with entry points in notebooks/workload/<project>/; flat layout unchanged.
- FR-3: DAG IDs <bundle>-<name>; names unique per repository.
- CR-1/CR-2: entry points <layer>/<file>.py with bronze, silver, gold, ops, deploy, other; workflows have no layer folders.

## Architecture and design decisions
- Subproject folders resolve entry points in the matching code folder, so one subproject can't name another's code.
- The layer list is fixed in spec.LAYERS.

## Implementation decisions
- Workflow.project and entrypoint_path; workflow_files yields (path, project); load_repository enforces unique names.
- Spec and factory drafts were written before the intent was opened at the user's instruction; reviewed and kept in Code Generation.

## Deviations
- The user asked for no intent for the workload change; the platform part became this small intent when the user required it.
- CR-1 and CR-2 were added during Build and Test.

## Verification
See construction/build-and-test/build-and-test-summary.md. Host 547 passed, 3 skipped; Airflow image 71 passed. Live: flat, subproject and other/ layouts load the same four DAGs without import errors; UAT 8/8 and 13/13 on 1b83568 and f8c13e0; Jenkins default_ci main/uat #11 and #12 SUCCESS. Not run: a production run; a CI refusal on a pushed branch.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/airflow-workflows.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md

## Superseded decisions
- sample-dp's notebooks first moved flat into notebooks/workload/sample/, then into notebooks/workload/sample/other/ (CR-2).

## Archived artifacts
- aidlc-docs/archive/20261111-workflow-subprojects/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261111-workflow-subprojects/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261111-workflow-subprojects/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261111-workflow-subprojects/full-artifacts/aidlc-docs/current/compaction/20261111-workflow-subprojects/manifest.json
- aidlc-docs/archive/20261111-workflow-subprojects/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/airflow-workflows.md
- aidlc-docs/archive/20261111-workflow-subprojects/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261111-workflow-subprojects/full-artifacts/infra/airflow/lakehouse_dags/spec.py
- aidlc-docs/archive/20261111-workflow-subprojects/full-artifacts/infra/airflow/lakehouse_dags/factory.py
- aidlc-docs/archive/20261111-workflow-subprojects/full-artifacts/README.md
- aidlc-docs/archive/20261111-workflow-subprojects/full-artifacts/tests/airflow/workflow_strategies.py
- aidlc-docs/archive/20261111-workflow-subprojects/full-artifacts/tests/airflow/test_workflow_spec.py
- aidlc-docs/archive/20261111-workflow-subprojects/full-artifacts/tests/airflow/test_dag_factory.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261111-workflow-subprojects/full-artifacts/`
