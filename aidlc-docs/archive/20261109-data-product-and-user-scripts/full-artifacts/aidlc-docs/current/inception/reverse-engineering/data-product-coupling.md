# How the `default` Data Product Is Wired In

The platform has exactly one product, `default`. Its name is a constant in 22 files.

| Component | What exists for `default` | Where | How it is keyed |
|---|---|---|---|
| Keycloak | Groups `role-default-{owner,developer,analyst,writer}`; Polaris client roles of the same names; the writer user `srv-default-writer`; `srv-starrocks` in `role-default-writer` | `infra/keycloak/bootstrap-realm.py` (`ROLES`), `realm-contract.json`, `bootstrap-users.json` | constants |
| Polaris | Catalogs `lakehouse`, `lakehouse_uat`, `lakehouse_dev` (one per environment). Each catalog's storage base is the product bucket, `s3://bucket-default/lakehouse/`. Namespaces `default_lh`, `default_lhuat`, `default_lhdev`. Grants are **catalog-wide** (owner `CATALOG_MANAGE_*`; others read or write the whole catalog) | `infra/polaris/bootstrap-default-catalogs.py`, `bootstrap-product-authorization.py` | constants |
| Polaris OIDC | Only `role-default-(developer\|analyst\|owner\|writer)` may become principal roles (a regex filter) | `infra/polaris/oidc.properties` | a regex fixed to `default` |
| RustFS | Buckets `bucket-default{,-uat,-dev}`; one policy per group naming those buckets | `infra/rustfs/bootstrap-buckets.py`, `bootstrap-policies.py` | constants |
| StarRocks | Catalogs mirroring Polaris; roles `role_default_*`; MV databases `default_lh*` | `infra/starrocks/starrocks_common.py` | constants |
| JupyterHub | Admits `role-default-developer`, `role-default-analyst`, `role-platform-admin` | `infra/jupyter/hub/lakehouse_policy.py`, `jupyterhub_config.py` | constants |
| Airflow | UI role mapping per `role-default-*` group; the broker requires `role-default-writer` in the writer token | `infra/airflow/airflow_sso_roles.py`, `webserver_config.py`, `infra/airflow-token-broker/app.py` | constants |
| Jenkins | Permission matrix for `role-default-{owner,developer,analyst}` | `infra/jenkins/casc/jenkins.yaml` | constants |
| Reconcilers | The Polaris and StarRocks group reconcilers iterate the fixed `default` groups | `infra/polaris/reconcile-keycloak-groups.py`, `infra/starrocks/reconcile-starrocks-users.py` | constants |
| Verifiers | Role-matrix and STS checks use the `default` names | `scripts/verify/*`, `infra/spark-bootstrap/*` | constants |

## What this means for a second product
1. **Catalog model**:
   - Catalogs are per environment, and a catalog's storage base points at the product bucket.
   - A new product either gets its **own catalogs** (`<product>`, `<product>_uat`, `<product>_dev`, each on its own bucket), so today's catalog-wide grants still isolate it.
   - Or it shares the environment catalogs with its own namespace. That needs the extra bucket in each catalog's allowed locations, **namespace-scoped grants** in place of catalog-wide ones, and a change to how `default` itself is granted.
2. **Polaris OIDC filter**: must accept the new product's groups. The regex is fixed to `default`, so a change to `oidc.properties` and a Polaris restart are needed.
3. **Keycloak**: new groups and Polaris client roles per product. `platform-admin` maps to owner in each product.
4. **Every bootstrap is single-product today.** The new script needs product-parameterized versions of the bucket, policy, catalog, grant, and StarRocks steps, and the reconcilers must learn every product's groups.
5. **Apps**: JupyterHub admission, Airflow role mapping, and the Jenkins matrix are fixed to the `default` groups. Whether new products' groups get access there is a scope decision.
6. **Writer and service identities**: `srv-default-writer` and the broker check are `default`-specific. A writer identity per product is a scope decision.

## A new user
- **Today**: users are created only from `infra/keycloak/bootstrap-users.json` (the five bootstrap users). There is no generic "add a user" command.
- **Downstream**: a new Keycloak user in a product group is picked up by the Polaris reconciler (principal) and the StarRocks reconciler (JWT user) within five minutes, or immediately with the on-demand commands.
