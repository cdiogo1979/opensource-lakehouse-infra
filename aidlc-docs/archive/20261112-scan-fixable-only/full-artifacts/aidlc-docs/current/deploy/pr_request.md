# PR request — Upload only findings with a released fix to Code scanning

## Problem
About 40% of the Trivy findings in Code scanning (1 492 of 3 874, MEDIUM and above) have no fixed version, mostly Debian packages in the Airflow, Jenkins and token broker images. Nothing can be done about them but a dismissal, and they bury the alerts that can be fixed.

## Solution
`scripts/verify/vulnerability-scan.py` drops findings without a fixed version from the SARIF before upload, at every severity, and logs per target how many were left out. Dependency snapshots (Dependabot) are unchanged. Trivy's full JSON stays in `--out` for local review; a fix released later shows up on the next run. Docs: vulnerability alerts page.

## Verification
663 tests passed, 3 skipped; dry-run scan of the 15 targets: 2 382 uploaded, 1 492 left out.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
