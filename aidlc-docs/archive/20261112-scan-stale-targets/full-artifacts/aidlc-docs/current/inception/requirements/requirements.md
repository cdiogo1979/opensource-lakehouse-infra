# Requirements — Scan Stale Targets

## Request
"seems the number of critical issues in the spark runtime increased" → "lets proceed with 1, proceed with all you prpoposed tests and recommendations".

## Finding
Each target has its own Code scanning category and dependency-snapshot correlator (`vulnerability-scan/<name>`). GitHub closes alerts only when a newer upload for the same category lacks them, and keeps a snapshot until the same correlator is resubmitted. `tabulario/spark-iceberg` left the scan with the Spark base change, so its 255 critical alerts (and its packages in the dependency graph) stay open next to the new `apache/spark` ones (48 critical upstream; 23 in the built image).

## Requirements
- **FR-1** After scanning, the workflow lists the existing Trivy analyses on the ref (`GET /repos/{repo}/code-scanning/analyses?tool_name=Trivy&ref=...`, paginated) and, for each `vulnerability-scan/<name>/` category not among the current targets, uploads an empty SARIF in that category (tool `Trivy`), so its alerts close as fixed.
- **FR-2** For the same stale names, it submits an empty dependency snapshot with correlator `vulnerability-scan/<name>`, so their packages leave the dependency graph.
- **FR-3** Only categories with the `vulnerability-scan/` prefix are touched; a failure to list analyses fails the run after the scans (reported), never silently.
- **FR-4** The run logs which targets were closed. Docs: the vulnerability-alerts page explains it.
- **NFR-1** Unit tests (stale computation, empty SARIF and snapshot, pagination, prefix guard); the first run after the push must close the `spark-iceberg` category (check by the user: the alerts move to closed).
