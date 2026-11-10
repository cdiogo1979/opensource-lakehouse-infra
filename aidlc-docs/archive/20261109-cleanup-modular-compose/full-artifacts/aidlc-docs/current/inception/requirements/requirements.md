# Requirements — Cleanup and Modular Compose

## Intent Analysis
- **User request**: "let start a small intent to clean up scripts and other files not needed anymore on the current solution. also remove the tpch generator and loader . furthermore lets make it more modular in terms of the docker compose. there should be a compose.core  (keycloak,polaris, rustfs), compose.jupyter, compose.jenkins in additional to the airflow and starrocks already existing"
- **Type**: cleanup and restructuring, with one repair (Q3).
- **Scope**: repository files, the Compose layout, `lakehouse.sh`, the scripts and tests that name Compose files, and the README.
- **Complexity**: moderate. Depth is minimal to standard. The inventory is in `../reverse-engineering/cleanup-inventory.md`, and the module map in `../reverse-engineering/compose-module-map.md`.

## Functional Requirements

### FR-1 Remove unused files
Remove:
- `infra/tpch-generator/` and `infra/tpch-loader/` (requested)
- `infra/identity-provisioner/`, `infra/bucket-init/`, and `infra/polaris/reset-default-product-once.py`, with the README "One-time catalog path reset" section
- `scripts/prepare-ranger-test-secrets.sh`
- `docker-compose.deferred.yml`
- `infra/jupyter/examples/`
- the root `Jenkinsfile` (Q1: A)

Remove local caches (`__pycache__`, `.pytest_cache`, `.hypothesis`) and add `.pytest_cache/` and `.hypothesis/` to `.gitignore`.

Removed files are snapshotted into the intent folder first and preserved in the closure archive, because there is no git.

### FR-2 Remove the finished Jenkins migration (Q2: A)
- Remove `scripts/migrate-jenkins-home.py`, the `lakehouse.sh remove-legacy-jenkins` command, and the related README text and tests.
- Jenkins starts with its existing home volume. The existing `.lakehouse-home-origin` marker may stay in the volume, unused.

### FR-3 Repair the Spark smoke checks (Q3: A)
- `scripts/bootstrap/smoke-spark.sh` and the Spark part of `scripts/verify/role-matrix.py` use the current runtime image `local/lakehouse-spark-runtime:3.5.5_1.10.2`, so `bootstrap-default-product.sh` runs end to end again, including the StarRocks steps.
- They keep their existing behavior: smoke tables in three environments, and the role-matrix data checks.

### FR-4 Modular Compose (Q4: A)
Compose is split into five files with the project `lakehouse-local`:

| File | Services |
|---|---|
| `compose.core.yml` | keycloak-db, keycloak, polaris-db, polaris-schema-init, polaris, polaris-group-reconciler, rustfs; networks core, data-access, rustfs-identity; their volumes |
| `compose.jupyter.yml` | jupyterhub; the network jupyter-user and volume jupyterhub-state |
| `compose.jenkins.yml` | jenkins; volume jenkins-home |
| `compose.airflow.yml` | renamed from `docker-compose.airflow.yml`, unchanged otherwise |
| `compose.starrocks.yml` | renamed from `docker-compose.starrocks.yml`, unchanged otherwise |

- `docker-compose.yml` is removed.
- Container, volume, and network names stay the same, so existing state and reset keep working, and no reset is needed.

### FR-5 Module selection (Q5: A)
- Core always runs.
- Jupyter, Jenkins, and StarRocks run with `lakehouse.sh start`, `status`, and `stop` by default. Each can be turned off in `.env` with `JUPYTER_ENABLED=false`, `JENKINS_ENABLED=false`, or `STARROCKS_ENABLED=false`.
- Airflow keeps `start-airflow`, `airflow-status`, and `stop-airflow`, and is added to the Compose file list whenever those commands run.
- Every script and test that names a Compose file uses the new files. `lakehouse.sh` builds the file list in one place.

### FR-6 README
- Document the modules, their files, the opt-out flags, and how to run `docker compose` by hand with the right files.
- Remove the obsolete sections: the one-time reset, the Jenkins migration and legacy removal, and the deferred inventory.

### FR-6a README rewrite (change request during Code Generation, 2026-11-09)
- **User input**: "on readme remove references to the old stack , add a index on the top of the page, make it easier to understand".
- **Removed**: references to the old stack and project history. That covers the "being rebuilt" intro, the "Unit 2/3" sections, the Build and Test history, the retired-components list, legacy volume notes, and links to archived docs.
- **Added**: a Contents index at the top.
- **New structure**: Components, Quick start, Compose modules, Users and sign-in (one access table per group), Data layout, one section per service (including a new Airflow section), Operations, Scripts, and Known limitations.
- **Corrected**: the JupyterHub admitted groups, and the platform-admin row in the RustFS policy table.

### FR-7 Script layout (change request during Code Generation, 2026-11-09)
- **User input**: "organise the scipts inside the /scripts folder in a consistent way". The user chose "By purpose".
- **Layout**:
  - The entry points `lakehouse.sh` and `bootstrap-default-product.sh` stay at the top of `scripts/`, with `aidlc_intent.py`, whose path the AI-DLC skill uses.
  - The other 22 scripts move into `setup/`, `bootstrap/`, `operations/`, `clients/`, and `verify/`, with shorter names inside each folder, for example `verify/role-matrix.py` and `bootstrap/smoke-spark.sh`.
- Every reference outside the archives is updated, and moved scripts resolve the repository root from their new depth.

## Non-Functional Requirements
- No change to the running platform's behavior with every module enabled. Containers are recreated only if their definition changes.
- Contract tests are updated for the new layout. The full suite passes, apart from the 2 known Airflow drift failures.
- Verified live: start with all modules; opt-outs; the product bootstrap end to end; existing verifiers.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q6: B) |
| Property-Based Testing | No | Requirements Analysis (Q7: C) |
| Resiliency Baseline | No | Requirements Analysis (Q8: B) |

## Out of scope
- The BI token intent.
- The Jenkins CI job restore.
- The Airflow role drift.
- The JupyterHub broker test `PYTHONPATH`.
- The RustFS console version.
