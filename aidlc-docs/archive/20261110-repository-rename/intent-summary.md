# Intent Summary: Repository Rename

## Intent
Repository Rename (`20261110-repository-rename`)

## Objective
Follow the user's renames of the workload repository (opensource-lakehouse to opensource-lakehouse-sample-dp) and of this workspace's folder (opensource-lakehouse-infra-v2 to opensource-lakehouse-infra): product file, docs, tests, notebooks, the stack recreated from the new folder; plus two small fixes (no REST metrics reports, the Nessie log message).

## Date
2026-11-11

## Scope
Included: data-products/default.yaml, README, two platform tests, the workload notebooks' Initialization path and docs (932feee), the stack recreation including four containers start doesn't recreate, CR-1 rest-metrics-reporting-enabled=false in lakehouse_spark, CR-2 the test_environment log message (cb80fc5). Excluded: the knowledge folder's name and the archives (kept as identifiers and history); the user's own clones.

## Units / workstreams
rename

## Major requirements
- FR-1: the stack on the new workspace folder, no container referring to the old one.
- FR-2 to FR-4: the product file, platform docs and tests, and the workload notebooks and docs on the new repository name and path.
- CR-1: no REST metrics reports from Spark sessions; CR-2: no Nessie reference in test_environment's log.

## Architecture and design decisions
- The knowledge folder name and the archives keep the old workspace name, as stable identifiers and history.
- Negative tests about sibling ../opensource-lakehouse paths keep the old name.

## Implementation decisions
- keycloak-db, polaris-db, airflow-postgres and polaris-group-reconciler force-recreated with --no-deps; airflow-postgres with placeholders for interpolation-only variables it doesn't use.
- rest-metrics-reporting-enabled=false per catalog in lakehouse_spark.catalog_settings (property verified in Iceberg 1.10.2's RESTSessionCatalog).

## Deviations
- The products test fixture compared with default.yaml was found by the suite, not in the plan.
- start and start-airflow left four containers on the old folder; recreated separately.

## Verification
See construction/build-and-test/build-and-test-summary.md. Host 530 passed, 3 skipped; workload 85 passed, lint clean. Live: 0 containers refer to the old folder; bundles on the renamed repository at cb80fc5; UAT 8/8 and 13/13; Polaris 0 metrics requests during the runs (4 the hour before); Jenkins default_ci main #9 and uat #9 SUCCESS from the new URL; JupyterHub healthy and admitting users. Not run: a production run; the user's local clone remote and notebook server restart were still pending at approval.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/airflow-workflows.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/workload-python-environment.md

## Superseded decisions
- The workload repository name opensource-lakehouse replaced by opensource-lakehouse-sample-dp; the Initialization path ~/work/opensource-lakehouse replaced by ~/work/opensource-lakehouse-sample-dp.

## Archived artifacts
- aidlc-docs/archive/20261110-repository-rename/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261110-repository-rename/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261110-repository-rename/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261110-repository-rename/full-artifacts/aidlc-docs/current/compaction/20261110-repository-rename/manifest.json
- aidlc-docs/archive/20261110-repository-rename/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261110-repository-rename/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/airflow-workflows.md
- aidlc-docs/archive/20261110-repository-rename/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/workload-python-environment.md
- aidlc-docs/archive/20261110-repository-rename/full-artifacts/data-products/default.yaml
- aidlc-docs/archive/20261110-repository-rename/full-artifacts/README.md
- aidlc-docs/archive/20261110-repository-rename/full-artifacts/infra/workload-python/python/lakehouse_spark.py
- aidlc-docs/archive/20261110-repository-rename/full-artifacts/tests/jenkins/test_product_pipelines.py
- aidlc-docs/archive/20261110-repository-rename/full-artifacts/tests/products/test_repo_and_bundles.py
- aidlc-docs/archive/20261110-repository-rename/full-artifacts/tests/workload_env/test_spark_session.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261110-repository-rename/full-artifacts/`
