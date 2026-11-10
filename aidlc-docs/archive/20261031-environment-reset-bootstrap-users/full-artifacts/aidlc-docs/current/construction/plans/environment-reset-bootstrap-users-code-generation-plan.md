# Code Generation Plan — environment-reset-bootstrap-users

This plan is the single source of truth for Part 2. Each step is marked `[x]` in the interaction that completes it.

## Unit Context
- **Unit**: `environment-reset-bootstrap-users`. Traceability: FR-1–FR-9 and RB-1–RB-14.
- **Workspace**: this repository only. No file in `../opensource-lakehouse` is edited. Its `.runtime` folder is removed as a Build and Test operator step (RB-14).
- **Not in this stage**: running the reset, starting services, and knowledge updates.

## Steps

### Step 1 — Identity source of truth (FR-3, RB-3)
- [x] Create `infra/keycloak/bootstrap-users.json`: the default password, five groups, and five users (domain-entities.md).

### Step 2 — Realm bootstrap (FR-3–FR-5, RB-1, RB-4, RB-8)
- [x] Modify `infra/keycloak/bootstrap-realm.py`:
  - **Group**: create `role-platform-admin` and give it the `polaris` client role `role-default-owner`.
  - **Writer client**: replace the `write-service-account` client with `lakehouse-writer` (password grant, 3600 s token, Polaris mapper).
  - **Retire**: `ensure_owner_user`, `--owner-*`, and the platform-admin password file; also remove the writer service-account group membership.
  - **Users**: create missing bootstrap users from the JSON, create-only.
  - Report the counts.
- [x] Modify `infra/keycloak/realm-contract.json`: add `role-platform-admin`, replace `write-service-account` with `lakehouse-writer`, and list the bootstrap users with their groups (no password).

### Step 3 — Enforcing user bootstrap (FR-3, RB-2)
- [x] Create `infra/keycloak/bootstrap-users.py`. A pure `plan_user_changes(current, desired)` function, plus apply logic that resets passwords and normalizes groups for the five users only.
- [x] Create `scripts/bootstrap-users.sh` as a thin wrapper.
- [x] Modify `scripts/bootstrap-default-product.sh`: run `scripts/bootstrap-users.sh` after `bootstrap-realm.py`.

### Step 4 — `role-platform-admin` service mappings (FR-4)
- [x] `infra/polaris/reconcile-keycloak-groups.py`: also read `role-platform-admin`, and map its members to the principal role `role-default-owner`.
- [x] `infra/rustfs/bootstrap-policies.py`: add `role-platform-admin` to `ACCESS_MATRIX` with the owner access.
- [x] `infra/airflow/airflow_sso_roles.py` and `infra/airflow/webserver_config.py`: map `role-platform-admin` to `Admin`.
- [x] `infra/jenkins/casc/jenkins.yaml`: give the `role-platform-admin` group `Overall/Administer`.

### Step 5 — Writer migration (FR-5, RB-5–RB-8)
- [x] `scripts/prepare-lakehouse-runtime.py`: write `srv-default-writer-password` from the JSON and stage it; stop creating `platform-admin-password`.
- [x] `infra/airflow-token-broker/app.py`: password grant; `KEYCLOAK_WRITER_CLIENT_ID` defaults to `lakehouse-writer`; `KEYCLOAK_WRITER_USERNAME` (`srv-default-writer`); `KEYCLOAK_WRITER_PASSWORD_FILE`; check `preferred_username`.
- [x] `docker-compose.airflow.yml`: broker environment and password-file secret.
- [x] `infra/spark-bootstrap/create_smoke_tables.py` and `scripts/run-bootstrap-smoke-spark.sh`: password grant and the mounted password file.
- [x] `scripts/verify-polaris-keycloak-auth.py`, `scripts/verify-keycloak-outage.py`, `scripts/verify-polaris-oidc-negative-cases.py`: the writer token via the password grant; principal `srv-default-writer`.

### Step 6 — Bundles inside this repository (FR-9, RB-13)
- [x] `scripts/lakehouse.sh`: the default `LAKEHOUSE_BUNDLE_HOST_ROOT` becomes `${ROOT_DIR}/.runtime/airflow-dag-bundles`; remove `LAKEHOUSE_PROJECT_ROOT`.
- [x] `scripts/provision-airflow-secrets.sh`: create the Bundle directory in this repository; no sibling path.
- [x] `infra/airflow/validate-bundle-config.py`: require `<repo>/.runtime/airflow-dag-bundles`; drop `LAKEHOUSE_PROJECT_ROOT`.
- [x] `docker-compose.airflow.yml`: remove `LAKEHOUSE_PROJECT_ROOT`.

### Step 7 — Full reset (FR-1, FR-2, RB-9–RB-12)
- [x] Create `scripts/reset-lakehouse.py`. A pure inventory selection from the Docker listings; the prompt, `--yes`, and `--dry-run`; ordered removal; the `.runtime` path guard.
- [x] Modify `scripts/lakehouse.sh`: add the `reset [--yes|--dry-run]` command and usage.

### Step 8 — Tests
- [x] `tests/keycloak/test_bootstrap_users_contract.py`: JSON shape; `plan_user_changes` (password reset, group normalization, users outside the set untouched); create-only behavior in the realm bootstrap; `role-platform-admin` client role; the `lakehouse-writer` client; `write-service-account` absent.
- [x] `tests/test_reset_lakehouse.py`, placed under `tests/operations/`: inventory selection (exact names, prefix, labels, other projects excluded); confirmation (`reset` only, `--yes`, `--dry-run`, mutually exclusive); the path guard.
- [x] Update the existing tests that assert old behavior:
  - the RustFS policy names (now five)
  - the Jenkins matrix
  - the Keycloak contract tests that expect `write-service-account`
  - Airflow mapping tests, adding the `role-platform-admin` expectation only (the developer drift is out of scope)
  - the broker tests, if any
- [x] Add a Bundle-root contract (`tests/airflow/test_bundle_root_contract.py`): no `LAKEHOUSE_PROJECT_ROOT`, and the root is inside the repository.

### Step 9 — README (FR-8)
- [x] Add "Start the platform" (prerequisites, `start`, `bootstrap-default-product.sh`, optional `start-airflow`, URLs, the bootstrap users table with `ChangeM3!`) and "Reset the platform" (what is deleted and kept, the prompt, `--yes`, `--dry-run`, irreversibility, back up Jenkins and data first). Remove the obsolete `platform-admin-password` and `write-service-account` text.
- [x] Create the code summary `aidlc-docs/current/construction/environment-reset-bootstrap-users/code/code-summary.md`.

## Traceability
| Requirement | Steps |
|---|---|
| FR-1, FR-2 Reset | 7, 8 |
| FR-3 Bootstrap users | 1, 2, 3, 8 |
| FR-4 Platform admin | 2, 4, 8 |
| FR-5 Writer migration | 2, 5, 8 |
| FR-6 Startup | 3 (wiring); Build and Test |
| FR-7 Narrow reset kept | (unchanged) |
| FR-8 README | 9 |
| FR-9 Bundles | 6, 8 |
