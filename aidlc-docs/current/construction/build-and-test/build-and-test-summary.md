# Build and Test Summary — Scan Stale Targets

| Check | Result |
|---|---|
| `tests/operations/test_vulnerability_scan.py` | 12 passed (4 new) |
| Host pytest | see the commit (full suite run before commit) |
| First workflow run after the push | to check: the log lists `spark-iceberg-3.5.5_1.8.1` as closed; its alerts move to closed |
