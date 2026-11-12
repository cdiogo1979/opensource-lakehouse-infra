# Intent Summary: Scan Stale Targets

## Intent
Scan Stale Targets (`20261112-scan-stale-targets`)

## Objective
Close the Code scanning alerts and dependency snapshots of images that leave the scan.

## Date
2026-11-12

## Scope
Included: close_stale in vulnerability-scan.py, tests, docs. Excluded: scanning built images (item 2).

## Units / workstreams
supply-chain

## Major requirements
- FR-1 empty SARIF for stale categories.
- FR-2 empty snapshot for stale correlators.
- FR-3 prefix guard, fail loudly.
- FR-4 docs.

## Architecture and design decisions
- Derive stale targets from the existing Trivy analyses on the ref.

## Implementation decisions
- Only full non-dry runs close; paginated listing.

## Deviations
- Stages and push pre-approved by the user.

## Verification
construction/build-and-test/build-and-test-summary.md: 658 passed; run 43213687800 success; dependency graph 6058 -> 5489.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Superseded decisions
- None recorded

## Archived artifacts
- aidlc-docs/archive/20261112-scan-stale-targets/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261112-scan-stale-targets/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261112-scan-stale-targets/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261112-scan-stale-targets/full-artifacts/scripts/verify/vulnerability-scan.py
- aidlc-docs/archive/20261112-scan-stale-targets/full-artifacts/tests/operations/test_vulnerability_scan.py
- aidlc-docs/archive/20261112-scan-stale-targets/full-artifacts/docs/reference/vulnerability-alerts.md
- aidlc-docs/archive/20261112-scan-stale-targets/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261112-scan-stale-targets/full-artifacts/`
