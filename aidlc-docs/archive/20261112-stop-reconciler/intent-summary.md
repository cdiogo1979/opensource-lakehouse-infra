# Intent Summary: Stop and Start the Scheduled Reconciler

## Intent
Stop and Start the Scheduled Reconciler (`20261112-stop-reconciler`)

## Objective
lakehouse.sh stop and start manage the scheduled reconciler with the rest of the stack, and the reconciler stops cleanly.

## Date
2026-11-12

## Scope
Included: scripts/lakehouse.sh stop and start, infra/polaris/reconciler/run.sh signal handling, operations docs, contract tests, canonical knowledge. Excluded: Airflow (own start-airflow/stop-airflow).

## Units / workstreams
operations

## Major requirements
- FR-1 stop stops the reconciler first.
- FR-2 start starts it last when set up.
- FR-3 docs and tests; the loop exits on SIGTERM (found live).

## Architecture and design decisions
- Manage the reconciler only once the product bootstrap created it, so a fresh start without products doesn't start it.

## Implementation decisions
- RECONCILER_COMPOSE with profile scheduled-reconciliation; reconciler_exists via docker inspect; trap plus background sleep and wait in run.sh.

## Deviations
- Stages approved in advance with the stated plan; the SIGTERM handling was added after the live check showed exit 137.

## Verification
construction/build-and-test/build-and-test-summary.md: tests 88 passed; live stop stopped the reconciler; docker stop 0 s, exit 0. Not run live: start (stack stopped by the user).

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/lakehouse-product-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Superseded decisions
- The reconciler outside lakehouse.sh start and stop.

## Archived artifacts
- aidlc-docs/archive/20261112-stop-reconciler/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261112-stop-reconciler/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261112-stop-reconciler/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261112-stop-reconciler/full-artifacts/scripts/lakehouse.sh
- aidlc-docs/archive/20261112-stop-reconciler/full-artifacts/infra/polaris/reconciler/run.sh
- aidlc-docs/archive/20261112-stop-reconciler/full-artifacts/docs/reference/operations.md
- aidlc-docs/archive/20261112-stop-reconciler/full-artifacts/tests/operations/test_compose_modules_contract.py
- aidlc-docs/archive/20261112-stop-reconciler/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/lakehouse-product-access.md
- aidlc-docs/archive/20261112-stop-reconciler/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261112-stop-reconciler/full-artifacts/`
