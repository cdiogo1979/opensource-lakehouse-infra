# Intent Summary: Scan Alert Locations

## Intent
Scan Alert Locations (`20261112-scan-alert-locations`)

## Objective
Code scanning alerts point at the pinning line, one per package, with a clear first line.

## Date
2026-11-12

## Scope
Included: vulnerability-scan.py SARIF rewrite, tests, vulnerability-alerts docs. Excluded: what is scanned.

## Units / workstreams
supply-chain

## Major requirements
- FR-1 location at the pinning line.
- FR-2 one alert per package.
- FR-3 message headline.
- FR-4 docs.

## Architecture and design decisions
- Fingerprint excludes the installed version so an alert persists until fixed.

## Implementation decisions
- relocate() parses Trivy's message fields; library/ and docker.io/ prefixes recognized as the image itself.

## Deviations
- Pre-approved small intent.

## Verification
construction/build-and-test/build-and-test-summary.md: 652 passed, 3 skipped; dry runs.

## Canonical documents updated
- None recorded

## Superseded decisions
- Trivy's own SARIF locations.

## Archived artifacts
- aidlc-docs/archive/20261112-scan-alert-locations/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261112-scan-alert-locations/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261112-scan-alert-locations/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261112-scan-alert-locations/full-artifacts/scripts/verify/vulnerability-scan.py
- aidlc-docs/archive/20261112-scan-alert-locations/full-artifacts/tests/operations/test_vulnerability_scan.py
- aidlc-docs/archive/20261112-scan-alert-locations/full-artifacts/docs/reference/vulnerability-alerts.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261112-scan-alert-locations/full-artifacts/`
