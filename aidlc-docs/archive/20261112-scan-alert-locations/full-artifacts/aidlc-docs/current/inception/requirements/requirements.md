# Requirements — Scan Alert Locations

## Request
"why is the code check looking into usr/local/bin/gosu:1" / "in code scanning , why do i see this twice" → "yes proceed with the scan imporvement".

## Findings
Trivy's SARIF gives every image result the location `<image repository>:1` (or a path inside the image, e.g. `usr/local/bin/gosu:1`) and no fingerprints, so GitHub shows a non-existent file and merges results of the same CVE in different packages (XKCP: 4 packages, 2 alerts). `spark-iceberg` yields 12 023 results in one run, beyond what GitHub keeps.

## Requirements
- **FR-1 Location**: each image result points at the repository line that pins the image (first source from `list-images.py`, e.g. `infra/spark-runtime/Dockerfile:21`); lock results at `infra/workload-python/requirements.lock` and the package's line.
- **FR-2 One alert per package**: each result gets a `partialFingerprints` entry from target, CVE, package and path in the image (not the installed version), so packages aren't merged and an alert closes when its package is fixed.
- **FR-3 Message**: first line `<package> <installed> in <image>[ at <path in image>]: fixed in <version>` (or `no fix released`), then Trivy's details.
- **FR-4 Docs**: the vulnerability-alerts page explains the alert location and that the first run after the change closes the old alerts and opens equivalent ones.
