# Intent Summary: Reconciler and StarRocks Recovery

## Intent
Reconciler and StarRocks Recovery (`20261111-reconciler-starrocks-recovery`)

## Objective
Re-apply StarRocks' LDAP bind pattern after an FE restart and make sure the scheduled sync reaches StarRocks.

## Date
2026-11-11

## Scope
Included: the reconciler runs mounted current code, a bind-pattern step first each cycle, a healthcheck and status line, docs and tests. Excluded: a faster than one-interval recovery, a least-privilege reconciler identity.

## Units / workstreams
reconciler-recovery

## Major requirements
- FR-1 mount current code read-only.
- FR-2 bind-pattern step first, independent of Keycloak and product files.
- FR-3 healthcheck and status.
- FR-4 docs.

## Architecture and design decisions
- Mounted code instead of rebuild hooks, so the reconciler can't fall behind the product model.
- Success means every step of a cycle succeeded; unhealthy after two intervals plus a minute.

## Implementation decisions
- reconcile-starrocks-users.py --bind-pattern-only (ensure_bind_pattern).
- ENTRYPOINT /bin/sh run.sh because the mounted file is 644.
- Property P1 over the real healthcheck expression.

## Deviations
- All stages and recommended options approved in advance by the user.

## Verification
construction/build-and-test/build-and-test-summary.md: pytest 592 passed, 3 skipped; first cycle fully successful; after an FE restart the scheduled cycle restored the bind pattern in 289 s; container healthy. Not run live: the unhealthy transition (property-tested).

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/starrocks-sql-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md

## Superseded decisions
- The reconciler image's baked-in product model and scripts superseded by read-only mounts.
- The bind pattern applied only after the user sync's safety checks, superseded by a first independent step.

## Archived artifacts
- aidlc-docs/archive/20261111-reconciler-starrocks-recovery/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261111-reconciler-starrocks-recovery/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261111-reconciler-starrocks-recovery/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261111-reconciler-starrocks-recovery/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/starrocks-sql-access.md
- aidlc-docs/archive/20261111-reconciler-starrocks-recovery/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md
- aidlc-docs/archive/20261111-reconciler-starrocks-recovery/full-artifacts/infra/starrocks/reconcile-starrocks-users.py
- aidlc-docs/archive/20261111-reconciler-starrocks-recovery/full-artifacts/infra/polaris/reconciler/run.sh
- aidlc-docs/archive/20261111-reconciler-starrocks-recovery/full-artifacts/infra/polaris/reconciler/Dockerfile
- aidlc-docs/archive/20261111-reconciler-starrocks-recovery/full-artifacts/compose.core.yml
- aidlc-docs/archive/20261111-reconciler-starrocks-recovery/full-artifacts/scripts/lakehouse.sh
- aidlc-docs/archive/20261111-reconciler-starrocks-recovery/full-artifacts/README.md
- aidlc-docs/archive/20261111-reconciler-starrocks-recovery/full-artifacts/tests/polaris/test_reconciler_recovery.py
- aidlc-docs/archive/20261111-reconciler-starrocks-recovery/full-artifacts/tests/starrocks/test_starrocks_bootstrap_contract.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261111-reconciler-starrocks-recovery/full-artifacts/`
