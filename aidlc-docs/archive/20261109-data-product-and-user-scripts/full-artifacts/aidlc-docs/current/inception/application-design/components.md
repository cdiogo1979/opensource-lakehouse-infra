# Components — Data Product and User Scripts

No new service or container. One new shared module; the existing component scripts become product-driven; three operator scripts sit on top.

| # | Component | Location | New or changed | Responsibility |
|---|---|---|---|---|
| C1 | **Product model** | `infra/products/data_products.py`, `infra/products/template.yaml` | New | Load, validate, and template product files; derive names; collision and locked-name checks; the applied-names state. Pure, with no network calls |
| C2 | **Product configuration files** | `data-products/<name>.yaml`, starting with `default.yaml` | New | The whole configuration of each product (FR-1). The single source for every component |
| C3 | **Keycloak identity** | `infra/keycloak/product-identity.py` (new); `bootstrap-realm.py` (changed) | Changed | Product groups and Polaris client roles, the `role-platform-admin` owner mappings, `srv-starrocks` writer membership, and the writer user. `bootstrap-realm.py` keeps the realm and clients and stops hard-coding `default` |
| C4 | **Keycloak user creation** | `infra/keycloak/create-user.py` (new) | New | Create one enabled user with no groups (FR-9) |
| C5 | **RustFS storage** | `infra/rustfs/bootstrap-buckets.py`, `bootstrap-policies.py` | Changed | Buckets and group policies per product. The `role-platform-admin` policy aggregates every product's buckets. Removal empties (only with purge) and deletes buckets and policies |
| C6 | **Polaris catalog and access** | `infra/polaris/bootstrap-default-catalogs.py` → `bootstrap-catalogs.py`; `bootstrap-product-authorization.py`; `oidc.properties` | Changed | Allowed locations in the shared catalogs; namespaces in the product bucket; principal roles and **namespace-scoped** catalog roles; the `default` migration; the server flag and the filter pattern |
| C7 | **StarRocks access** | `infra/starrocks/starrocks_common.py`, `bootstrap-starrocks.py` | Changed | Roles per product with **database-scoped** grants; MV databases; removal |
| C8 | **Reconcilers** | `infra/polaris/reconcile-keycloak-groups.py`, `infra/starrocks/reconcile-starrocks-users.py`, reconciler image | Changed | Group, principal-role, and user mapping across all product files. The image gains pinned PyYAML and a read-only mount of `data-products/` |
| C9 | **App access** | JupyterHub (`lakehouse_policy.py`, `jupyterhub_config.py`); Airflow (`airflow_sso_roles.py`, security manager); Jenkins (`casc/jenkins.yaml` → rendered) | Changed | JupyterHub and Airflow read the mounted product files at each sign-in, so no restart. The Jenkins matrix is rendered from the files into `.runtime/container-mounts/jenkins-casc.yaml`, and Jenkins restarts when it changes |
| C10 | **Operator scripts** | `scripts/operations/create-data-product.sh`, `remove-data-product.sh`, `create-user.sh` | New | Orchestrate C1–C9 (see `services.md`) |
| C11 | **Product bootstrap** | `scripts/bootstrap-default-product.sh` | Changed | Applies every product file after a reset, so all products come back |

## Boundaries kept
- Each component script stays the only writer to its system. The operator scripts call those scripts and never talk to Keycloak, RustFS, Polaris, or StarRocks directly.
- Secrets stay in `.runtime/credentials/`; product files hold paths, never values.
- The Airflow broker and the `lakehouse-writer` client stay `default`-only (C3 A, out of scope).
