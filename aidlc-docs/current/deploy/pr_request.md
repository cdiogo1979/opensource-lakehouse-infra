# PR request — Close alerts of images that leave the scan

## Problem
Code scanning closes an alert only when a newer upload in the same category lacks it, and the dependency graph keeps a snapshot until its correlator is resubmitted. When the Spark base changed from `tabulario/spark-iceberg` to `apache/spark`, the old image's 255 critical alerts and its packages stayed open next to the new image's.

## Solution
After a full run, `scripts/verify/vulnerability-scan.py` lists the existing Trivy analyses on the ref and, for each `vulnerability-scan/<name>/` category whose image is no longer scanned, uploads an empty SARIF in that category and an empty dependency snapshot with that correlator. Only `vulnerability-scan/` categories are touched; partial (`--only`) and dry runs never close anything; a listing failure fails the run. Docs: vulnerability-alerts page.

## Verification
Tests 12 in the scan suite (stale names, prefix guard, empty SARIF and snapshot, pagination, partial runs); the first run after the push closes the `spark-iceberg-3.5.5_1.8.1` category.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
