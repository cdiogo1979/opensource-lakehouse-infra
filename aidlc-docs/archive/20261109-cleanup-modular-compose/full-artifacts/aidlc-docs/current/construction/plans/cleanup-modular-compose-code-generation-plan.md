# Code Generation Plan — cleanup-modular-compose

Single unit. Code lives at the workspace root. Traceability refers to FR-1..FR-6.

## Step 1 — Snapshot and remove unused files (FR-1, FR-2)
- [x] Snapshot everything listed below into `aidlc-docs/current/construction/cleanup-modular-compose/code/removed-files-snapshot/` and verify the copy (no git; the closure archive keeps it).
- [x] Remove:
  - `infra/tpch-generator/`, `infra/tpch-loader/`, `infra/identity-provisioner/`, `infra/bucket-init/`
  - `infra/polaris/reset-default-product-once.py`
  - `scripts/prepare-ranger-test-secrets.sh`
  - `docker-compose.deferred.yml`
  - `infra/jupyter/examples/`
  - `Jenkinsfile`
  - `scripts/migrate-jenkins-home.py`
  - tests that exist only for removed code, such as `tests/jenkins/test_migrate_home.py`
- [x] Remove `remove_legacy_jenkins` and its dispatch from `scripts/lakehouse.sh`, and the migration call from `start`.
- [x] Delete `__pycache__`, `.pytest_cache`, and `.hypothesis`. Add `.pytest_cache/` and `.hypothesis/` to `.gitignore`.

## Step 2 — Split and rename the Compose files (FR-4)
- [x] `compose.core.yml`: keycloak-db, keycloak, polaris-db, polaris-schema-init, polaris, polaris-group-reconciler, and rustfs; networks core, data-access, rustfs-identity; volumes keycloak-db-data, polaris-db-data, rustfs-data. The project name is `lakehouse-local`.
- [x] `compose.jupyter.yml`: jupyterhub, the network jupyter-user, and volume jupyterhub-state.
- [x] `compose.jenkins.yml`: jenkins and volume jenkins-home.
- [x] Rename `docker-compose.airflow.yml` to `compose.airflow.yml` and `docker-compose.starrocks.yml` to `compose.starrocks.yml`, updating their header comments.
- [x] Remove `docker-compose.yml`. Resource names stay the same.

## Step 3 — Module selection and references (FR-5)
- [x] `scripts/lakehouse.sh`:
  - read `JUPYTER_ENABLED`, `JENKINS_ENABLED`, and `STARROCKS_ENABLED` (environment or `.env`; default true)
  - build `COMPOSE` from core plus the enabled modules, and `AIRFLOW_COMPOSE` as that plus the Airflow file
  - gate the Jupyter and Jenkins start, status, and stop steps
  - keep the empty-array handling safe for bash 3.2, and update the usage line
- [x] Update every Compose file reference:
  - `scripts/verify/airflow-dags.sh`, `scripts/verify/jenkins-oidc.py`, `scripts/verify/rustfs-oidc.py`
  - `infra/starrocks/*` comments and `.env.example` (new flags)
  - the tests under `tests/{jenkins,jupyterhub,polaris,rustfs,starrocks,airflow,keycloak}`
- [x] Add a check that no file outside `aidlc-docs` still names `docker-compose*.yml` or a removed path.

## Step 4 — Repair the Spark smoke checks (FR-3)
- [x] Diagnose `scripts/bootstrap/smoke-spark.sh` with `local/lakehouse-spark-runtime:3.5.5_1.10.2`, then fix the script, its mounts, and any configuration so it creates and reads the three smoke tables.
- [x] Apply the same fix to the Spark part of `scripts/verify/role-matrix.py`.

## Step 5 — README, tests, summary (FR-6)
- [x] README:
  - a "Compose modules" section: files, flags, and manual `docker compose -f ...` usage
  - update start, stop, and status
  - remove the one-time reset, Jenkins migration, legacy removal, and deferred-inventory text
- [x] Contract tests:
  - module files and resource names unchanged
  - flag handling in `lakehouse.sh`
  - removed paths absent and unreferenced
  - smoke image repointed
- [x] Run the full suite and `docker compose config` for the module combinations.
- [x] Write `aidlc-docs/current/construction/cleanup-modular-compose/code/code-summary.md`.

## Additional changes found during generation (DOC-02)
- [x] `scripts/bootstrap-default-product.sh` and `scripts/verify/keycloak-outage.py` ran a bare `docker compose`, relying on the removed default file. They now pass `-f compose.core.yml`, and a contract test guards every Compose invocation.
- [x] The Spark runtime image was missing (pruned outside this session); it was rebuilt from `infra/spark-runtime/Dockerfile`.
- [x] FR-7 (change request): moved 22 scripts into `scripts/{setup,bootstrap,operations,clients,verify}/` and kept the two entry points and `aidlc_intent.py` at the top.
  - Root paths fixed for the new depth (`parents[2]`, `../..`).
  - Rewrote references in 23 files, plus `./scripts/` forms, bare names, and one path-built test loader.
  - README "Scripts" section added.
  - Verified: suite at baseline, and the moved scripts run from another directory against the live stack.
- [x] FR-6a (change request): rewrote `README.md` around a Contents index.
  - Removed old-stack and history references, and duplicated provider text.
  - Added an Airflow section and a per-group access table.
  - Fixed the JupyterHub group list and the RustFS platform-admin row.
  - Checked the anchors and old-stack terms, and updated the one README-dependent test.
- [x] Build and Test fix: `BUILDX_NO_DEFAULT_ATTESTATIONS=1` in `lakehouse.sh` and `bootstrap-default-product.sh`. Repeat starts were recreating containers, because the containerd image store gave each cached build a new image ID through a timestamped attestation.
- [x] Build and Test fix: `COMPOSE_IGNORE_ORPHANS=true` in both entry scripts, plus a README warning against `--remove-orphans`.
- [x] Contract tests for both fixes.
- [x] Documentation (user finding during Build and Test): with DBeaver's StarRocks connection type, only `idTokenFile` is needed. The README now makes that the main DBeaver path, and keeps the three Connector/J properties and the truststore for other JDBC clients. The README test was updated.
