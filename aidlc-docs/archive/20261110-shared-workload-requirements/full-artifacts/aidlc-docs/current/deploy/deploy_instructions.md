# Deployment Instructions — Shared workload requirements

All steps are manual commands in this workspace's root. On this local stack they were carried out on 2026-11-10 during Build and Test. Repeat them on another copy of the stack in this order.

## 1. Rebuild the Spark runtime image
- **Prerequisites**: Docker; network access to PyPI and the base image registry.
- **Execution**: `docker build -t local/lakehouse-spark-runtime:3.5.5_1.10.2 -f infra/spark-runtime/Dockerfile .` (also done by `./scripts/lakehouse.sh start` and `start-airflow`).
- **Validation**: the build prints `OK: Python 3.10, 53 locked package(s) at their locked versions`.
- **Failure handling**: a lock mismatch fails the build; regenerate the lock with `scripts/setup/lock-workload-python.sh` only if `requirements.in` changed. The previous image stays tagged until a build succeeds.

## 2. Rebuild the Jupyter single-user image
- **Prerequisites**: step 1 (it copies `/opt/spark` from the runtime image); network access to conda-forge, PyPI and Ubuntu's archive.
- **Execution**: `docker build -t local/lakehouse-jupyter-singleuser:6.1.1-spark -f infra/jupyter/singleuser/Dockerfile .` (also done by `./scripts/lakehouse.sh start` when Jupyter is enabled).
- **Validation**: the same build check line.

## 3. Check parity
- **Execution**: `bash scripts/verify/workload-python-parity.sh`
- **Validation**: `Workload Python parity: OK.`
- **Failure handling**: stop; rebuild the image the verifier names.

## 4. Apply the Airflow changes
- **Prerequisites**: no running DAG runs: the bundle `subdir` change (CR-6) recreates the Airflow containers, and the broker image changes (CR-3).
- **Execution**: `./scripts/lakehouse.sh start-airflow`
- **Validation**: `Verified Bundle default-main: ...` and `Verified Bundle default-uat: ...`; `airflow tasks list <dag_id>` in the scheduler shows `install_requirements`; the DAG processor log lists only `lakehouse.py` per bundle.
- **Failure handling**: restore the previous `infra/products/data_products.py` and `infra/airflow/validate-bundle-config.py` (without `subdir`) and rerun `start-airflow`.

## 5. Recreate Jenkins for the lock mount
- **Execution**: `docker compose -f compose.core.yml -f compose.jupyter.yml -f compose.jenkins.yml -f compose.starrocks.yml up -d --no-deps jenkins` (use the module files that `.env` enables), or `./scripts/lakehouse.sh start`.
- **Validation**: `docker exec lakehouse-local-jenkins-1 ls /opt/lakehouse/workload-python` lists `requirements.lock` and `workload_python.py`.

## 6. Restart the JupyterHub (only if it predates the current `infra/products/data_products.py`)
- **Execution**: `docker restart lakehouse-local-jupyterhub-1`
- **Validation**: developers and analysts can sign in (the Hub log has no "Data product files are unusable").

## 7. Users restart their Jupyter servers
- **Action**: each user, **File → Hub Control Panel → Stop My Server**, then **Start My Server**.
- **Validation**: the Launcher shows only "Lakehouse (Python 3.10)"; `git --version` works in a terminal.

## 8. Post-deployment runs
- **Execution**: trigger `default-uat-generate_tpch` in Airflow; let Jenkins `default_ci` build `main` and `uat` (or **Scan Multibranch Pipeline Now**).
- **Validation**: 13/13 tasks; `install_requirements` logs `Installed: duckdb==1.5.6`; CI shows `requirements.txt resolves against the platform lock`.
