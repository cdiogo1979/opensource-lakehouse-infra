# PR Request — Cleanup, modular Compose, and script layout

_Proposed PR description. No pull request has been created; this workspace has no git metadata._

## Problem
- **Retired code**: the repository still carried files from retired stacks and finished one-time tasks: the TPC-H generator and loader, the FreeIPA identity provisioner, the one-time catalog reset, the Ranger secrets script, the Jenkins home migration, the deferred-services inventory, and an unused root `Jenkinsfile`.
- **One Compose file**: core services, JupyterHub, and Jenkins all lived in a single `docker-compose.yml`.
- **Scripts**: `scripts/` was a flat list of 25 files.
- **README**: it mixed current instructions with project history.
- **Spark smoke step**: it depended on a legacy image that no longer exists, so the product bootstrap stopped halfway.

## Solution
- **Cleanup**: removed 18 unused files after snapshotting them for the intent archive, and removed the Jenkins migration and the `remove-legacy-jenkins` command. Caches are git-ignored.
- **Modular Compose**:

  | File | Contents |
  |---|---|
  | `compose.core.yml` | Keycloak, Polaris, RustFS |
  | `compose.jupyter.yml` | JupyterHub |
  | `compose.jenkins.yml` | Jenkins |
  | `compose.airflow.yml` | Airflow (renamed) |
  | `compose.starrocks.yml` | StarRocks (renamed) |

  The project and resource names are unchanged, and the rendered configuration of core, Jupyter, and Jenkins is identical to the old file.
- **Module flags**: `JUPYTER_ENABLED`, `JENKINS_ENABLED`, and `STARROCKS_ENABLED` (default true) select the optional modules. `lakehouse.sh` builds the Compose file list in one place.
- **Scripts by purpose**: the entry points `lakehouse.sh` and `bootstrap-default-product.sh` stay at the top of `scripts/`. The rest are grouped in `setup/`, `bootstrap/`, `operations/`, `clients/`, and `verify/`.
- **Spark smoke repaired**: `bootstrap/smoke-spark.sh` and `verify/role-matrix.py` run on the current Spark runtime image, with explicit OAuth2 catalog authentication.
- **Fixed during Build and Test**:
  - Repeated starts no longer recreate containers (`BUILDX_NO_DEFAULT_ATTESTATIONS=1`).
  - Misleading orphan warnings are suppressed (`COMPOSE_IGNORE_ORPHANS=true`).
- **README rewritten**: a Contents index, components, quick start, modules, users and sign-in, data layout, per-service sections (including Airflow), operations, scripts, and limitations, with no old-stack history. The DBeaver instructions use the StarRocks connection with only `idTokenFile`.

## Main changes
| Area | Paths |
|---|---|
| Compose | `compose.{core,jupyter,jenkins,airflow,starrocks}.yml` (new or renamed); removed `docker-compose.yml` and `docker-compose.deferred.yml` |
| Lifecycle | `scripts/lakehouse.sh`, `scripts/bootstrap-default-product.sh`, `.env.example` |
| Scripts moved | 22 scripts into `scripts/{setup,bootstrap,operations,clients,verify}/`, with root paths fixed |
| Spark smoke | `scripts/bootstrap/smoke-spark.sh`, `scripts/verify/role-matrix.py`, `infra/spark-bootstrap/{create_smoke_tables,verify_role_matrix}.py` |
| Removed | `infra/{tpch-generator,tpch-loader,identity-provisioner,bucket-init,jupyter/examples}`, `infra/polaris/reset-default-product-once.py`, `scripts/prepare-ranger-test-secrets.sh`, `scripts/migrate-jenkins-home.py`, `Jenkinsfile`, `tests/jenkins/test_migrate_home.py` |
| Docs and tests | `README.md`; new `tests/operations/test_compose_modules_contract.py`; updated contract tests across modules |

## Verification
Build and Test passed on 2026-11-09 against the live stack. See `aidlc-docs/current/construction/build-and-test/build-and-test-summary.md`.
- **Tests**: 217 passed, 1 skipped, plus 2 earlier Airflow drift failures (unchanged, out of scope). The JupyterHub broker tests pass (10).
- **Product bootstrap**: passed end to end, including the Spark smoke tables in all three environments and the StarRocks steps.
- **Containers**: none recreated by a repeat `start` or by a stop and start.
- **Opt-outs**: working.
- **Verifiers**: RustFS OIDC and STS, Polaris checks, the full role matrix including its Spark part, the Airflow DAGs, and a StarRocks login all pass. Jenkins passes 8 of 9 (the known missing CI job).

## Deployment
No data migration or reset is required. See [deploy_instructions.md](deploy_instructions.md).

## Risks and limitations
1. **Renamed paths**: anyone calling the old `docker-compose*.yml` files or the old script paths directly must switch to the new names. Archived intents keep the old names as history.
2. **Manual Compose commands**: these must list `compose.core.yml` plus the needed modules. Never use `--remove-orphans`, because it deletes the other modules.
3. **Image recreation on upgrade**: the first `start` after this change may recreate Jenkins, JupyterHub, and the reconciler once, because their images are rebuilt without attestations. Later starts recreate nothing.
4. **Airflow DAG check**: `scripts/verify/airflow-dags.sh` needs the Airflow environment from `lakehouse.sh`, so it is meant to run through `start-airflow`.
5. **Earlier item**: the Jenkins workload CI job is still missing.
