# Unit (Contract) Test Instructions

```sh
PYTHONPATH=infra/jupyter/hub python3 -m pytest -q tests
```

- **Isolation**: `tests/conftest.py` gives each test session a private product directory holding only `default.yaml`, so results do not depend on the local `data-products/`.
- **New suites**:
  - `tests/products`: model, template, collisions, locked names, state, lock
  - `tests/keycloak/test_product_identity.py`: product identities, create-user, platform-admin sign-in
  - `tests/rustfs/test_product_storage.py`: policies, buckets, purge
  - `tests/polaris/test_product_catalogs_and_grants.py`: allowed locations, namespaces, grant plans, the `default` migration, add-before-revoke order, OIDC filter, role-matrix spec
  - `tests/polaris/test_reconciler_products.py`: sync image and mount, Build and Test regressions
  - `tests/starrocks/test_product_access.py`: database-scoped grants, removal, retired roles
  - `tests/operations/test_data_product_scripts.py`: bash 3.2 syntax, usage, refusals, step order, product CLI
- **Result**: 332 passed, 1 skipped, 1 failed. The failure is the known Airflow developer-role drift (`test_approved_groups_map_to_exact_airflow_roles` expects `Admin`; the mapping is `User`). It predates this intent and is in the open follow-ups.
