# Deployment Instructions — Platform Spark session helper

Manual commands in this workspace's root, in this order. Carried out on this local stack on 2026-11-10, except step 5 for every user.

## 1. Rebuild the Spark runtime image
- **Prerequisites**: Docker; network access to PyPI.
- **Execution**: `docker build -t local/lakehouse-spark-runtime:3.5.5_1.10.2 -f infra/spark-runtime/Dockerfile .` (also by `./scripts/lakehouse.sh start` and `start-airflow`).
- **Validation**: `OK: Python 3.10, 56 locked package(s)`; the import check of `lakehouse_spark` passes.
- **Failure handling**: the previous image stays tagged until a build succeeds.

## 2. Rebuild the Jupyter single-user image
- **Prerequisites**: step 1.
- **Execution**: `docker build -t local/lakehouse-jupyter-singleuser:6.1.1-spark -f infra/jupyter/singleuser/Dockerfile .`
- **Validation**: the same lock check; the import check of `lakehouse_spark`, `lakehouse_broker_client`, `ipywidgets`.

## 3. Check parity
- **Execution**: `bash scripts/verify/workload-python-parity.sh` → `Workload Python parity: OK.`

## 4. Check compatibility before the workload update (when deploying fresh)
- **Execution**: trigger `default-uat-test_environment` and `default-uat-generate_tpch` with the previous workload code.
- **Validation**: 8/8 and 13/13. Airflow itself needs no restart: run containers use the rebuilt image.

## 5. Workload repository and users
- **Workload**: `main` and `uat` at `42de0f3` (already pushed). Airflow picks it up within about 5 minutes; Jenkins builds both branches.
- **Users**: **File → Hub Control Panel → Stop My Server**, then **Start My Server**; `git pull` in the clone; run the Initialization section (restart the kernel after the first install).
- **Validation**: UAT 8/8 and 13/13 on the new commit; `default_ci` SUCCESS; in Jupyter, the resolver prints `Lakehouse environment dev: …/configs/dev.yml`.
- **Failure handling**: revert the workload commits on `main` and `uat`; the new images also run the previous workload code (step 4).
