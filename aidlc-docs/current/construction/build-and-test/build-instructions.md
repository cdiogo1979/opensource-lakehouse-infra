# Build Instructions — StarRocks Audit Capture

- **Test environment (host)**: a venv with `tests/requirements-pbt.txt`, PyYAML and `infra/jupyter/hub/requirements.txt` (the Hub suites import JupyterHub and DockerSpawner).
- **Images**: `docker build -t local/lakehouse-spark-runtime:3.5.9_1.10.2 -f infra/spark-runtime/Dockerfile .` and `docker build -t local/lakehouse-jupyter-singleuser:6.1.1-spark -f infra/jupyter/singleuser/Dockerfile .` (both fail the build if `lakehouse_starrocks` or `pymysql` don't import); then `scripts/verify/workload-python-parity.sh`.
- **StarRocks**: `mkdir -p .runtime/starrocks-audit && chmod 700 .runtime/starrocks-audit`; recreate the FE (`docker compose -f compose.core.yml -f compose.starrocks.yml up -d --force-recreate starrocks-fe`) for `fe.conf`, the plugin volume and the package mount; `python3 infra/starrocks/bootstrap-starrocks.py --runtime-only` (capture), then `python3 infra/starrocks/bootstrap-starrocks.py` (grants). `scripts/lakehouse.sh start` does the same.
- **Airflow and JupyterHub**: `scripts/lakehouse.sh start-airflow` (new `LAKEHOUSE_STARROCKS_CA_HOST_PATH`); recreate JupyterHub for its new mount and spawner settings.
- **Known**: `start-airflow`'s final DAG check waits for every bundle to have a DAG; `audit-main` has none until the audit product promotes `uat` to `main`.
