# Code Summary — data-product-provisioning

Code Generation changed files only; nothing in the running stack changed. Build and Test runs the one-time migration: the access baseline, the Polaris restart, applying `default.yaml`, and recreating the apps.

## Change requests during Code Generation
- **CR-2**: developers author StarRocks MVs in dev (read, read, author).
- **CR-3**: the product files live in `data-products/` at the repository root.
- **CR-4**: the operator scripts sign in to Keycloak as a platform administrator (`--admin-user`, `--admin-password-file`, `LAKEHOUSE_ADMIN_PASSWORD`, or a prompt). They refuse users outside `role-platform-admin`.

## Created
| Path | Purpose |
|---|---|
| `data-products/default.yaml` | The default product, reproducing today's names, matrices, and app mappings (plus CR-2) |
| `infra/products/data_products.py` | Product model: validation, collisions, locked names, applied state, the lock, the group pattern, app helpers |
| `infra/products/template.yaml` | The standard file for `--init` |
| `infra/products/render_jenkins.py` | Deterministic Jenkins CasC render. It rewrites in place because of the file bind mount, and has `--check` and `--exclude` |
| `infra/products/product-cli.py` | init, validate, record, resolve, summarize, backup, forget |
| `infra/keycloak/keycloak_products.py` | Per-product Keycloak objects, and the platform-admin sign-in and check |
| `infra/keycloak/product-identity.py` | Keycloak apply, remove, and member inventory per product |
| `infra/keycloak/create-user.py` | Create one user with no groups |
| `scripts/operations/create-data-product.sh`, `remove-data-product.sh`, `create-user.sh`, `lib/data-products.sh` | Operator scripts (bash 3.2) |
| Tests | `tests/products/test_data_products.py`, `tests/keycloak/test_product_identity.py`, `tests/rustfs/test_product_storage.py`, `tests/polaris/test_product_catalogs_and_grants.py`, `tests/polaris/test_reconciler_products.py`, `tests/starrocks/test_product_access.py`, `tests/operations/test_data_product_scripts.py` |

## Modified
| Path | Change |
|---|---|
| `infra/keycloak/bootstrap-realm.py` | Product groups from the files (through `keycloak_products`); `KeycloakAdmin` takes a login realm |
| `infra/keycloak/realm-contract.json` | `data_products` section; platform admin and `srv-starrocks` described per product |
| `infra/rustfs/bootstrap-buckets.py` | `--product`, `--inventory`, `--remove`, `--purge-data`, `--dry-run` |
| `infra/rustfs/bootstrap-policies.py` | Matrix from the files; product policies converge; `role-platform-admin` spans all buckets; `--remove` |
| `infra/polaris/bootstrap-default-catalogs.py` → `bootstrap-catalogs.py` | Allowed locations converge; product namespaces in their bucket; inventory and remove |
| `infra/polaris/bootstrap-product-authorization.py` | Namespace-scoped grants; add then revoke; `none` deletes the catalog role; remove; dry run |
| `infra/polaris/oidc.properties` | `ALLOW_NAMESPACE_CUSTOM_LOCATION` and the group pattern filter |
| `infra/polaris/reconcile-keycloak-groups.py` | Groups from the files; platform admin gets every owner role; missing groups count as empty; invalid files change nothing |
| `infra/polaris/reconciler/Dockerfile`, `run.sh`, `compose.core.yml` | PyYAML 6.0.3, product model in the image, read-only mount of `data-products/` |
| `infra/starrocks/starrocks_common.py` | Model built from the files (roles, scopes, MV databases); `require_products` |
| `infra/starrocks/bootstrap-starrocks.py` | Database-scoped grants; `ALL TABLES IN DATABASE` parsing; `--product`, `--inventory`, `--remove`, `--purge-data` |
| `infra/starrocks/reconcile-starrocks-users.py` | Missing groups count as empty; invalid files refuse |
| `infra/jupyter/hub/lakehouse_policy.py`, `jupyterhub_config.py`, `compose.jupyter.yml` | Admission from the mounted files at each sign-in (`LakehouseOAuthenticator.check_allowed`), failing closed |
| `infra/airflow/airflow_sso_roles.py`, `airflow_oauth_security_manager.py`, `webserver_config.py`, `compose.airflow.yml` | Group-to-role mapping from the mounted files at sign-in; identity `AUTH_ROLES_MAPPING` |
| `infra/jenkins/casc/jenkins.yaml`, `compose.jenkins.yml`, `scripts/setup/prepare-runtime.py` | The template holds the static entries; the rendered file is mounted; rendered at every start |
| `scripts/bootstrap-default-product.sh` | Every product file; records the applied state |
| `scripts/operations/reset-lakehouse.py` | Also deletes `.runtime/state` |
| `scripts/verify/role-matrix.py`, `infra/spark-bootstrap/verify_role_matrix.py` | `--product`; expected access from the file; smoke-table setup for new products; isolation checks |
| `README.md` | Data products, Adding users, the updated access model, scripts, limitations |
| Existing tests | Keycloak, RustFS, StarRocks, JupyterHub, Airflow, Jenkins, and reset contracts updated to the product model |

## Test results (contract suite)
`PYTHONPATH=infra/jupyter/hub python3 -m pytest -q tests`: **327 passed, 1 skipped, 1 failed**.

The failure is the known Airflow developer-role drift: the test expects `Admin` and the mapping is `User`. It predates this intent and is listed in the open follow-ups. Every Compose module combination renders.

## Fixes made during Build and Test
| Finding (live) | Fix |
|---|---|
| `airflow-init` failed: `webserver_config` imports `airflow_sso_roles`, but the product model is mounted only into the API server | `data_products` is imported lazily, and failures fail closed to the platform administrator |
| Polaris dry run reported "would bind" for existing bindings | Bindings are always looked up; only the write is skipped in a dry run |
| A non-admin got a raw "HTTP 403" | `require_platform_admin` names the missing admin rights |
| A removal's Polaris sync tried to give `platform-admin` the deleted owner role (HTTP 404) | Missing product groups are also removed from the platform administrator's owner roles |
| A removal's StarRocks sync refused because the product's roles were already dropped | Roles of products whose groups are gone are not required (`MISSING_GROUPS`) |
| The role matrix could not clean up after the writer was reduced to read in prod | Setup and cleanup use the writer, or else the owner, whichever writes every environment |
| Suites depended on which product files exist locally | `tests/conftest.py` gives each session a product directory holding only `default` |

Contract suite after the fixes: **332 passed, 1 skipped, 1 failed** (the known Airflow drift).
