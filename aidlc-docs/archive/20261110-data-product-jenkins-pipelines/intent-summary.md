# Intent Summary: Data Product Jenkins Pipelines

## Intent
Data Product Jenkins Pipelines (`20261110-data-product-jenkins-pipelines`)

## Objective
Creating or applying a data product also sets up Jenkins: a folder per product whose owner group is its admin, and, with a repo, the multibranch pipelines <name>_ci (prod and UAT branches when they change) and <name>_cd (branches that are the source of an open pull request) on the repository's Jenkinsfile.

## Date
2026-11-10

## Scope
Included: job-dsl pin and version-checked plugin parity; projectMatrix with per-folder rights (owner folder admin, apps.jenkins roles per folder, Overall/Read globally); render_jenkins.py writing CasC, a Job DSL script and the desired state; the init.groovy.d hook applying the DSL and deleting managed leftovers; product model rules (no apps.jenkins owner or Overall/*, github_repository); create/remove plan and restart; verifier, realm contract, README, tests. Excluded: webhooks, GitHub tokens, fork pull requests, build agents or Docker pipelines, restoring the old job's history, Airflow changes.

## Units / workstreams
jenkins-pipelines

## Major requirements
- Every product gets a Jenkins folder <name>; with a repo, <name>_ci (prod_branch and uat_branch, scan 5 min) and <name>_cd (same-repository PR source branches, github.com only, scan 30 min), both on the repository's Jenkinsfile.
- The product owner is admin of the folder only; developers and analysts get their apps.jenkins rights on their folder only; product groups get Overall/Read globally; only platform admin and break-glass administer Jenkins.
- Folders and jobs are configuration as code, recreated at every start; removing a product deletes its folder; removing its repo deletes the two jobs and keeps the folder.

## Architecture and design decisions
- Q1 Job DSL (job-dsl 3732.v9a_c49a_61a_313) rendered from the product files; Q2 owner folder admin only (22 folder permissions); Q3 per-folder developer/analyst rights; Q4 unauthenticated GitHub; Q5 no fork PRs; Q6 _ci 5 min, _cd 30 min; Q7 empty folder without repo; Q8 removal deletes folder and history; Q9 old opensource-lakehouse-dp job not restored; Q10 PBT partial.
- Owner rights are fixed by rule: apps.jenkins refuses owner and any Overall/* permission.
- Deletion by an init.groovy.d hook that touches only top-level folders carrying the marker and their <name>_ci/<name>_cd jobs, driven by a rendered desired-state JSON; it deletes nothing on an invalid state or a failed apply.

## Implementation decisions
- render_jenkins.py writes jenkins-casc.yaml, jenkins-jobs.groovy and jenkins-products.json; exit 3 if any changed; --check prints the plan.
- Every product value in the DSL is a single-quoted Groovy literal (groovy_string); github_repository() parses GitHub URLs.
- The Dockerfile parity check compares name:version from plugin manifests.
- The verifier checks the owner's full admin set by Jenkins permission class.

## Deviations
- Build and Test found that a Job DSL script in CasC runs before Jenkins loads its jobs, so new folders were lost until the next restart; the DSL moved to its own file applied by the init hook after job loading (and the ^${ CasC escaping became unnecessary).
- During testing an unchanged re-apply of the test product without --no-restart recreated Airflow (and the removal again); no DAG run was active; the two test DAG records were removed by Airflow itself.
- Canonical reconciliation: application-design.md still said the Airflow broker serves only srv-default-writer (stale since 20261109-data-product-airflow-bundles); removed.

## Verification
See construction/build-and-test/build-and-test-summary.md. Suite 422 passed, 2 skipped (P1-P5; three mutations caught). Image rebuilt with the name:version plugin check. Live: jenkins-oidc.py 10/10; default_ci main #1 and uat #1 SUCCESS; default_cd scanned unauthenticated (0 PRs); ACL per group with cross-product isolation; jptest created, repo removed, removed, re-created from scratch (folder in memory after one start, builds SUCCESS), re-applied unchanged (no restart), removal with automatic restart. Not run: a real PR build, reset, interactive per-role logins.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/jenkins-ci-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md

## Superseded decisions
- Jenkins rights platform-wide (globalMatrix; owner Overall/Administer) replaced by projectMatrix with per-folder rights (Data Product and User Scripts intent).
- Jobs not configuration as code, and the open follow-up to restore opensource-lakehouse-dp/opensource-lakehouse-ci, replaced by product folders and jobs as code (default/default_ci, default/default_cd).
- Plugin parity by name only replaced by name:version.

## Archived artifacts
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/aidlc-docs/current/compaction/20261110-data-product-jenkins-pipelines/manifest.json
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/jenkins-ci-access.md
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/infra/jenkins/plugins.txt
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/infra/jenkins/Dockerfile
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/infra/jenkins/casc/jenkins.yaml
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/infra/jenkins/init.groovy.d/reconcile-data-products.groovy
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/compose.jenkins.yml
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/infra/products/data_products.py
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/infra/products/render_jenkins.py
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/infra/products/template.yaml
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/data-products/default.yaml
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/infra/keycloak/realm-contract.json
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/scripts/operations/lib/data-products.sh
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/scripts/operations/create-data-product.sh
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/scripts/operations/remove-data-product.sh
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/scripts/setup/prepare-runtime.py
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/scripts/verify/jenkins-oidc.py
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/README.md
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/tests/jenkins/test_product_pipelines.py
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/tests/products/product_strategies.py
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/tests/jenkins/test_casc_contract.py
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/tests/jenkins/test_plugins_contract.py
- aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/tests/products/test_data_products.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261110-data-product-jenkins-pipelines/full-artifacts/`
