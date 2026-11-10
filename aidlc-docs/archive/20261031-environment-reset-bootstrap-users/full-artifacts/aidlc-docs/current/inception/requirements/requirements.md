# Requirements — Environment Reset and Bootstrap Users

## Intent Analysis
- **User request**: "in this new intent you will develop script that resets the entire environment (deletes buckets, dabases, groups , users, secrets, etc) . the existing startup script should then be adjusted a tested, with a small adjustement which is to create some bootstrap users joe-developer (role-defaut-developer) , peter-analyst (role-default-analyst) , maria-owner (role-default-owner) , srv-default-writer (role-default-writer) and platform-admin (role-platform-admin) . all users can be created with the default pass ChangeM3! . Finally this should be reflected in the read me file (how to start the platform and how to reset the plaform)"
- **Request type**: New Feature (reset, bootstrap users) and Enhancement (startup). The clarifications add a Migration: the writer workload identity moves from the `write-service-account` client to the `srv-default-writer` user.
- **Scope estimate**: System-wide:
  - operator scripts and the Keycloak bootstrap
  - service group mappings for `role-platform-admin`
  - the Airflow writer token broker, Spark smoke job, and Polaris verifiers
  - runtime secrets
  - README
- **Complexity estimate**: Complex. The reset is destructive and irreversible. The writer-identity migration changes the authentication flow of Airflow and Spark workloads.
- **Requirements depth**: Standard
- **Clarifications**: `requirement-verification-questions.md` (13) and `requirement-verification-clarification-questions.md` (3). No remaining contradictions.

## Functional Requirements

### FR-1 Full environment reset (Q3: C, Q4: B, C3: A)
`scripts/lakehouse.sh reset` deletes all v2 lakehouse state:
- stops and removes the core and Airflow Compose services
- deletes the volumes `lakehouse-local_keycloak-db-data`, `_polaris-db-data`, `_rustfs-data`, `_jupyterhub-state`, `_jenkins-home`, and `_airflow-postgres-data`; together these hold all buckets, databases, catalogs, realm, groups, users, policies, and the Jenkins and Airflow metadata
- deletes the JupyterHub single-user home volumes (`lakehouse-jupyter-home-*`) and the runtime containers labelled `lakehouse-local.role=jupyter-user-server` or `=airflow-spark-run`
- removes the v2 networks: `lakehouse-local_core`, `_jupyter-user`, `_data-access`, `_rustfs-identity`, `_airflow-internal`, `_airflow-spark`
- deletes `.runtime/credentials/`, `.runtime/container-mounts/`, and `.runtime/airflow-dag-bundles/` (all secrets, certificates, and generated configuration)
- deletes the Airflow Bundle checkouts, which live in this repository's `.runtime/airflow-dag-bundles/` after FR-9. The reset never touches the sibling `opensource-lakehouse` repository.

It keeps:
- the `local/lakehouse-*` images
- volumes and containers of other projects (`iceberg-poc-*`, `jupyter-platform_*`, `openmetadata-docker_*`, `airflow-spark-jenkins_*`, `jenkins_home`)
- all other files in the sibling repository
- `.runtime/aidlc-test-venv`

### FR-2 Reset safety (Q4: B, C3: A)
- The reset prints the exact inventory of what exists and will be deleted, then asks the operator to type `reset`. Any other input aborts with no changes.
- `--yes` skips the prompt for non-interactive use, still printing the inventory.
- `--dry-run` prints the inventory and changes nothing.
- Only resources matching the exact names, prefixes, and labels above are touched.
- The reset is idempotent: running it on an already-clean environment succeeds.

### FR-3 Bootstrap users (Q2: B, Q5: A, Q6, C1: A)
| User | Group | Password |
|---|---|---|
| `joe-developer` | `role-default-developer` | `ChangeM3!` |
| `peter-analyst` | `role-default-analyst` | `ChangeM3!` |
| `maria-owner` | `role-default-owner` | `ChangeM3!` |
| `srv-default-writer` | `role-default-writer` | `ChangeM3!` |
| `platform-admin` | `role-platform-admin` | `ChangeM3!` |

