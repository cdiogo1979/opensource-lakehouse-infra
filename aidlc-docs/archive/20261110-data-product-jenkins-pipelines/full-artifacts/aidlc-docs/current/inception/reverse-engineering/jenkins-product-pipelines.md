# Focused Reverse Engineering — Jenkins Jobs for Data Products

Intent `20261110-data-product-jenkins-pipelines`. Scope: how Jenkins is configured, how its permissions come from the data product files, what the old workload CI job was, and what a per-product folder with two multibranch pipelines needs. Captured 2026-11-10 against the running platform.

## Current state

| Area | Today | Source |
|---|---|---|
| Version | Jenkins 2.580.1, built-in node, 2 executors, no Docker socket | `infra/jenkins/Dockerfile`, `casc/jenkins.yaml` |
| Plugins | 104 exact versions. Present: `cloudbees-folder`, `workflow-multibranch`, `branch-api`, `git`, `github-branch-source`, `matrix-auth 3.3`, `configuration-as-code`. **Absent: `job-dsl`.** | `infra/jenkins/plugins.txt` |
| Jobs | **None.** The 2026-10-31 reset deleted the home; jobs are not configuration as code. | live home, `jenkins-ci-access.md` |
| Authorization | `globalMatrix`: static `role-platform-admin` and `jenkins-break-glass` entries, plus one entry per product role from `apps.jenkins`. **Platform-wide only**: `globalMatrix` ignores folder permissions. | `casc/jenkins.yaml`, `infra/products/render_jenkins.py` |
| Product owner today | `Overall/Administer` on the whole Jenkins (template default) | `data-products/default.yaml`, `infra/products/template.yaml` |
| Apply flow | `create-data-product.sh` renders the CasC file (`apply_jenkins`) and restarts Jenkins when it changed; `remove-data-product.sh` renders with `--exclude`. `prepare-runtime.py` renders on every `start`. | `scripts/operations/lib/data-products.sh` |
| Repository | `repo` block: `url` (https, no credentials), `prod_branch`, `uat_branch`; optional. | `infra/products/data_products.py` (`_repo`) |

## The old workload CI job (backup of 2026-10-31)
- **Layout**: folder `opensource-lakehouse-dp` holding the multibranch job `opensource-lakehouse-ci`.
- **Source**: plain Git (`GitSCMSource`), `https://github.com/cdiogo1979/opensource-lakehouse/`, anonymous. It discovered every branch.
- **Triggers**: none, so it scanned only when someone started a scan. Dead branches were pruned.
- **Pipeline**: `Jenkinsfile` at the root.
- **Folder permissions**: none.

## The workload `Jenkinsfile` (`cdiogo1979/opensource-lakehouse`, `515e403`)
`agent any`; venv and `pip install -r requirements-dev.txt` (from PyPI), then compile, lint, flake8 and bandit in parallel, then pytest. It doesn't deploy anything and doesn't check which branch or job type it runs in, so the `_ci` and `_cd` jobs would run identical stages.

## What the request needs, and the gaps

1. **Jobs as code.** Jobs are not code today, and a reset deletes them. There are two ways to create them:
   - **Job DSL in CasC**: add the `job-dsl` plugin (it resolves cleanly against 2.580.1, and all its dependencies are already pinned) and have `render_jenkins.py` emit a `jobs:` section. Jenkins recreates the jobs at every start, including after a reset. CasC doesn't delete jobs that leave the script, so removal needs one explicit delete.
   - **REST API from the operator scripts** (`createItem` with `config.xml`): no new plugin, but it needs a login (the break-glass account), only works while Jenkins runs, and a reset loses the jobs.
2. **Owner as admin of the folder only.** That means switching `globalMatrix` to `projectMatrix` (supported by the installed `matrix-auth 3.3`) and giving each product folder an authorization property for the owner group. With that, the owner's global `Overall/Administer` from `apps.jenkins` would have to go. Otherwise the folder scoping means nothing, because global Administer overrides every folder.
3. **`_ci`: builds the prod and UAT branches when they change.** A plain Git source with a branch filter for exactly `prod_branch` and `uat_branch`. Jenkins is loopback-only and gets no webhooks, so "when they change" means a periodic scan. Airflow refreshes its bundles every 300 s; the same 5-minute interval would match.
4. **`_cd`: builds any branch that is the source of a pull request.** Only the GitHub Branch Source can tell which branches have PRs, through the GitHub API. Its branch discovery mode "only branches that are also filed as PRs" does exactly this.
   - **GitHub only**: a non-GitHub `repo.url` can't get a `_cd` job.
   - **Rate limit**: the anonymous API allows **60 requests per hour per IP**, shared with everything else on this host. Every scan costs several requests, so two or more products scanning every 5 minutes would hit the limit. A GitHub token credential raises the limit to 5000 per hour, but the `repo` block is credential-free by design.
   - **Fork PRs**: PRs from forks live in other repositories, so "branch that is the source of a PR" covers same-repository PRs only, unless fork PRs are also discovered as PR heads.
5. **Naming.** Folder `<name>`, jobs `<name>_ci` and `<name>_cd`. Product names match `[a-z][a-z0-9]{1,19}`, so they are safe item names and can't clash with each other.
6. **Products without `repo`.** Today `repo` is optional. Such a product has no repository to build, so the open choices are no folder at all, or an empty folder.
7. **Removal.** Deleting the folder deletes its build history. `remove-data-product.sh` already backs up the product file first, but not Jenkins history.
8. **Developers and analysts.** Their `apps.jenkins` rights (`Job/Build`, and so on) are platform-wide today. With folders, they could be scoped to their own product's folder too.

## Tests in place
- `tests/jenkins/test_compose_jenkins_contract.py` and `tests/jenkins/test_jenkins_client_contract.py`
- The product-model tests in `tests/products/` cover `apps.jenkins` and `repo` validation.
- `scripts/verify/jenkins-oidc.py` checks the OIDC wiring and still expects the old `opensource-lakehouse-dp/opensource-lakehouse-ci` job.
