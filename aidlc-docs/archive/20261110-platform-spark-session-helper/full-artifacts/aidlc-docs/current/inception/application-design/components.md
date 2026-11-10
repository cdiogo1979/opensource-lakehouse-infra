# Components — Platform Spark Session Helper

| # | Component | Location | Status | Responsibility |
|---|---|---|---|---|
| C1 | Platform session module `lakehouse_spark` | `infra/workload-python/python/lakehouse_spark.py` (moved from `infra/jupyter/singleuser/`) | changed | `create_spark_session(app_name, catalog)`: token source, the three Polaris catalogs, redaction, the existing-session rule. The only place catalog settings exist |
| C2 | Hub broker client `lakehouse_broker_client` | `infra/workload-python/python/lakehouse_broker_client.py` (moved, unchanged) | moved | The Jupyter user's token from the Hub broker |
| C3 | Platform import path | `infra/workload-python/lakehouse-platform.pth` → `/opt/lakehouse/venv/lib/python3.10/site-packages/` | new | Adds `/opt/lakehouse/python` to the venv's `sys.path`, in both images and whatever `PYTHONPATH` says (Airflow run containers set only the bundle) |
| C4 | Spark defaults | `infra/jupyter/singleuser/spark-defaults.conf` (both images) | changed | Only Iceberg extensions and redaction; the catalog lines move to C1 |
| C5 | Images | `infra/spark-runtime/Dockerfile`, `infra/jupyter/singleuser/Dockerfile` | changed | Copy C1, C2, C3 to the same paths; Jupyter's `PYTHONPATH` drops `/opt/lakehouse`. The lock gains `ipywidgets` 8.1.9 (CR-3); JupyterLab gains `jupyterlab_widgets` 3.0.17 |
| C6 | Repository `notebooks/common/job_runtime.py` | workload repository | changed | `start_spark_job(app_name, argv=None)`: environment and config, then `lakehouse_spark.create_spark_session` |
| C7 | Repository `notebooks/common/cli.py` | workload repository | changed | `parse_args` (unchanged), `task_args` (Jupyter: `TASK_ARGS`), `parse_task_args(declaration, argv=None)` (CR-2, CR-3) |
| C8 | Repository `notebooks/common/jupyter_environment_resolver.py` | workload repository | new (CR-1; replaces `notebooks/workload/jupyter_helper.py`) | Run with `%run`: repository root, environment, application name, `spark` and `config` into the notebook |
| C9 | Repository `notebooks/common/jupyter_input_widget_helper.py` | workload repository | new (CR-3) | Run with `%run` after `WIDGET_LIST`: one text widget per name, kept in the notebook's `LAKEHOUSE_WIDGETS` |
| C10 | Entry points, docs, tests | workload repository | changed | `%run` lines, `generate_tpch.py` on `parse_task_args`, `count_sample_rows.py` guard removed, README, AGENTS.md, tests |

**Unchanged**: the DAG factory, the Java token provider, `config_loader.py`, the smoke bootstrap (it sets all its catalog keys itself, with `oauth2`).
