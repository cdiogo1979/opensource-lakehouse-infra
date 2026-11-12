# PR request — Jupyter images: patched base, no Lab downgrade

## Problem
Trivy and Dependabot reported HIGH and CRITICAL findings in the Jupyter images: our requirements pinned JupyterLab 4.3.5 and notebook 7.3.2 (downgrading the base and keeping known vulnerabilities), the base digests (2026-10-20) carried old Brotli, certifi, oauthlib, the zip crate in rattler and Ubuntu packages, and they were arm64-only.

## Solution
- Both images on JupyterHub 6.1.1-7 (rebuilt 2026-11-07), multi-architecture digests.
- `infra/jupyter/singleuser/requirements.txt` no longer pins `jupyterlab` or `notebook`; the install is constrained to the base's versions (`pip list --format=freeze`), so an extension can't downgrade them; a test guards it.
- `apt` and `libapt-pkg7.0` upgraded in both images.
- Docs: JupyterHub versions; the arm64 limitation no longer includes the Jupyter base images.

## Verification
Trivy: Jupyter-owned HIGH/CRITICAL findings 40 -> 7 packages (single-user) and 9 -> 1 (Hub); the rest are explained in the build-and-test summary. Tests 653 passed, 3 skipped; workload parity OK; live sign-in, server and kernel checked by the user.

## Deployment
Rebuild with `./scripts/lakehouse.sh start` (done); the next scan run closes the matching alerts.

## Follow-ups
The workload environment's pip 23.0.1 and setuptools 65.5.0 (both images) go with the workload-lock intent; the Spark jars with the Spark base intent.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
