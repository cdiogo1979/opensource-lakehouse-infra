# Code Summary — Cleanup and Modular Compose

Intent `20261109-cleanup-modular-compose`, unit `cleanup-modular-compose`.

## Requirements traceability
| Requirement | Change |
|---|---|
| FR-1 Remove unused files | Removed `infra/{tpch-generator,tpch-loader,identity-provisioner,bucket-init}`, `infra/polaris/reset-default-product-once.py`, `scripts/prepare-ranger-test-secrets.sh`, `docker-compose.deferred.yml`, `infra/jupyter/examples`, and the root `Jenkinsfile`. That is 18 files, snapshotted and verified identical in `code/removed-files-snapshot/` first. Caches were cleared, and `.pytest_cache/` and `.hypothesis/` added to `.gitignore`. |
| FR-2 Jenkins migration | Removed `scripts/migrate-jenkins-home.py` (with `tests/jenkins/test_migrate_home.py`), the `remove-legacy-jenkins` command, and its function. `scripts/verify/jenkins-oidc.py` now checks the realm, the matrix, and the workload CI job, with no origin marker. |
| FR-3 Spark smoke | `scripts/bootstrap/smoke-spark.sh` and `scripts/verify/role-matrix.py` use `local/lakehouse-spark-runtime:3.5.5_1.10.2`. Both Spark jobs set `rest.auth.type=oauth2`, because the image's `spark-defaults.conf` selects the broker AuthManager. |
| FR-4 Modular Compose | `docker-compose.yml` is split into `compose.core.yml`, `compose.jupyter.yml`, and `compose.jenkins.yml`. The Airflow and StarRocks files are renamed to `compose.airflow.yml` and `compose.starrocks.yml`. The rendered config of core, jupyter, and jenkins is identical to the old file (services, networks, volumes, secrets, name), and resource names are unchanged. |
| FR-5 Module selection | `scripts/lakehouse.sh` reads `JUPYTER_ENABLED`, `JENKINS_ENABLED`, and `STARROCKS_ENABLED` (environment or `.env`; case-insensitive; default true). It builds `COMPOSE` from core plus the enabled modules, and `AIRFLOW_COMPOSE` from that plus Airflow, and gates the start, status, and stop steps. It is safe for bash 3.2. Compose references are updated in `scripts/verify/jenkins-oidc.py`, `scripts/verify/rustfs-oidc.py`, `scripts/verify/airflow-dags.sh`, `scripts/verify/keycloak-outage.py`, and `bootstrap-default-product.sh`; the last two would have broken without the old default file. `.env.example` gains the flags. |
| FR-6 README | New "Compose modules" section (files, flags, and manual `docker compose -f` usage). The one-time reset, Jenkins migration, legacy removal, and deferred-inventory text are replaced by "Product bootstrap details" and "Retired components". Every Compose example names its files. |

## Tests
- New `tests/operations/test_compose_modules_contract.py`:
  - module files and services per module
  - the project name only in core
  - resource names unchanged
  - retired files absent and unreferenced
  - every Compose invocation names its files
  - flag-built file list
  - five module combinations rendered with `docker compose config`
  - the Spark runtime image and auth
- Updated: Jenkins, JupyterHub, Polaris, RustFS, StarRocks, Airflow, and Keycloak contract tests.
- Results:
  - Full suite: 215 passed, 1 skipped, plus 2 earlier Airflow drift failures. Broker tests: 10 passed.
  - Static checks pass.
  - The Spark smoke job and the full role-matrix verifier pass live on the current image.

## Environment note
Unused local images were pruned outside this session: only images in use by containers remained. The Spark runtime image was rebuilt from its Dockerfile, as `lakehouse.sh start` does.

## Change request: script layout (FR-7)
- **Layout**: `scripts/` keeps `lakehouse.sh`, `bootstrap-default-product.sh`, and `aidlc_intent.py` at the top. The other scripts are in `setup/` (8), `bootstrap/` (3), `operations/` (1), `clients/` (2), and `verify/` (8).
- **Renames**:
  - `prepare-lakehouse-runtime.py` became `setup/prepare-runtime.py`
  - `prepare-airflow-token-broker-certificates.py` became `setup/prepare-airflow-broker-certificates.py`
  - `run-bootstrap-smoke-spark.sh` became `bootstrap/smoke-spark.sh`
  - `verify-*` became `verify/*`, and `verify-airflow-environment-dags.sh` became `verify/airflow-dags.sh`
- **Verification**: moved scripts compute the repository root one level deeper. Tests: 215 passed, 1 skipped, plus 2 earlier Airflow drift failures. Live: setup, certificate, `bootstrap-users`, reset dry run, `status`, the RustFS verifier, and the StarRocks login all ran correctly, including from another working directory.

## Change request: README rewrite (FR-6a)
`README.md` was restructured: a Contents index at the top, then Components, Quick start, Compose modules, Users and sign-in, Data layout, Services (Keycloak, Polaris, RustFS, JupyterHub, Airflow, StarRocks, Jenkins), Operations, Scripts, and Known limitations.
- **Removed**: old-stack and project-history text.
- **Facts checked against the code**:
  - the bootstrap step order
  - the Airflow role mapping
  - the JupyterHub admitted groups
- **Checks**: 21 internal links all resolve, and no old-stack term remains. Tests: 215 passed, 1 skipped, plus the 2 earlier Airflow drift failures.

## Build and Test changes
- **Reproducible builds**: `BUILDX_NO_DEFAULT_ATTESTATIONS=1` stops repeat starts from recreating containers.
- **Orphans**: `COMPOSE_IGNORE_ORPHANS=true` hides misleading orphan warnings.
- Both are set in `scripts/lakehouse.sh` and `scripts/bootstrap-default-product.sh`, documented in the README, and covered by contract tests. Final suite: 217 passed, 1 skipped, plus 2 earlier Airflow failures.
