# System Architecture — Environment State and Identity Bootstrap

## Persistent state (what a full reset must cover)
| Kind | Items (local, `lakehouse-local` project) |
|---|---|
| Core volumes | `lakehouse-local_keycloak-db-data`, `_polaris-db-data`, `_rustfs-data` (buckets and IAM policies), `_jupyterhub-state`, `_jenkins-home` |
| Airflow volume | `lakehouse-local_airflow-postgres-data` (`docker-compose.airflow.yml`) |
| Per-user volumes | `lakehouse-jupyter-home-<hash>` (JupyterHub single-user homes) |
| Ephemeral containers | Jupyter user servers (label `lakehouse-local.role=jupyter-user-server`), Airflow Spark runs (label `lakehouse-local.role=airflow-spark-run`) |
| Networks | `lakehouse-local_core`, `_jupyter-user`, `_data-access`, `_rustfs-identity`, `_airflow-internal`, `_airflow-spark` |
| Protected runtime files | `.runtime/credentials/*` (about 33 files: Keycloak, Polaris, RustFS, JupyterHub, Airflow, and Jenkins secrets, certificates, and configuration), `.runtime/container-mounts/*` |
| Other runtime | `.runtime/airflow-dag-bundles/`; the Airflow Bundle checkouts default to `../opensource-lakehouse/.runtime/airflow-dag-bundles` (outside this repository) |
| Images | `local/lakehouse-*` (Jupyter, Spark runtime, Airflow, broker, Jenkins, reconciler) |
| Not part of v2 | `iceberg-poc-*`, `airflow-spark-jenkins_*`, `jupyter-platform_*`, `openmetadata-docker_*`, `jenkins_home` volumes; `.runtime/aidlc-test-venv` |

Note: deleting the database and RustFS volumes removes buckets, catalogs, realm, groups, users, and policies in one step. API-level deletion is not needed for a full reset.

## Existing reset capability
`infra/polaris/reset-default-product-once.py` is a guarded, one-time reset that empties only the default-product buckets and catalogs. It requires `boto3`. It is not a full environment reset.

## Startup sequence today
1. `scripts/lakehouse.sh start`:
   1. prepare runtime credentials
   2. broker certificates
   3. image builds
   4. DBs and RustFS
   5. Polaris schema
   6. Keycloak and Polaris
   7. `bootstrap-realm.py`
   8. JupyterHub
   9. Jenkins (build, migrate home, start)
2. `scripts/bootstrap-default-product.sh` (it calls `start` first):
   1. realm
   2. Polaris realm
   3. buckets, then RustFS policies
   4. catalogs and authorization
   5. group reconciliation and the scheduled reconciler
   6. writer verification
   7. Spark smoke
3. `scripts/lakehouse.sh start-airflow`: optional and separate.

## Identity bootstrap today (`infra/keycloak/bootstrap-realm.py`)
- **Groups**: `role-default-{developer,analyst,owner,writer}` only. `role-platform-admin` does not exist.
- **platform-admin**: created with a random password from `.runtime/credentials/platform-admin-password`, marked **temporary** (required action `UPDATE_PASSWORD`), and placed in `role-default-owner`.
- **Writer**: `role-default-writer` membership comes from the `write-service-account` client's service-account user. A human-style user `srv-default-writer` does not exist.
- **Live realm now**: users `joe-developer` (developer, created manually) and `platform-admin` (owner).

## Group-to-service mapping today (no `role-platform-admin` anywhere)
| Service | Mapping |
|---|---|
| Polaris | product roles from `resource_access.polaris.roles`; the reconciler handles the 4 `role-default-*` groups |
| JupyterHub | developer and analyst admitted |
| Airflow | owner → Admin, developer → User (code drift), analyst → User, writer → Viewer |
| RustFS | group-named policies for the 4 groups |
| Jenkins | owner Administer, developer build, analyst read |
