# Deployment Instructions: Jenkins onboarding and Keycloak SSO

> These instructions document the steps. They do not authorize or perform a deployment. Run everything from the repository root. All steps are manual operator actions; the scripts they call are automated.

**Target**: the local Docker Compose stack (project `lakehouse-local`), loopback only.

## Steps

### 1. Back up
- **Action**: back up `.runtime/credentials/`, and the legacy volume `iceberg-poc-jenkins-home` if it still exists.
- **Validation**: the backup is readable.
- **Failure handling**: do not continue without a backup. Step 7 is irreversible.

### 2. Stop the legacy Jenkins
- **Action**: stop `hive-dremio-rustfs-jenkins-1` if it is running.
- **Validation**: `docker inspect -f '{{.State.Running}}' hive-dremio-rustfs-jenkins-1` reports `false`.
- **Failure handling**: the migration refuses while the legacy container is running.

### 3. Start the stack (automated)
- **Execution**: `scripts/lakehouse.sh start`. In order, it:
  1. creates the Jenkins secrets
  2. runs the realm bootstrap, which adds the `jenkins` client
  3. builds the pinned image
  4. copies and verifies the legacy home once
  5. starts Jenkins and waits until it is healthy
- **Validation**:
  - the output ends with the Jenkins URL `http://127.0.0.1:8090`
  - `scripts/lakehouse.sh status` lists `jenkins healthy`
- **Failure handling**:
  - "not empty and has no origin marker": inspect `lakehouse-local_jenkins-home` before retrying.
  - Copy verification failure: remove the unmarked target volume after review, then retry.
  - Image build failure about the plugin set: check `plugins.txt` and network access to `updates.jenkins.io`.

### 4. Verify (read-only)
- **Execution**: `python3 scripts/verify-jenkins-oidc.py`
- **Validation**: 9 PASS lines.

### 5. Interactive check (manual)
- **Execution**: sign in at <http://127.0.0.1:8090> through Keycloak as product-group users.
- **Validation**: permissions match the README table; the break-glass login works.

### 6. CI check (manual)
- **Execution**: trigger `opensource-lakehouse-dp/opensource-lakehouse-ci` `main`.
- **Validation**: the build succeeds.
- **Known blocker**: the build currently fails on the workload regression in commit `00b6623` until that test is fixed in `opensource-lakehouse`.

### 7. Remove the legacy instance (gated, irreversible)
- **Prerequisites**: steps 4–5 passed, and the removal is approved.
- **Execution**: `scripts/lakehouse.sh remove-legacy-jenkins --confirm`
- **Validation**: the command reports that it removed `hive-dremio-rustfs-jenkins-1` and `iceberg-poc-jenkins-home`. `jenkins_home` remains.
- **Local stack**: this step was already executed on 2026-10-31 after approval.

## Fresh install (no legacy home)
`scripts/lakehouse.sh start` starts Jenkins with an empty home and prints a notice. Security comes from configuration as code. The workload job must then be restored from a backup of `lakehouse-local_jenkins-home` or recreated.

## Rollback
- **Before step 7**: stop Jenkins (`docker compose stop jenkins`) and remove `lakehouse-local_jenkins-home`. The legacy instance is untouched.
- **After step 7**: restore `lakehouse-local_jenkins-home` from backup.
- **Leftovers**: the Keycloak `jenkins` client, its mapper, and the secrets are inert without the Jenkins service. Removing them is a separate reviewed change.

## Inputs and blockers
- **Blocker for a green CI build**: the `opensource-lakehouse` test fix (outside this change).
- **Before shared or production use**: TLS, non-loopback hostnames, a least-privilege Keycloak bootstrap identity, and backups of the Jenkins home.
