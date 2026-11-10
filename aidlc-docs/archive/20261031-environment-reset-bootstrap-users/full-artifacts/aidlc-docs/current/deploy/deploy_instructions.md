# Deploy Instructions — Environment reset and bootstrap users

Target: a local `lakehouse-local` Docker Compose stack in a checkout of `opensource-lakehouse-infra-v2`. The development machine already runs this change; these steps are for any other checkout. All steps are manual and run from the repository root.

Choose one path:
- **Path A** rebuilds from nothing. It is recommended and is the path that was verified.
- **Path B** upgrades in place. It was not verified live.

## 1. Back up (both paths)
- **Action:** save anything you want to keep.
  - The Jenkins home, for example: `docker run --rm -v lakehouse-local_jenkins-home:/src:ro -v "$PWD/.runtime/backups/<date>":/dst postgres:17.11-alpine3.24 tar -C /src -czf /dst/jenkins-home.tar.gz .`
  - Bucket data and notebooks from Jupyter homes.
  - `.runtime/credentials/`, stored encrypted.
- **Prerequisites:** Docker running. Stop Jenkins first for a consistent copy.
- **Validation:** the archive exists and `tar -tzf` lists entries.
- **Failure handling:** do not continue to step 2A without a backup you trust. There is no rollback for the reset.

## 2A. Reset (Path A only)
- **Action:** `./scripts/lakehouse.sh reset --dry-run`, review the list, then `./scripts/lakehouse.sh reset`, and type `reset`.
- **Validation:** `Reset complete`. A second `--dry-run` lists nothing. Other projects' containers and volumes are not listed.
- **Failure handling:** fix the reported cause and rerun. Resources that are already gone are skipped.

## 3. Start and bootstrap (both paths)
- **Action:** `./scripts/bootstrap-default-product.sh`. It runs `lakehouse.sh start` first.
- **Validation:**
  - `Keycloak realm bootstrap verified (... writer-client=lakehouse-writer; ... groups=5; realm-admin-group=role-platform-admin; ...)`
  - `Bootstrap users match their defaults (...; users=5)`
  - `Default product bootstrap and smoke verification completed.`
- **Failure handling:** the scripts are idempotent, so fix the cause and rerun. A conflict message from the realm bootstrap means existing Keycloak objects differ from the contract. Review them before changing anything.

## 3b. Remove old writer identity (Path B only, manual)
- **Action:** in the `lakehouse` realm, delete the `write-service-account` client. In Polaris, remove the principal `service-account-write-service-account` and its principal-role assignments.
- **Prerequisites:** step 3 passed, and the Airflow broker runs the new image (step 4). Nothing else uses the old client.
- **Validation:** `scripts/verify-polaris-keycloak-auth.py` still passes.
- **Failure handling:** none needed. The old identity is unused, and leaving it in place is harmless.
- **Blocker:** no script exists for this step.

## 4. Airflow (optional)
- **Action:** `./scripts/lakehouse.sh start-airflow`.
- **Validation:** `Airflow is ready at http://127.0.0.1:8085; production and UAT Bundles are registered`. `.runtime/airflow-dag-bundles/` contains `lakehouse-main` and `lakehouse-uat`.
- **Failure handling:**
  - An `airflow-init` validator error means the image is out of date. Rerun the command, which rebuilds it.
  - In Path B, after the Airflow Bundles are confirmed, the old `../opensource-lakehouse/.runtime` folder is unused and can be removed.

## 5. Validate
- **Action:**
  - Run `python3 scripts/verify-rustfs-oidc.py`, `python3 scripts/verify-rustfs-sts.py`, `python3 scripts/verify-polaris-oidc-negative-cases.py`, `python3 scripts/verify-role-matrix.py`, and `python3 scripts/verify-jenkins-oidc.py`.
  - Sign in to JupyterHub as `joe-developer` and as `platform-admin`.
  - Sign in to <http://keycloak.localhost:8080/admin/lakehouse/console/> as `platform-admin`.
- **Validation:** all verifiers pass. After a reset, the Jenkins check "migrated workload CI job is missing" is expected.
- **Failure handling:** stop and investigate. To put the users back to their defaults, run `./scripts/bootstrap-users.sh`, then `python3 infra/polaris/reconcile-keycloak-groups.py`.

## 6. Restore the Jenkins CI job (optional, after a reset)
- **Action:**
  1. Stop Jenkins.
  2. Extract the job from the backup into the volume, for example `jobs/opensource-lakehouse-dp/` from `jenkins-home.tar.gz`.
  3. Start Jenkins again.
- **Blocker:** there is no scripted restore. Agree the procedure before running it.
