# Components — Data Product Airflow Bundles

| # | Component | Location | Change | Responsibility |
|---|---|---|---|---|
| C1 | **Product model** | `infra/products/data_products.py`, `template.yaml`, `data-products/default.yaml` | Changed | Optional `repo: {url, prod_branch, uat_branch}`, validated. Bundle names `<name>-main` and `<name>-uat`. The writer is the product's `writer_user` |
| C2 | **Bundle list** | `scripts/setup/airflow-bundle-config.py`, `infra/airflow/validate-bundle-config.py` | Changed | Generate the GitDagBundle list from the product files. The validator checks its shape (in the image) and, with `--host-paths`, equality with the files |
| C3 | **Broker writer set** | `scripts/setup/stage-airflow-writers.py` (new); `compose.airflow.yml` | New | Stage `.runtime/container-mounts/airflow-writers/` (`writers.json`: product → writer username, writer group, password file name; plus the password files) for the broker only |
| C4 | **Writer token broker** | `infra/airflow-token-broker/app.py` | Changed | Holds every product writer; maps the DAG ID to a product; checks the DAG's bundle through the Airflow API as `lakehouse-broker` (Viewer); issues and renews tokens for that product's writer; refuses mismatches |
| C5 | **Broker's Airflow identity** | `infra/airflow/ensure-broker-viewer.py` (new; run by `airflow-init`); `prepare-runtime.py` / `provision-airflow-secrets.sh` | New | Local FAB user `lakehouse-broker`, role Viewer, password from a protected file; created or updated idempotently |
| C6 | **Lifecycle and operators** | `scripts/lakehouse.sh` (`prepare_airflow_environment`, `start-airflow`); `scripts/operations/{create,remove}-data-product.sh`, `lib/data-products.sh` | Changed | Generate the bundle list, stage writers, and recreate Airflow when the bundle list or writer set changed (fingerprint in `.runtime/state/airflow-bundles.json`) |
| C7 | **DAG verifier** | `scripts/verify/airflow-dags.sh` | Changed | Expect each product's `<name>-main`/`<name>-uat` bundles. DAG checks are reported per bundle, since IDs depend on the workload patch |
| C8 | **Workload patch** | delivered as `deploy/opensource-lakehouse.patch` (not applied here) | New | `dags/dag_defaults.py`: bundle `<product>-main`/`-uat` gives prefix = bundle name and environment prod/UAT. Product configs: `configs/<product>/<env>.yml` with a fallback to `configs/<env>.yml` |
