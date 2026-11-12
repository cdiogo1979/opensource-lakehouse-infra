# Build and Test Summary — Scan Alert Locations

| Check | Result |
|---|---|
| `tests/operations/test_vulnerability_scan.py` | 8 passed (3 new: image location and per-package fingerprints, lock line and stable fingerprint, image-name recognition) |
| Host pytest | 652 passed, 3 skipped |
| Dry runs | postgres 83 results / 83 fingerprints at `compose.airflow.yml:43` (gosu: "... at usr/local/bin/gosu"); lock 5 / 5 at the lock's lines; spark-iceberg 12 023 / 12 023, CVE-2022-37454 as 4 alerts at `infra/spark-runtime/Dockerfile:21` |

To check after the push: Code scanning shows repository locations; the previous alerts close and equivalent ones open once.
