# Intent Summary: Materialized View Promotion

## Intent
Materialized View Promotion (`20261111-mv-promotion`)

## Objective
Developers develop and test StarRocks materialized views in dev; the views reach UAT and prod through the normal process (branches, CI, Airflow) instead of by hand.

## Date
2026-11-11

## Scope
Included: MV file rules and CI check, mv_deploy module, factory deploy task and on-demand DAG, writer token login in the reconciler, scheduler mounts, bundle sparse_dirs, docs, the staged-mount fix (CR-2), and in the sample repository the two tpch views (CR-1), tests, README, AGENTS.md, knowledge. Excluded: synchronous refresh before swap, per-view tasks (user decisions), production deploy trigger.

## Units / workstreams
platform, sample-product

## Major requirements
- FR-1 to FR-3: views declared in materialized_views/<project>/<name>.sql with three placeholders, checked in CI.
- FR-4 to FR-6: the platform deploys them as the writer (create, replace by swap, drop managed, keep, skip missing tables) before every pipeline run and on demand, and logs the outcome.
- FR-7 / CR-1: mv_tpch_current (latest load day, all details) and mv_tpch_day_nation_segment.
- CR-2: staged mounts keep their inode when unchanged (core reconciler failed after start-airflow).

## Architecture and design decisions
- Declared files deployed by platform code; product code never holds a StarRocks login.
- Writer token login (probe P1): authentication_jwt with Keycloak keys; the broker issues the token; writers lose password login.
- Marker comment with a digest identifies managed views; replace by create plus atomic SWAP (probe P2).
- One deploy task; only new or changed files cause work; no synchronous refresh before swap (user decisions).

## Implementation decisions
- OpenID Connect client handler for pymysql (capability byte, length-encoded token).
- Missing source table detected by StarRocks' 'Unknown table' (probe P2c).
- materialized_views added to bundle sparse_dirs and the bundle config check (found live).

## Deviations
- Functional design folded into the application design.
- A failed 'git revert -q' made one pipeline live check run on the removal commit; redone.
- During the release a failed tree check did not stop the uat force-push, which reset sample uat to main for about a minute; corrected by pushing the squashed commit to main and uat.

## Verification
construction/build-and-test/build-and-test-summary.md: host 628 passed, 3 skipped; Airflow image 118 passed; StarRocks 49 passed; sample 110 passed, 2 skipped; live UAT create, repeat, replace by swap, drop, pipeline step, restore; query rewrite traced.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/airflow-workflows.md
- aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/starrocks-sql-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/materialized-view-promotion.md

## Superseded decisions
- Writer users on LDAP password login.
- Views in UAT and prod made by hand.

## Archived artifacts
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/infra/airflow/lakehouse_dags/mv_deploy.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/infra/airflow/lakehouse_dags/spec.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/infra/airflow/lakehouse_dags/factory.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/infra/airflow/lakehouse_dags/__init__.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/infra/airflow/lakehouse_dags/validate.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/infra/airflow/validate-bundle-config.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/infra/products/data_products.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/infra/starrocks/reconcile-starrocks-users.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/infra/starrocks/starrocks_common.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/scripts/setup/prepare-runtime.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/scripts/setup/prepare-starrocks-certificates.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/scripts/setup/prepare-ldap-certificates.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/scripts/verify/dag-factory-tests.sh
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/compose.airflow.yml
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/tests/airflow/test_mv_promotion.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/tests/airflow/test_dag_factory.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/tests/airflow/test_workflow_spec.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/tests/starrocks/test_starrocks_bootstrap_contract.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/tests/starrocks/test_starrocks_properties.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/tests/operations/test_runtime_staging.py
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/docs/reference/data-products.md
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/docs/reference/starrocks.md
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/docs/reference/limitations.md
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/docs/security.md
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/docs/journeys/data-product-developer.md
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/airflow-workflows.md
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/starrocks-sql-access.md
- aidlc-docs/archive/20261111-mv-promotion/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261111-mv-promotion/full-artifacts/`
