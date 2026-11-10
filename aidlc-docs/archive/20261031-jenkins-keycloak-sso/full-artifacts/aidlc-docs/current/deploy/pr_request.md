# Proposed PR: Onboard Jenkins into the v2 stack with Keycloak SSO

> Proposed PR description only. No pull request has been created. This workspace has no Git metadata.

## Problem
Jenkins, the CI for the `opensource-lakehouse` workload repository, was deferred during the v2 rebuild. It ran only as a hand-configured legacy container from the sibling `hive-dremio-rustfs` stack. That container:
- had 102 manually installed plugins
- had a single shared local admin, and any logged-in user could do anything
- was published on port 8098 on all network interfaces
- had the Docker socket mounted

## Solution
Bring Jenkins into the v2 Compose stack by migrating the legacy home, pin it, and make Keycloak the sign-in:
- **Pinned image**: Jenkins 2.580.1 with an exact 104-plugin set, the legacy versions plus `oic-auth 4.731.v4932b_506e767` and `nimbus-jose-jwt-api`. The build fails if the installed set differs, and the image overrides the home's plugins at start.
- **Security as code**: configuration as code defines the OIDC realm, PKCE, group permissions, break-glass escape hatch, executors, and root URL, and is reapplied at every start.
  - Browser redirects use `keycloak.localhost`; back-channel calls use `keycloak:8080`.
  - Secrets are read from mounted files.
- **Permissions**: owner gets Administer. Developer can read, build, cancel, and view workspaces. Analyst is read-only. The writer group, users without a group, and anonymous users get nothing.
- **Keycloak client**: a confidential `jenkins` client with exact callbacks and post-logout URIs for both loopback hosts, and a `groups` claim in the ID token. It reuses the shared loopback-URI and port helpers now shared with RustFS.
- **Migration**: a one-time verified copy of the legacy home keeps the job and its history. A guarded command removes the legacy container and volume only after verification.
- **Exposure**: Jenkins runs on `127.0.0.1:8090` without the Docker socket and starts with the core `scripts/lakehouse.sh start`.

## Main changes
- **New**:
  - `infra/jenkins/plugins.txt`, `infra/jenkins/casc/jenkins.yaml`
  - `scripts/migrate-jenkins-home.py`, `scripts/verify-jenkins-oidc.py`
  - `tests/jenkins/` (4 files), `tests/keycloak/test_jenkins_client_contract.py`
- **Modified**:
  - `infra/jenkins/Dockerfile`
  - `infra/keycloak/bootstrap-realm.py`, `realm-contract.json`
  - `scripts/prepare-lakehouse-runtime.py`
  - `docker-compose.yml` (service and `lakehouse-local_jenkins-home` volume), `docker-compose.deferred.yml`, `.env.example`
  - `scripts/lakehouse.sh` (start, status, stop, `remove-legacy-jenkins --confirm`)
  - `README.md`

## Verification
Build and test ran on the local Compose stack on 2026-10-31. Passed:
- `verify-jenkins-oidc.py` 9/9, also after a restart
- idempotent reruns
- a headless SSO and permission run with temporary users (deleted afterwards), covering every role, refusal of users without a group, the escape hatch, and logout
- the plugin set equals `plugins.txt`
- the migration was verified
- RustFS, Airflow, and JupyterHub unaffected
- an interactive login confirmed by the user
- tests: Jenkins, Keycloak, and RustFS suites 90 passed; the full suite 174 passed, 1 skipped, and 2 pre-existing Airflow failures

**Verification waiver (user-accepted, not a pass)**: no successful workload CI build was achieved. `main` #11 and `uat` #4 ran the full pipeline on v2: checkout, venv, compile, lint, flake8, and bandit passed. Both failed on one `opensource-lakehouse` unit test, because commit `00b6623` ("rename dag") renamed the DAG without updating `test_dag_factory_reuses_spark_container_for_bundle_workloads`.

## Deployment
Ordered steps are required; see [`deploy_instructions.md`](deploy_instructions.md). On the local stack they were applied during Build and Test, including the approved legacy removal.

## Risks and limitations
- **Workload regression**: fix the test in `opensource-lakehouse` and push it; Jenkins rebuilds on its next scan.
- **Hand-made migrated state**: jobs and build history came from the legacy home and are not defined as code. Configuration as code overwrites UI changes to security and core settings on restart.
- **No Docker in pipelines**: pipelines that need Docker would fail. The current `Jenkinsfile` does not.
- **Startup cost**: core start now builds and starts Jenkins.
- **Legacy removal is irreversible**: the legacy home survives only as the v2 copy, so back up `lakehouse-local_jenkins-home`.
- **Bootstrap admin identity**: the Keycloak bootstrap still uses the local bootstrap admin.
- **Not production-ready**: this is a local single-node, loopback-only setup.
- **Unrelated pre-existing issues**: the Airflow developer role-mapping test drift, and the CI collection gap for the JupyterHub broker test.
