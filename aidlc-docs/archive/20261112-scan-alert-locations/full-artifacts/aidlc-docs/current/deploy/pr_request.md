# PR request — Code scanning alerts at the pinning line, one per package

## Problem
Trivy's SARIF located image findings at `<image repository>:1` or a path inside the image (`usr/local/bin/gosu:1`), files that don't exist in the repository, and carried no fingerprints, so GitHub merged findings of one CVE in different packages (CVE-2022-37454 in four python3.9 packages showed as two alerts).

## Solution
`scripts/verify/vulnerability-scan.py` rewrites each SARIF result before upload:
- location: the repository line that pins the image (e.g. `infra/spark-runtime/Dockerfile:21`), or the workload lock's line;
- `partialFingerprints` from target, CVE, package and path in the image (not the version), so each package is its own alert and an alert closes when its package is fixed;
- first message line: package, installed version, image (and path inside it), fixed version or "no fix released"; Trivy's details follow.
Docs: how to read an alert.

## Verification
Tests 652 passed, 3 skipped; dry runs on postgres, the lock and spark-iceberg.

## Deployment
Push; the next run closes the previous Code scanning alerts and opens the equivalent ones with the new locations.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
