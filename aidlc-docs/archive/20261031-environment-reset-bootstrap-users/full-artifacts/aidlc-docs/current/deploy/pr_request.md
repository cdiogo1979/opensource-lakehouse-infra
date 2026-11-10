# PR Request — Environment reset, bootstrap users, and independent Airflow Bundles

_Proposed PR description. No pull request has been created. This workspace has no git metadata._

## Problem
The local platform had no supported way to start over. Removing state meant hand-picking Docker volumes and runtime files. Startup also had problems:
- It created one `platform-admin` user with a generated one-time password and no other people to test with.
- Airflow and Spark wrote as a client-credentials service account.
- Airflow Bundles were mounted from the sibling `opensource-lakehouse` repository, which tied the two repositories together.

## Solution
- **Full reset:** `scripts/lakehouse.sh reset` is backed by `scripts/reset-lakehouse.py`.
  - It finds only this platform's resources: containers by Compose project or runtime-role label, an exact list of volumes and networks, the Jupyter home volume prefix, and three generated `.runtime` directories.
  - It lists everything before deleting, and asks you to type `reset`. `--yes` skips the prompt, and `--dry-run` only lists.
  - A path guard refuses symlinks and anything outside those three directories. Images, other projects, and `.runtime/backups` are never touched.
- **Bootstrap users:**
  - Five users with the permanent password `ChangeM3!` are defined in a single file, `infra/keycloak/bootstrap-users.json`: `joe-developer`, `peter-analyst`, `maria-owner`, `srv-default-writer`, and `platform-admin`.
  - The realm bootstrap creates missing users only.
  - The separate `scripts/bootstrap-users.sh` resets the five users to their default password and single group. It leaves every other user alone, and runs as part of the product bootstrap.
- **`role-platform-admin`:**
  - It has owner rights in Polaris and RustFS, Admin in Airflow, and Administer in Jenkins.
  - Added at the user's request during Build and Test: realm-admin of the `lakehouse` realm in Keycloak (not `master`), and JupyterHub admission as a Hub admin.
- **Writer identity:**
  - `write-service-account` is replaced by the user `srv-default-writer` through the new confidential `lakehouse-writer` client (password grant, 1-hour tokens).
  - The users are the Airflow token broker, Spark bootstrap, and verifiers. Its password file is written from the JSON file.
- **Independent repositories:**
  - Airflow Bundles are cloned into `<infra-v2>/.runtime/airflow-dag-bundles`. `LAKEHOUSE_PROJECT_ROOT` is removed.
  - The Bundle validator checks the host path only when given `--host-paths`, which `lakehouse.sh` passes on the host.
- **README:** new "Start the platform" and "Reset the platform" sections, with the users table, Keycloak sign-in URLs, and backup advice.

## Main changes

| Area | Paths |
|---|---|
| Reset | `scripts/reset-lakehouse.py` (new), `scripts/lakehouse.sh` |
| Users and groups | `infra/keycloak/bootstrap-users.json` (new), `infra/keycloak/bootstrap-users.py` (new), `scripts/bootstrap-users.sh` (new), `infra/keycloak/bootstrap-realm.py`, `infra/keycloak/realm-contract.json`, `scripts/bootstrap-default-product.sh` |
| Platform-admin mappings | `infra/polaris/reconcile-keycloak-groups.py`, `infra/rustfs/bootstrap-policies.py`, `infra/airflow/airflow_sso_roles.py`, `infra/airflow/webserver_config.py`, `infra/jenkins/casc/jenkins.yaml`, `infra/jupyter/hub/lakehouse_policy.py`, `infra/jupyter/hub/jupyterhub_config.py` |
| Writer migration | `infra/airflow-token-broker/app.py`, `docker-compose.airflow.yml`, `infra/spark-bootstrap/create_smoke_tables.py`, `scripts/run-bootstrap-smoke-spark.sh`, `scripts/prepare-lakehouse-runtime.py`, `scripts/verify-polaris-keycloak-auth.py`, `scripts/verify-keycloak-outage.py`, `scripts/verify-polaris-oidc-negative-cases.py` |
| Bundles | `scripts/lakehouse.sh`, `scripts/provision-airflow-secrets.sh`, `infra/airflow/validate-bundle-config.py` |
| Docs | `README.md` |
| Tests | new: `tests/keycloak/test_bootstrap_users_contract.py`, `tests/operations/test_reset_lakehouse.py`, `tests/airflow/test_bundle_root_contract.py`; updated: RustFS policy, Jenkins CasC, Airflow SSO, JupyterHub config and policy, Unit 4 Hub journey contracts |

## Verification
Build and Test passed on 2026-10-31 against the live local stack. See `aidlc-docs/current/construction/build-and-test/build-and-test-summary.md`.
- **Contract tests:** 185 passed, 1 skipped, 2 failed. The 2 failures are the earlier Airflow developer-role drift, which is not part of this change. The JupyterHub broker tests pass (10) with `PYTHONPATH=infra/jupyter/hub`.
- **Live rebuild:** a real reset and a rebuild from nothing both passed, along with the product bootstrap and Spark smoke tables.
- **Users and verifiers:**
  - All five users log in with the default password.
  - The rerun of `bootstrap-users.sh` restored the defaults after deliberate changes.
  - RustFS OIDC and STS, Polaris negative cases, and the role matrix pass.
  - The Airflow broker issues a token as `srv-default-writer`.
  - platform-admin administers only the `lakehouse` realm.
  - The user confirmed JupyterHub sign-in in a browser.
- **Jenkins verifier:** 8 of 9 checks pass. The CI job is absent after a reset (see Risks).
- **Not run:** `scripts/verify-keycloak-outage.py`, because it stops Keycloak. Browser checks other than JupyterHub were not repeated for the new users.

## Deployment
The local environment already runs this change. Deploying it to another checkout or machine requires ordered operational steps; see [deploy_instructions.md](deploy_instructions.md).

## Risks and limitations
1. **The reset is irreversible.** It deletes realm, users, catalogs, bucket data, Jupyter homes, the Jenkins home and build history, Airflow metadata, and generated secrets. Back up first.
2. **The Jenkins CI job is lost on reset.** The job lives only in the Jenkins home. A pre-reset backup exists at `.runtime/backups/20261031-pre-reset/jenkins-home.tar.gz`. Follow-up: restore it, or define the job as code.
3. **The default password is documented.** `ChangeM3!` is local-development only, and the stack must not be exposed beyond loopback.
4. **platform-admin has full control of the `lakehouse` realm.** That includes changing its own rights and client secrets. `bootstrap-users.sh` restores only its group membership.
5. **The `lakehouse-writer` client accepts any realm user's password.** Tokens carry only that user's own roles, and the client secret is held by the broker and Spark runtime only.
6. **Upgrading without a reset leaves leftovers.** The old `write-service-account` client and its Polaris principal stay behind and must be removed by hand. See deploy step 3b.
7. **Out of scope:** stale `write-service-account` references remain in the deferred `infra/tpch-loader` and `infra/starrocks`.
8. **Unexplained container loss during testing.** Stopped `hive-dremio-rustfs-*` and `iceberg-poc-*` containers disappeared during the Build and Test window. Their volumes are intact. The reset did not remove them, and the cause is unknown.
