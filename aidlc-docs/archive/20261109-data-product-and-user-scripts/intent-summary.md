# Intent Summary: Data Product and User Scripts

## Intent
Data Product and User Scripts (`20261109-data-product-and-user-scripts`)

## Objective
Operator scripts to create, change, and remove data products from per-product YAML files, and to create users; the platform becomes multi-product with namespace- and database-scoped access in shared catalogs.

## Date
2026-11-09

## Scope
Included: per-product YAML files in data-products/ (default included); create-data-product.sh (--init, apply, dry run), remove-data-product.sh (default refused, purge, resumable), create-user.sh; Keycloak, RustFS, Polaris, StarRocks, reconcilers, JupyterHub, Airflow, and Jenkins driven by the files; namespace-scoped Polaris and database-scoped StarRocks grants including the default migration; platform-admin sign-in for the scripts; role matrix per product with isolation. Excluded: Airflow writer workloads for other products, per-product Airflow/Jenkins permissions, the BI token intent. Extensions off.

## Units / workstreams
data-product-provisioning

## Major requirements
- FR-1 per-product YAML configuration files (CR-1), at the repository root (CR-3); names locked once applied
- FR-2 create-data-product.sh: --init, then apply a file; converges every component including revokes
- FR-3..FR-8 Keycloak groups and writer user, RustFS buckets and policies, Polaris namespaces and namespace-scoped grants, StarRocks database-scoped roles and MV databases, app mappings, and reconcilers for every product
- FR-9 create-user.sh: one user, no groups, default ChangeM3!
- FR-11 remove-data-product.sh: default refused, data check with --purge-data, typed confirmation, backup, resumable (CR-1)
- CR-2 developers author StarRocks MVs in dev; CR-4 scripts sign in to Keycloak as a platform administrator and refuse others

## Architecture and design decisions
- Shared environment catalogs with a bucket per product; Polaris needs the server-wide ALLOW_NAMESPACE_CUSTOM_LOCATION flag (the per-catalog property is ignored, probed)
- Polaris OIDC filter is the fixed pattern role-<token>-<role>, so new products need no Polaris restart
- JupyterHub and Airflow read the mounted product files at each sign-in and fail closed; Jenkins CasC is rendered from the files and Jenkins restarts only on change
- NAMESPACE_LIST at catalog level is accepted: namespace names are visible across products, contents are not
- Product roles never create, drop, or relocate namespaces; additions run before revocations; extras on managed roles are revoked and reported
- Platform admin is owner of every product through Keycloak client roles; it keeps catalog-wide manage in StarRocks

## Implementation decisions
- infra/products/data_products.py is the single model, copied into the reconciler image and mounted into JupyterHub and Airflow
- Each component script keeps ownership of its system and takes --product, --dry-run, and where relevant --inventory, --remove, --purge-data
- infra/keycloak/keycloak_products.py holds the per-product Keycloak logic for bootstrap-realm.py and product-identity.py
- The Jenkins render rewrites the mounted file in place because single-file bind mounts keep their inode
- tests/conftest.py gives each test session a product directory holding only default

## Deviations
- Requirements changed four times during the intent (CR-1..CR-4), each recorded in requirements.md and the audit
- FR-2's planned restarts of JupyterHub, Airflow, and Polaris per product were replaced by file reads and the filter pattern (AD-Q2, AD-Q3)
- Seven defects found in Build and Test were fixed with regression tests (Airflow init import, removal-time reconciles, verifier cleanup role, dry-run bindings, admin refusal message, test isolation)

## Verification
See construction/build-and-test/build-and-test-summary.md. Default migration with an identical role matrix and converged Polaris and StarRocks; a sales product created, verified with isolation both ways, edited and reapplied, removed (refused with data, purged, resumed); user creation with refusals; app mappings in running containers; sign-in verifiers (Jenkins 8/9, known missing CI job). Suite 332 passed, 1 skipped, 1 known Airflow drift failure. Not run: interactive browser sign-ins of a new product's users.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/starrocks-sql-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/jenkins-ci-access.md

## Superseded decisions
- Catalog-wide Polaris grants per role (owners CATALOG_MANAGE_*, writers NAMESPACE_CREATE) replaced by namespace-scoped grants; see archive requirements FR-5 and business-rules BR-2
- Catalog-wide StarRocks grants (including CREATE DATABASE) replaced by database-scoped grants
- Static Jenkins matrix and static JupyterHub/Airflow group lists replaced by product-file driven mappings
- bootstrap-default-catalogs.py renamed bootstrap-catalogs.py; infra/data-products moved to data-products/ (CR-3)
- Developer MV level read/read/read replaced by read/read/author (CR-2)
- Operator Keycloak access through the master admin replaced by platform-admin sign-in in the lakehouse realm for the operator scripts (CR-4)

## Archived artifacts
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/aidlc-docs/current/compaction/20261109-data-product-and-user-scripts/manifest.json
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/starrocks-sql-access.md
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/jenkins-ci-access.md
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/data-products/default.yaml
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/products/data_products.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/products/template.yaml
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/products/render_jenkins.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/products/product-cli.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/products/__init__.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/scripts/operations/create-data-product.sh
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/scripts/operations/remove-data-product.sh
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/scripts/operations/create-user.sh
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/scripts/operations/lib/data-products.sh
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/scripts/operations/reset-lakehouse.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/scripts/bootstrap-default-product.sh
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/scripts/setup/prepare-runtime.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/scripts/verify/role-matrix.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/spark-bootstrap/verify_role_matrix.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/keycloak/keycloak_products.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/keycloak/product-identity.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/keycloak/create-user.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/keycloak/bootstrap-realm.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/keycloak/realm-contract.json
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/rustfs/bootstrap-buckets.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/rustfs/bootstrap-policies.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/polaris/bootstrap-catalogs.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/polaris/bootstrap-product-authorization.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/polaris/oidc.properties
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/polaris/reconcile-keycloak-groups.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/polaris/reconciler/Dockerfile
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/polaris/reconciler/run.sh
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/starrocks/starrocks_common.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/starrocks/bootstrap-starrocks.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/starrocks/reconcile-starrocks-users.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/jupyter/hub/lakehouse_policy.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/jupyter/hub/jupyterhub_config.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/airflow/airflow_sso_roles.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/airflow/airflow_oauth_security_manager.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/airflow/webserver_config.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/infra/jenkins/casc/jenkins.yaml
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/compose.core.yml
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/compose.jupyter.yml
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/compose.airflow.yml
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/compose.jenkins.yml
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/README.md
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/tests/conftest.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/tests/products
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/tests/keycloak/test_product_identity.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/tests/rustfs/test_product_storage.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/tests/polaris/test_product_catalogs_and_grants.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/tests/polaris/test_reconciler_products.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/tests/starrocks/test_product_access.py
- aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/tests/operations/test_data_product_scripts.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261109-data-product-and-user-scripts/full-artifacts/`
