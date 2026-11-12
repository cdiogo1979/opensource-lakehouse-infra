# PR request — Vulnerability scanning of images and the workload lock

## Problem
Dependabot alerts covered only the manifests GitHub reads: not the workload Python lock (`requirements.lock`), not what is inside the container images, and GitHub's advisory database has no operating-system packages. Manifests of retired components under `aidlc-docs/archive/` add noise.

## Solution
- `scripts/verify/list-images.py`: every external image from the Compose files and current Dockerfiles, with their sources and pinning (`--check` fails on images not pinned by digest).
- `scripts/verify/vulnerability-scan.py`: Trivy (official image pinned by digest) scans each image (`linux/arm64`) and the workload lock once, then submits the packages to the dependency graph (Dependabot alerts for language packages) and uploads findings of MEDIUM and above as SARIF to Code scanning (OS packages included); `--dry-run` for local use.
- `.github/workflows/vulnerability-scan.yml`: on push to `main`, weekly and on demand; `permissions: {}` with only `contents: write` and `security-events: write` for the job; `actions/checkout` pinned by commit, credentials not persisted; no third-party scanning action.
- Docs: `docs/reference/vulnerability-alerts.md` (feeds, fixing, the one-time auto-triage rule for archive manifests, gaps), security, scripts, README.

## Verification
Tests 635 passed, 3 skipped. Local dry runs: workload lock 56 packages and 5 findings (pyarrow 17.0.0 HIGH; requests, tornado MEDIUM); postgres 49 packages, 83 findings; polaris 711 packages, 418 findings. First workflow run on push.

## Deployment
Push to `main` runs the workflow; then create the archive auto-triage rule in Settings (see the docs).

## Risks and limitations
Not covered: Jenkins plugins (Jenkins' own warnings), the Spark image's downloaded jars, images not pinned by digest (rustfs, the maven build stage) are scanned by tag.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