- **Password**: permanent (Q2: B), with no forced change.
- **When users are created**: routine `lakehouse.sh start` creates missing groups and missing users only, never changing existing passwords or groups.
- **Enforcing step**: `scripts/bootstrap-users.sh` is explicit and is run by `bootstrap-default-product.sh` after a reset. Each run re-applies the default password and makes each user's group membership exactly its default group (C1: A).
- **Profile completeness**: users are enabled, with no required actions and a complete profile (first name, last name, email), so Keycloak does not interrupt login.
- **Default password storage**: `ChangeM3!` is the documented default and lives in one place, a constant in the bootstrap code. It is not a generated secret file.
- **Retired file**: `.runtime/credentials/platform-admin-password` is no longer created or used.

### FR-4 `role-platform-admin` (Q1: A)
- The realm bootstrap creates the group `role-platform-admin`.
- It grants the same rights as `role-default-owner` in every service:
  - Polaris (owner product role and principal reconciliation)
  - RustFS (a group-named policy equal to the owner policy)
  - Airflow (Admin)
  - Jenkins (Administer)
  - JupyterHub (admission equal to owner, if owner is admitted)
- `platform-admin` is in `role-platform-admin` only, no longer in `role-default-owner`.
- Change note (2026-10-31, Build and Test, user request): `role-platform-admin` also gets the `lakehouse` realm's `realm-management/realm-admin` role. It does not get `master` realm administration.
- Change note (2026-10-31, Build and Test, user request): `role-platform-admin` is admitted to JupyterHub and is the Hub admin group.

### FR-5 Writer workload identity migration (Q7: B, C2: B)
- **Identity change**: Airflow's writer token broker and the Spark bootstrap smoke job obtain writer tokens as `srv-default-writer` instead of the `write-service-account` client.
- **Client**: a dedicated confidential Keycloak client for the writer password grant, with direct access grants enabled and the existing one-hour writer access-token lifetime.
- **Broker**: it validates tokens accordingly. The writer password reaches the broker and Spark only through protected mounted files, never through the environment or logs.
- **Polaris principal**: the Polaris writer principal becomes `srv-default-writer`, reconciled from `role-default-writer`.
- **Retirement**: `write-service-account` is removed from `role-default-writer` and retired from the realm bootstrap and contract.
- **Updated components**: the Polaris writer verifiers (`verify-polaris-keycloak-auth.py`, `verify-keycloak-outage.py`, `verify-polaris-oidc-negative-cases.py`), `create_smoke_tables.py`, `run-bootstrap-smoke-spark.sh`, the broker, and the Compose wiring.
- **Out of scope**: the legacy and deferred `tpch-loader` and `starrocks` references, which are not part of the v2 runtime.

### FR-6 Startup (Q8: A)
- The documented startup stays two steps: `scripts/lakehouse.sh start`, then `scripts/bootstrap-default-product.sh`.
- Airflow stays optional: `scripts/lakehouse.sh start-airflow`.
- Both steps work on a freshly reset environment.

### FR-7 Narrow reset (Q10: A)
`infra/polaris/reset-default-product-once.py` is kept. The README presents the full reset as the primary reset.

### FR-8 README
- Document how to start the platform: the prerequisites, the two-step start, the optional Airflow start, the bootstrap users table with the default password, and service URLs.
- Document how to reset the platform: what is deleted and kept, the prompt, `--yes`, `--dry-run`, and irreversibility.
- Remove the obsolete `platform-admin-password` and `write-service-account` instructions.

### FR-9 Airflow Bundles inside this repository (change request, 2026-10-31)
- **New default location**: Airflow Git Bundle checkouts move from `../opensource-lakehouse/.runtime/airflow-dag-bundles` to this repository's `.runtime/airflow-dag-bundles/`. The default `LAKEHOUSE_BUNDLE_HOST_ROOT` becomes `<infra-v2>/.runtime/airflow-dag-bundles`.
- **Scripts that change**:
  - `scripts/provision-airflow-secrets.sh` creates that directory (mode 0700).
  - `infra/airflow/validate-bundle-config.py` requires the Bundle root to be this repository's ignored `.runtime/airflow-dag-bundles`, instead of the sibling's.
