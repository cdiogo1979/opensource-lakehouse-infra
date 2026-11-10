# Code Generation Plan — data-product-provisioning

This plan is the single source of truth for Code Generation. Brownfield: existing files are changed in place, and no `_new` or `_v2` copies are made. Application code lives at the workspace root; only the code summary goes under `aidlc-docs/`.

## Unit context
- **Requirements**: FR-1..FR-11 (CR-1 included).
- **Design**:
  - Application Design C1–C11, S1–S5
  - Functional Design BR-1..BR-10 and flows A–F
- **Dependencies**: none on other units. Runtime: Keycloak, Polaris 1.8.0, RustFS, StarRocks 4.1.7, JupyterHub, Airflow, and Jenkins, as running today.
- **Data owned**:
  - the product files (`data-products/*.yaml`)
  - the applied state (`.runtime/state/data-products/`)
  - removal backups (`.runtime/backups/*-remove-*`)
- **Not changed**:
  - the Airflow token broker, the `lakehouse-writer` client, and `bootstrap-users.json`
  - the default smoke tables (`create_smoke_tables.py`)
  - `rustfs-sts.py` and `polaris-keycloak-auth.py`, which remain `default` verifiers

## Steps

### Step 1 — Product model (C1, C2; FR-1, BR-1)
- [x] Create `infra/products/__init__.py`, `infra/products/data_products.py`:
  - load and validate, collisions, locked names, applied state, the lock directory
  - the group pattern, the template renderer, and derived names
- [x] Create `infra/products/template.yaml`, the standard file with a `{name}` placeholder.
- [x] Create `data-products/default.yaml`, which reproduces today's names, matrices, and app mappings exactly.
- [x] Create `tests/products/test_data_products.py`:
  - validation rules, reserved names, unknown keys, collisions, locked names
  - the template round trip, and `default.yaml` matching today's constants

### Step 2 — Keycloak (C3, C4; FR-3, FR-9, BR-5, BR-9)
- [x] Create `infra/keycloak/product-identity.py` with apply, `--remove`, `--inventory` (members), and `--dry-run`. It manages:
  - groups and client roles
  - the platform-admin owner mappings
  - the `srv-starrocks` writer membership
  - the writer user, and its password file on creation only
- [x] Change `infra/keycloak/bootstrap-realm.py`: the product groups, roles, and `srv-starrocks` membership move to product-identity. The realm, clients, mappers, and `role-platform-admin` stay.
  - The bootstrap users' groups must exist first, so `bootstrap-default-product.sh` runs product-identity before `bootstrap-users.sh`.
- [x] Create `infra/keycloak/create-user.py`: BR-9; the password comes from a file or the default, sent in the request body only.
- [x] Update `infra/keycloak/realm-contract.json` to describe product groups by pattern and `default` as the first product.
- [x] Tests:
  - `tests/keycloak/test_product_identity.py`: plans for apply and remove with a fake admin API
  - `tests/keycloak/test_create_user.py`: validation, refusal on an existing user, no password in arguments
  - update `test_bootstrap_users_contract.py`

### Step 3 — RustFS (C5; FR-4, BR-4)
- [x] Change `infra/rustfs/bootstrap-buckets.py` and `bootstrap-policies.py`:
  - `--product` (all files by default), `--remove`, `--inventory` (object counts), `--purge-data`, `--dry-run`
  - product policies converge to the file; the `role-platform-admin` policy aggregates every product's buckets
- [x] Update `tests/rustfs/test_policy_contract.py`: per-level statements, the aggregate, and removal.

### Step 4 — Polaris (C6; FR-5, BR-2, BR-7)
- [x] Rename `infra/polaris/bootstrap-default-catalogs.py` to `bootstrap-catalogs.py`, and update every reference (scripts, tests, README). It:
  - extends the shared catalogs' allowed locations, and checks the remaining storage settings as today
  - creates namespaces with their product location; a namespace with another location is a conflict
  - removes, with `--remove`: tables and views on purge, then namespaces and the allowed location
  - inventories tables and views with `--inventory`
- [x] Change `infra/polaris/bootstrap-product-authorization.py`:
  - principal roles, catalog roles, catalog-level and namespace-level grants per BR-2
  - additive first, then revokes of extras (BR-7); `none` levels delete the catalog role
  - `--remove`, `--dry-run`, and the `--roles-only` mode kept
- [x] Change `infra/polaris/oidc.properties`: `polaris.features."ALLOW_NAMESPACE_CUSTOM_LOCATION"=true` and the filter and mapping pattern (AD-Q1, AD-Q2).
- [x] Tests: update `tests/polaris/test_unit3_*` for the flag, the pattern, and the namespace grant plans, including the `default` migration plan from today's catalog-wide grants.

