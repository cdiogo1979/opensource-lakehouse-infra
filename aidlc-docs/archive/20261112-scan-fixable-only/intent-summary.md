# Intent Summary: Code Scanning Fixable Findings Only

## Intent
Code Scanning Fixable Findings Only (`20261112-scan-fixable-only`)

## Objective
Upload only findings with a released fix to Code scanning.

## Date
2026-11-12

## Scope
Included: fixable_only() in vulnerability-scan.py, test, docs. Excluded: Dependabot snapshots (unchanged), OS upgrades (next intent).

## Units / workstreams
supply-chain

## Major requirements
- FR-1 SARIF keeps only findings with a fixed version, every severity.
- FR-2 snapshots unchanged.
- FR-3 full JSON kept locally; counts logged.
- FR-4 docs.

## Architecture and design decisions
- Filter in the scanner: Trivy 0.76.1 convert has no --ignore-unfixed.

## Implementation decisions
- Filter before relocation, after the snapshot.

## Deviations
- Requirements and stages accepted in advance by the user (recommended decisions); push approved separately.

## Verification
construction/build-and-test/build-and-test-summary.md: 663 passed, 3 skipped; dry run 2 382 uploaded, 1 492 left out; workflow run checked after the push.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Superseded decisions
- Every Trivy finding of MEDIUM and above uploaded (infra-vulnerability-coverage).

## Archived artifacts
- aidlc-docs/archive/20261112-scan-fixable-only/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261112-scan-fixable-only/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261112-scan-fixable-only/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261112-scan-fixable-only/full-artifacts/scripts/verify/vulnerability-scan.py
- aidlc-docs/archive/20261112-scan-fixable-only/full-artifacts/tests/operations/test_vulnerability_scan.py
- aidlc-docs/archive/20261112-scan-fixable-only/full-artifacts/docs/reference/vulnerability-alerts.md
- aidlc-docs/archive/20261112-scan-fixable-only/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261112-scan-fixable-only/full-artifacts/`
