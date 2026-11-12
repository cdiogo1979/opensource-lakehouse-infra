# Requirements — Infra Vulnerability Coverage

Depth: standard (supply-chain monitoring; a GitHub workflow with write permission to the dependency graph).

## Request
"how could i monitor all software components (images, packages , etc) for security issues reported" → "i turnned on Dependabot alerts for both repos" → "make this as two intents, one for each repo".

## Answers
- Coverage: **Trivy in GitHub Actions**, submitting to the dependency graph; no files renamed.
- Archive: **exclude `aidlc-docs/archive/`** if GitHub supports it for alerts (probe first); otherwise a documented dismissal rule. Archived history stays untouched.

## Functional requirements
- **FR-1 Inventory**: a script (`scripts/verify/list-images.py`) lists every image the platform runs or builds from: `image:` references in the `compose.*.yml` files and `FROM` lines of the current Dockerfiles (not `aidlc-docs/`), with their pinned digests; locally built `local/...` images are excluded (their bases and locks are covered).
- **FR-2 Workflow**: `.github/workflows/dependency-submission.yml` runs on push to `main`, weekly, and on demand; Trivy (pinned version) scans each listed image and the workload Python lock (`infra/workload-python/requirements.lock`) and submits the results to GitHub's dependency graph (dependency submission API), so they appear in Dependabot alerts.
- **FR-3 Least privilege**: the workflow has `contents: write` only (required by dependency submission) and no other permission; actions pinned by commit SHA; no secrets beyond `GITHUB_TOKEN`.
- **FR-4 Archive**: alerts from `aidlc-docs/archive/` are excluded if GitHub supports a path exclusion for alerts; otherwise the triage page says to dismiss them as not used.
- **FR-5 Docs**: `docs/security.md` (supply chain: monitoring) and a short triage page (`docs/reference/vulnerability-alerts.md`): where alerts come from, what each covers, how to fix (bump the digest, version or lock in an intent), and the remaining gaps (Jenkins plugins: Jenkins' own warnings; Spark image jars).

## Non-functional
- **NFR-1** The workflow never builds or runs platform images; it only pulls and scans pinned ones.
- **NFR-2** Tests: the image list script (unit tests on the Compose and Dockerfile parsing; every listed image is pinned by digest or tag as in the files).

## Probes
- **P1** Does GitHub support excluding paths from Dependabot alerts (`dependabot.yml` `exclude-paths`, or dependency-graph settings)? Read GitHub's documentation.
- **P2** Trivy's GitHub dependency-submission output for an image and for the lock (format, manifest names, arm64-only images such as the JupyterHub digests): run once in the workflow after push, and check the dependency graph.

## Change requests
- **CR-1** (user, after a local Trivy check): GitHub's advisory database has no OS-package ecosystems (apk, deb), so Dependabot can't alert on image OS packages. The workflow also uploads Trivy's results as SARIF to Code scanning (OS packages included, severities MEDIUM and above), adding `security-events: write`. Trivy runs from its official image pinned by digest (`aquasec/trivy:0.76.1`, released 2026-10-21) instead of `aquasecurity/trivy-action` (its tags were hijacked in an earlier supply-chain incident); the only action is `actions/checkout` pinned by commit.

## Probe P2 (local half)
Trivy 0.76.1 `--format github`: the lock copied as `requirements.txt` gives one manifest with 56 pip packages; `postgres:17.11-alpine3.24@sha256:...` (`--platform linux/arm64`) gives 45 `pkg:apk` packages and 4 `pkg:golang` (gosu). The submission rewrites `file.source_location` and sets `sha`, `ref`, `job.correlator`.