### Step 5 — StarRocks (C7; FR-6, BR-3)
- [x] Change `infra/starrocks/starrocks_common.py`: the environments, group roles, and matrices come from the product files; database-scoped grant forms; `role_platform_admin` stays catalog-wide.
- [x] Change `infra/starrocks/bootstrap-starrocks.py`:
  - `--product`, `--remove` (roles, and MV databases with `FORCE` on purge), `--inventory` (MV and table counts)
  - the coverage rule extended to database-scoped objects, and refreshing the catalogs' database lists when new namespaces appear
- [x] Update `tests/starrocks/*`: strategies over products, the grant matrix per level, coverage, and removal.

### Step 6 — Reconcilers (C8; FR-8)
- [x] Change `infra/polaris/reconcile-keycloak-groups.py`: groups and the platform-admin owner roles come from all files; an invalid file skips the run with nothing changed.
- [x] Change `infra/starrocks/reconcile-starrocks-users.py`: managed roles from all files.
- [x] Change `infra/polaris/reconciler/Dockerfile`: add pinned PyYAML and copy `infra/products/`.
- [x] Change `compose.core.yml`: mount `data-products` read-only into `polaris-group-reconciler`.
- [x] Update the reconciler tests.

### Step 7 — Apps (C9; FR-7, BR-6)
- [x] **JupyterHub**:
  - `lakehouse_policy.py`: admitted groups from the mounted files, failing closed
  - `jupyterhub_config.py`: a `check_allowed` hook in place of the static `allowed_groups`
  - Dockerfile: copy `data_products.py`
  - `compose.jupyter.yml`: the read-only mount
- [x] **Airflow**:
  - `airflow_sso_roles.py`: the mapping from the mounted files, failing closed
  - Dockerfile: copy `data_products.py`
  - `compose.airflow.yml`: mount it into the API server
- [x] **Jenkins**:
  - Create `infra/products/render_jenkins.py` (deterministic).
  - `infra/jenkins/casc/jenkins.yaml` becomes the template with the static entries.
  - `scripts/setup/prepare-runtime.py` renders `.runtime/container-mounts/jenkins-casc.yaml`.
  - `compose.jenkins.yml` mounts the rendered file.
- [x] Update the tests in `tests/jupyterhub`, `tests/airflow`, `tests/jenkins`, and `tests/integration`.

### Step 8 — Operator scripts (C10, C11; FR-2, FR-9, FR-11, flows A–F)
- [x] Create `scripts/operations/create-data-product.sh`: `--init`, and apply with `--dry-run` and `--no-restart`. It holds the lock, runs the steps in order, restarts Jenkins when the render changed, and records the state.
- [x] Create `scripts/operations/remove-data-product.sh`:
  - the guards, the inventory, the typed confirmation with members
  - the backup, the removal in reverse order, the reconcile
  - deleting the file and state last
- [x] Create `scripts/operations/create-user.sh`.
- [x] Change `scripts/bootstrap-default-product.sh`: apply every product file (`default` first) in place of the single-product steps.
- [x] Create `tests/operations/test_data_product_scripts.py`: usage, refusing `default`, the lock, exit codes, no secrets in arguments, and a shellcheck-style bash 3.2 syntax check (`bash -n`).

### Step 9 — Verifiers (Build and Test support)
- [x] Change `scripts/verify/role-matrix.py` and `infra/spark-bootstrap/verify_role_matrix.py`:
  - `--product NAME` (default `default`): expected access from the product file
  - an **isolation** check: every role is refused on another product's namespaces
- [x] Update the related tests.

### Step 10 — Documentation and summary (FR-10)
- [x] Update `README.md`:
  - a "Data products" section: the file format, `--init`, apply, edit and reapply, remove
  - an "Adding users" section
  - the updated access model, with the deliberate reductions for `default` and the platform-wide Airflow and Jenkins admin note
  - the Contents index and the Scripts table
- [x] Run the full contract suite and record the results.
- [x] Create `aidlc-docs/current/construction/data-product-provisioning/code/code-summary.md`.

## Traceability
| Requirement | Steps |
|---|---|
| FR-1 product files | 1 |
| FR-2 create and apply | 8 |
| FR-3 Keycloak | 2 |
| FR-4 RustFS | 3 |
| FR-5 Polaris | 4 |
| FR-6 StarRocks | 5 |
| FR-7 apps | 7 |
| FR-8 reconcilers | 6 |
| FR-9 create user | 2, 8 |
| FR-10 docs and tests | 1–10 |
| FR-11 remove | 2–5, 8 |

## Live changes
Code Generation changes **files only**: no restarts and no changes to the running stack. The one-time migration (Polaris restart, applying `default.yaml`, the app recreates) runs in Build and Test, with the baseline taken first.
