# Build and Test Summary — Scan Stale Targets

| Check | Result |
|---|---|
| `tests/operations/test_vulnerability_scan.py` | 12 passed (4 new: stale names and prefix guard, empty SARIF and snapshot, pagination, partial runs) |
| Host pytest | 658 passed, 3 skipped |
| Workflow run [43213687800](https://github.com/cdiogo1979/opensource-lakehouse-infra/actions/runs/43213687800) (push of 0efe653) | success (the closing step fails the run on any error) |
| Dependency graph | 6058 -> 5489 packages: the replaced `tabulario/spark-iceberg` snapshot is empty |

To see in the UI (signed in): Security → Code scanning, closed alerts include the `spark-iceberg` ones.
