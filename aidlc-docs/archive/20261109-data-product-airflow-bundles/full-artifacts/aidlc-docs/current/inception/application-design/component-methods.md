# Component Methods — Data Product Airflow Bundles

## C1 Product model
- `Repo(url, prod_branch, uat_branch)`; `Product.repo: Repo | None`.
- `bundle_names(product) -> {"prod": f"{name}-main", "uat": f"{name}-uat"}`.
- `DAG_ID_PATTERN = ^([a-z][a-z0-9]{1,19})-(main|uat)-(.+)$`.
- `product_for_dag_id(dag_id) -> (product, env) | None`.

## C2 Bundle list
- `bundle_config(products) -> list[dict]`: deterministic, product order then prod/uat.
- `validate(configs, expected=None)`: shape rules; equal to `expected` when given.

## C3 Writer staging
`stage(products)` writes `writers.json` plus `<username>-password` copies (0644 in the 0700 mount directory, like other staged secrets) for products with a repo. It removes staged files of products without one, and returns a fingerprint.

## C4 Broker
| Method | Purpose |
|---|---|
| `load_writers(path)` | Product → `Writer(username, group, password)` |
| `resolve_product(dag_id)` | Parse the DAG ID, or refuse `unknown_product` |
| `verify_bundle(dag_id, product, env)` | Airflow API check, with the Viewer token cached until near expiry; refuse `bundle_mismatch`; Airflow unreachable gives `service_unavailable` |
| `_issue_token(writer)` | Password grant on `lakehouse-writer` for that writer; check `preferred_username` and the writer group in the role claim |
| `register_run` / `renew_run_token` | As today; the registration remembers its product so renewals use the same writer |

## C5 `ensure-broker-viewer.py`
Create or update `lakehouse-broker` (Viewer) from `AIRFLOW_BROKER_VIEWER_PASSWORD_FILE`; never prints the password.

## C6 Lifecycle
- `airflow_bundles_changed() -> bool` compares the fingerprint of (bundle list, writer set) with `.runtime/state/airflow-bundles.json`.
- `apply_airflow(dry_run, no_restart)` in the operator scripts: if Airflow is running and something changed, run `scripts/lakehouse.sh start-airflow`, which regenerates, validates, recreates, and verifies; otherwise print what would change.

## C8 Workload patch (in `opensource-lakehouse`)
- `identity_for_bundle(dags_dir)`:
  - `<p>-main` gives `(f"{p}-main", "prod")` and `<p>-uat` gives `(f"{p}-uat", "uat")`
  - the legacy names keep their old mapping
  - anything else gives `("dev", "dev")`
- `product_for_bundle(dags_dir) -> str` (`default` for legacy names).
- `load_environment_config(environment, config_dir, product)`: `configs/<product>/<env>.yml`, falling back to `configs/<env>.yml`.
