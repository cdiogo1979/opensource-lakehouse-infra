# PR Request — Data products and user scripts

_Proposed PR description. No pull request has been created; this workspace has no git metadata._

## Problem
- **One hard-coded product**: the platform supported only the `default` data product. Its name was a constant in about 22 files across Keycloak, RustFS, Polaris, StarRocks, the reconcilers, and the apps.
- **No operator commands**: there was no way to create or remove a data product, and no command to add a user.

## Solution
- **One YAML file per product**: every product, `default` included, is a file in `data-products/` holding its whole configuration:
  - environments: namespace, bucket, and MV database in the shared catalogs
  - the four groups
  - access levels per role and environment
  - MV levels, app mappings, and the writer user

  Every component reads these files.
- **Shared catalogs**: products live in the shared environment catalogs. Polaris grants are namespace-scoped and StarRocks grants database-scoped, for every product, `default` included. Each product's namespace lives in its own bucket, which needs the Polaris feature `ALLOW_NAMESPACE_CUSTOM_LOCATION`.
- **Operator scripts** in `scripts/operations/`:
  - `create-data-product.sh --init <name>` writes a standard file. `create-data-product.sh <file> [--dry-run] [--no-restart]` applies it and converges every component, revokes included. Names are locked once applied.
  - `remove-data-product.sh <name> [--purge-data] [--yes] [--dry-run]` refuses `default` and refuses while data exists unless `--purge-data`. It asks for the name to be typed, backs up first, and resumes after a failure.
  - `create-user.sh <username> …` creates a user with no groups; groups are assigned in Keycloak.
  - **Admin sign-in**: all three sign in to Keycloak as a platform administrator: `--admin-user` and `--admin-password-file`, or `LAKEHOUSE_ADMIN_PASSWORD`, or a hidden prompt. A password is never a command-line value. Users outside `role-platform-admin` are refused.
- **No restarts for new products**, except Jenkins:
  - The Polaris filter accepts the pattern `role-<token>-<role>`.
  - JupyterHub and Airflow read the files at each sign-in, and fail closed if a file is invalid.
  - Jenkins' matrix is rendered from the files, and Jenkins restarts only when it changes.
- **Change requests during the intent**:
  - CR-1: YAML files and a removal script
  - CR-2: developers author MVs in dev
  - CR-3: `data-products/` at the repository root
  - CR-4: platform-admin credentials as parameters

## Main changes
| Area | Paths |
|---|---|
| Product model | `data-products/default.yaml`; `infra/products/{data_products.py,template.yaml,render_jenkins.py,product-cli.py}` |
| Operator scripts | `scripts/operations/{create-data-product.sh,remove-data-product.sh,create-user.sh,lib/data-products.sh}` |
| Keycloak | `infra/keycloak/{keycloak_products.py,product-identity.py,create-user.py}` (new); `bootstrap-realm.py`, `realm-contract.json` |
| RustFS | `infra/rustfs/bootstrap-{buckets,policies}.py`: per product, converging, removal and purge |
| Polaris | `infra/polaris/bootstrap-catalogs.py` (renamed from `bootstrap-default-catalogs.py`), `bootstrap-product-authorization.py` (namespace-scoped), `oidc.properties` (flag and pattern), `reconcile-keycloak-groups.py`, `reconciler/{Dockerfile,run.sh}` |
| StarRocks | `infra/starrocks/{starrocks_common.py,bootstrap-starrocks.py,reconcile-starrocks-users.py}`: database-scoped, per product, removal |
| Apps | JupyterHub `lakehouse_policy.py`, `jupyterhub_config.py`; Airflow `airflow_sso_roles.py`, `airflow_oauth_security_manager.py`, `webserver_config.py`; Jenkins `casc/jenkins.yaml` (template) |
| Compose | `compose.core.yml` (sync job mount), `compose.jupyter.yml`, `compose.airflow.yml`, `compose.jenkins.yml` (product mounts, rendered CasC) |
| Lifecycle | `scripts/setup/prepare-runtime.py` (renders Jenkins), `scripts/bootstrap-default-product.sh` (all products), `scripts/operations/reset-lakehouse.py` (also `.runtime/state`) |
| Verification | `scripts/verify/role-matrix.py --product`, `infra/spark-bootstrap/verify_role_matrix.py` (isolation, setup) |
| Docs and tests | `README.md` (Data products, Adding users); `tests/conftest.py` and seven new test modules |

## Verification
- **Contract suite**: `PYTHONPATH=infra/jupyter/hub python3 -m pytest -q tests` gives 332 passed, 1 skipped, 1 failed. The failure is the pre-existing Airflow developer-role drift.
- **Live, on the local stack**:
  - the `default` migration, with the role matrix identical before and after
  - Polaris and StarRocks converged
  - apps recreated
  - a `sales` product created, verified with isolation both ways, edited, reapplied, and removed (refused with data, purged, resumed)
  - a user created, with duplicate and non-admin refusals
  - the sign-in verifiers
- **Fixed during Build and Test**: seven findings, all with regression tests (listed in the code summary).
- **Not run**: interactive browser sign-ins to JupyterHub, Airflow, and Jenkins as a new product's user. The mappings were checked in the running containers.

## Deployment
**Ordered steps are required** for an existing stack. See [`deploy_instructions.md`](deploy_instructions.md). The local stack used in Build and Test is already migrated.

## Risks and limitations
- **Access change for `default`**: grants move from catalog-wide to namespace-scoped. Owners lose catalog-wide management, writers and dev developers lose namespace creation, and StarRocks writers and owners lose `CREATE DATABASE`. Developers gain MV authoring in dev. Read and write per environment are unchanged.
- **Server-wide Polaris flag**: `ALLOW_NAMESPACE_CUSTOM_LOCATION` is enabled for the whole server. Tables stay confined to the catalogs' allowed locations, and product roles cannot create namespaces.
- **Visibility**: every product's namespace names are visible to anyone with catalog access.
- **Platform-wide app rights**: Airflow and Jenkins rights from any product file apply platform-wide.
- **StarRocks delay**: a new product becomes readable through StarRocks within about five minutes, at the catalog token renewal.
- **Out of scope**: the Airflow token broker still writes only as `srv-default-writer`.
- **Follow-ups**: the Airflow developer-role drift, the Jenkins CI job restore, and the other items in `aidlc-state.md`.