- **Unchanged**: the Bundle configuration (`lakehouse-main` and `lakehouse-uat`, cloned from `https://github.com/cdiogo1979/opensource-lakehouse.git`) and the Compose mounts, which already use the variable.
- **Independence (change 2026-10-31)**: infra-v2 and `opensource-lakehouse` are independent projects. infra-v2 consumes the workload repository only through Airflow's Git Bundles, cloned from GitHub into infra-v2's `.runtime/airflow-dag-bundles`; Jenkins CI also clones from GitHub.
  - `LAKEHOUSE_PROJECT_ROOT` is removed from `scripts/lakehouse.sh`, `scripts/provision-airflow-secrets.sh`, `infra/airflow/validate-bundle-config.py`, and `docker-compose.airflow.yml`.
  - No infra-v2 script or configuration references the sibling's local checkout.
  - infra-v2's knowledge base keeps no documents about the other project.
- **One-time cleanup (change 2026-10-31)**: remove the entire `../opensource-lakehouse/.runtime` folder. It is Git-ignored and holds only the old `airflow-dag-bundles` checkouts (5.3 MB). It should not exist in the workload repository. No other sibling file is touched. Airflow re-clones the Bundles into the new location on the next `start-airflow`.

## Out of Scope
- Deleting images or other projects' resources.
- Changes to `opensource-lakehouse` source.
- MFA.
- Production hardening.
- `tpch-loader` and `starrocks`.

## Non-Functional Requirements
- **Safety**: the reset never touches anything outside the exact v2 inventory, and the printed inventory matches what is deleted.
- **Idempotency**: reset, start, product bootstrap, and user bootstrap are all safe to rerun.
- **Secrets**: the writer password and other secrets reach containers only as mounted files. The shared default password is a deliberate local-development convenience and is documented as such.
- **Verification is local only**: this is a single-node development stack.

## Verification Requirements (Q9: A)
Contract tests plus a full local cycle:
1. reset, and confirm nothing in the inventory remains
2. `lakehouse.sh start`
3. `bootstrap-default-product.sh`, including the user bootstrap, Polaris reconciliation, and the Spark smoke job as `srv-default-writer`
4. check every bootstrap user exists in exactly its group and can log in with `ChangeM3!`
5. rerun the user bootstrap and confirm defaults are re-applied
6. rerun the existing verifiers: RustFS OIDC, Jenkins OIDC, Polaris writer, and RustFS STS
7. run `start-airflow` and check that a writer token is issued through the broker as `srv-default-writer`

## Assumptions and Risks

> **Change 2026-10-31 (user request during Workflow Planning)**: the Airflow Bundles move into this repository (FR-9). This supersedes the Q3 answer ("also sibling Bundles"): the reset deletes only this repository's state, and the sibling repository is cleaned once by FR-9. Risk 4 is updated accordingly.
1. **Data loss**: the reset destroys all current local data, including Jenkins build history (now the only copy), Airflow metadata, buckets, and catalogs. Back up anything needed before running it.
2. **Writer migration**: the password grant (ROPC) replaces the client-credentials grant for workloads. That is a weaker pattern, and with the permanent shared password `ChangeM3!` the workload writer credential becomes guessable. It is accepted for local development only.
3. **Airflow DAG verification**: a full writer-token path through Airflow needs `start-airflow`. A real DAG run depends on the sibling repository's DAGs and on the CI regression from the previous intent being fixed.
4. **Bundle move**: the one-time removal of `../opensource-lakehouse/.runtime` deletes Airflow's current checkouts. Airflow re-clones them into this repository's `.runtime` on the next `start-airflow`. Running Airflow must be restarted on the new path.
5. **Jenkins after reset**: Jenkins starts with an empty home and no job (the previous intent's fresh-home path). The CI job and history are lost unless the home is backed up first.

## Extension Configuration
| Extension | Decision |
|---|---|
| Security Baseline | No (Q11: B) |
| Property-Based Testing | No (Q12: C) |
| Resiliency Baseline | No (Q13: B) |
