# Integration Test Instructions

Live, on the local stack. Probes use the scheduler's control token inside the scheduler container and print only status codes, refusal codes, and the token's `preferred_username` and Polaris roles.

| # | Scenario | Steps | Expected |
|---|---|---|---|
| 1 | Bundles from the product files | `./scripts/lakehouse.sh start-airflow` | `default-main` and `default-uat` registered, DAGs `default-main-test_environment` and `default-uat-test_environment`; fingerprint recorded |
| 2 | Broker Viewer identity | `airflow users list` | `lakehouse-broker` with role Viewer only |
| 3 | Writer selection | `POST /v1/runs` for each product DAG; renew; revoke | 201 with the product's writer and only its writer group; renewal keeps the writer; revoke 204 |
| 4 | Refusals | DAG IDs without a product (`dev-...`, `main-...`), an unknown DAG | 403 `unknown_product`, 403 `unknown_dag`; no token |
| 5 | End-to-end run | trigger `default-uat-test_environment` | all tasks succeed (writes only to the dedicated smoke table) |
| 6 | New product with the same repo | `create-data-product.sh --init bttest`, add the `repo` block, `--dry-run`, apply | dry run lists the new bundles; apply recreates Airflow; `bttest-main`/`bttest-uat` DAGs registered; broker gives `srv-bttest-writer` |
| 7 | Idempotent apply | apply `--dry-run` again | "Airflow bundles and writers are unchanged." |
| 8 | Removal | `remove-data-product.sh bttest --dry-run`, then `--yes` | preview lists the remaining bundles; removal recreates Airflow; writer unstaged; its DAGs refused with `unknown_product`; fingerprint back to its earlier value |
