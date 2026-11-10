# PR Request — Data product Jenkins pipelines

_Proposed PR description. No pull request has been created, because this workspace has no git metadata. No change to the workload repository is needed: both jobs use its existing `Jenkinsfile`._

## Problem
- **No jobs**: Jenkins had no jobs since the 2026-10-31 reset, because jobs weren't configuration as code.
- **Platform-wide rights**: every product's owners were Jenkins administrators, and every product's developers could build every job.

## Solution
- **A folder per data product**, named `<name>`. With a `repo` block, it holds two multibranch pipelines on the repository's `Jenkinsfile`:
  - `<name>_ci`: plain Git, anonymous. Builds `prod_branch` and `uat_branch`, and scans every 5 minutes.
  - `<name>_cd`: GitHub Branch Source, anonymous. Builds only same-repository branches that are the source of an open PR (no forks), and scans every 30 minutes, which keeps unauthenticated GitHub use at about 5 products. A repository not on github.com gets only `_ci`.
- **Per-folder rights**:
  - The authorization strategy is now `projectMatrix`.
  - The owner group always holds the 22 folder permissions (jobs, runs, views, SCM tag, folder credentials).
  - `apps.jenkins` grants developers, analysts and writers rights on their own folder only; it now refuses `owner` and `Overall/*`.
  - Product groups get `Overall/Read` globally.
  - Only `role-platform-admin` and break-glass administer Jenkins.
- **Folders and jobs as code**:
  - `render_jenkins.py` writes the CasC file (security only), a Job DSL script and a desired-state JSON.
  - At every start, an `init.groovy.d` hook applies the script after the jobs load. Running the DSL from CasC lost new folders, which was found in testing.
  - The hook then deletes only marked product folders, and their `_ci` and `_cd` jobs, that left the state. It deletes nothing if the apply fails or the state is missing.
  - The jobs survive a `reset`.
- **Apply flow**: unchanged. Create and remove render the files and restart Jenkins only on change. The dry run prints the folder and job plan.
- **Hardening**: `job-dsl` is pinned, and the image check now compares plugin versions, not only names. Every product value in the DSL is a single-quoted Groovy literal (no interpolation).
- **Decisions** (requirements Q1 to Q10): Job DSL; owner is folder admin only; developer and analyst rights per folder; no GitHub token; no fork PRs; `_ci` scans every 5 minutes and `_cd` every 30; a product without `repo` gets an empty folder; removal deletes the folder and history, and removing only `repo` deletes the two jobs; the old CI job is not restored; partial property-based testing.

## Main changes
| Area | Paths |
|---|---|
| Jenkins | `infra/jenkins/plugins.txt`, `infra/jenkins/Dockerfile`, `infra/jenkins/casc/jenkins.yaml`, `infra/jenkins/init.groovy.d/reconcile-data-products.groovy` (new), `compose.jenkins.yml` |
| Product model and renderer | `infra/products/data_products.py`, `infra/products/render_jenkins.py`, `infra/products/template.yaml`, `data-products/default.yaml`, `infra/keycloak/realm-contract.json` |
| Scripts | `scripts/operations/lib/data-products.sh`, `scripts/operations/{create,remove}-data-product.sh`, `scripts/setup/prepare-runtime.py`, `scripts/verify/jenkins-oidc.py` |
| Docs and tests | `README.md`; `tests/jenkins/test_product_pipelines.py` (new), `tests/products/product_strategies.py`, updated `tests/jenkins/test_{casc,plugins}_contract.py` and `tests/products/test_data_products.py` |

## Verification
- **Suite**: `python3 -m pytest -q tests`: 422 passed, 2 skipped (Hypothesis P1 to P5 included). Three deliberate mutations were caught.
- **Live**:
  - the verifier passes 10/10;
  - `default_ci` built `main` and `uat` successfully, and `default_cd` scanned unauthenticated;
  - the ACL holds for each group, including cross-product isolation;
  - test product `jptest`: created, `repo` removed (jobs deleted, folder kept), removed (folder deleted), re-created from scratch (in memory after one start, both branches built), re-applied unchanged (no restart).
- **Not run**: `reset`, a real PR build, interactive per-role logins.

## Deployment
Required: see [deploy_instructions.md](deploy_instructions.md). Steps 1 to 3 are done on this local stack.

## Risks and limitations
- **Owners lose Jenkins-wide administration**: an intended change of rights.
- **Scans, not webhooks**: up to 5 minutes before a commit builds, and up to 30 for PR branches.
- **GitHub API limit**: unauthenticated, 60 requests per hour for the machine. Many GitHub products will exhaust it, and scans then wait.
- **Lost UI edits**: changes made in the UI to managed folders and jobs are overwritten at every start.
- **History deletion**: removing a product or its `repo` deletes that history, and a branch leaving the filter or a closed PR prunes its branch job and history.
- **No isolation for builds**: PR branches of the product's own repository run on the built-in node.
