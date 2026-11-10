# Deployment Instructions — Repository rename

Manual steps in this workspace's root, in order. Done on this local stack on 2026-11-10, except step 5.

1. **Product file and images**: with the updated `data-products/default.yaml`, rebuild the images: `./scripts/lakehouse.sh start` (it builds both) — Validation: `Workload Python parity: OK.` from `bash scripts/verify/workload-python-parity.sh`.
2. **Airflow**: `./scripts/lakehouse.sh start-airflow` with no DAG run active (the bundle URL changes, so Airflow is recreated) — Validation: `Verified Bundle default-main: …` and `default-uat: …`.
3. **Containers `start` doesn't recreate** (only after moving the workspace folder): `docker compose -f compose.core.yml up -d --no-deps --force-recreate keycloak-db polaris-db`; `docker compose -f compose.core.yml --profile scheduled-reconciliation up -d --no-deps --force-recreate polaris-group-reconciler`; `airflow-postgres` the same way with `-f compose.airflow.yml --profile airflow` (its interpolation needs placeholders for `AIRFLOW_UID`, `LAKEHOUSE_BROKER_CA_HOST_PATH`, `LAKEHOUSE_BUNDLE_CONFIG_LIST`, `LAKEHOUSE_BUNDLE_HOST_ROOT`, which that service doesn't use). Volumes are kept. — Validation: every service healthy; no container mount under the old folder.
4. **Checks**: UAT `default-uat-test_environment` and `default-uat-generate_tpch`; Jenkins `default_ci` both branches.
5. **Users**: `git remote set-url origin https://github.com/cdiogo1979/opensource-lakehouse-sample-dp.git` in local clones; Jupyter clones in `~/work/opensource-lakehouse-sample-dp`; restart notebook servers.
- **Failure handling**: GitHub redirects the old repository URL, so the previous product file keeps working; containers can be recreated again from the workspace folder.
