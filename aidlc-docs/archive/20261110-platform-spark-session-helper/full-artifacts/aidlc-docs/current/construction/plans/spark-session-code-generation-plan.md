# Code Generation Plan — spark-session

Unit `spark-session`. Platform code in this workspace; the workload change in the scratchpad clone (branch from `0bc9ecd`), pushed to `main` and `uat` only after approval. Rules: `construction/spark-session/functional-design/business-rules.md`.

## Platform (this workspace)
- [x] **Step 1 — Session module**: move `infra/jupyter/singleuser/{lakehouse_spark,lakehouse_broker_client}.py` to `infra/workload-python/python/`; rewrite `lakehouse_spark.py`: `CATALOGS`, `REDACTION_REGEX`, `catalog_settings`, `select_token_source`, `create_spark_session(app_name, catalog)` (BR-S1 to BR-S5). The broker client is unchanged.
- [x] **Step 2 — Import path**: `infra/workload-python/lakehouse-platform.pth` (`/opt/lakehouse/python`).
- [x] **Step 3 — Spark defaults**: `infra/jupyter/singleuser/spark-defaults.conf` keeps the extensions and redaction only (BR-S6).
- [x] **Step 4 — Widgets in the environment**: `ipywidgets==8.1.9` in `requirements.in`, the lock regenerated with `lock-workload-python.sh`; `jupyterlab_widgets==3.0.17` in `infra/jupyter/singleuser/requirements.txt`.
- [x] **Step 5 — Images**: both Dockerfiles copy `infra/workload-python/python/` to `/opt/lakehouse/python/` and the `.pth` into the venv; Jupyter's `PYTHONPATH` drops `/opt/lakehouse` and the old `COPY` of the two modules goes.
- [x] **Step 6 — Tests**: `tests/jupyterhub/test_unit2_broker_client.py` and `test_unit3_spark_credential_refresh.py` follow the new paths and the new rules; new `tests/workload_env/test_spark_session.py` (BR-S examples with a fake `pyspark`, P1, P2); image contract tests for the `.pth`, the copies, `PYTHONPATH`, `spark-defaults.conf`, the widget pins.
- [x] **Step 7 — README**: the Spark session module in the JupyterHub and workload environment sections; Jupyter widgets.

## Workload repository (scratchpad clone)
- [x] **Step 8 — `notebooks/common/job_runtime.py`**: `start_spark_job`, `jupyter_environment` (BR-J1 to BR-J5).
- [x] **Step 9 — `notebooks/common/cli.py`**: `task_args` (Jupyter `TASK_ARGS`), `parse_task_args`, `TaskArgumentError` (BR-A1 to BR-A7).
- [x] **Step 10 — `notebooks/common/jupyter_environment_resolver.py`** (BR-R, CR-1) and **`jupyter_input_widget_helper.py`** (BR-W, CR-3); remove `notebooks/workload/jupyter_helper.py`.
- [x] **Step 11 — Entry points**: the `%run` lines; `generate_tpch.py` on `parse_task_args` with `WIDGET_LIST` (BR-E1); `count_sample_rows.py` without the guard (BR-E2).
- [x] **Step 12 — Tests**: `tests/workload_foundation/` for `job_runtime` (a fake `lakehouse_spark`), `cli` (examples, P3 to P7), the resolver's root and name rules, the widget helper's list rules, `generate_tpch`'s new argument path.
- [x] **Step 13 — Docs**: README (entry points, Jupyter: environment, widgets, `TASK_ARGS`, the resolver; product folders in Airflow only; layout) and AGENTS.md.

## Documentation
- [x] **Step 14 — `construction/spark-session/code/code-summary.md`**.

## Not in this stage
Image builds, live runs, the Jupyter check and the push are Build and Test.
