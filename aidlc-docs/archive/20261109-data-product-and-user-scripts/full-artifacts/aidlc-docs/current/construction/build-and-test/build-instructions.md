# Build Instructions

1. **Settings and mounts**: `python3 scripts/setup/prepare-runtime.py` merges the Polaris settings (namespace-location flag and group pattern) and renders `.runtime/container-mounts/jenkins-casc.yaml`.
2. **Polaris**: `docker restart lakehouse-local-polaris-1`. This is needed once, for the new settings.
3. **Apps and sync job**:
   - `scripts/lakehouse.sh start` recreates JupyterHub and Jenkins with their new mounts.
   - `scripts/lakehouse.sh start-airflow` rebuilds and recreates Airflow.
   - `docker compose -f compose.core.yml --profile scheduled-reconciliation up -d --build polaris-group-reconciler` rebuilds the sync job (PyYAML and the product model).
4. **`default` migration**: `scripts/operations/create-data-product.sh data-products/default.yaml --admin-password-file <file>`. This replaces the catalog-wide grants with namespace-scoped ones.
