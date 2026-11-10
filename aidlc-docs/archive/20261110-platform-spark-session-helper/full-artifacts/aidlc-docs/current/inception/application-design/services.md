# Services and Orchestration — Platform Spark Session Helper

No new service.
1. **Airflow run**: `spark-submit` runs an entry point with the venv's Python; the venv's `.pth` makes `lakehouse_spark` importable; `start_spark_job` loads `configs/<product>/<env>.yml` or `configs/<env>.yml` from `/opt/lakehouse-bundle/configs` and calls the platform with `catalog_name`. Task arguments come from the workflow's `args`.
2. **Jupyter notebook**: optional `%env LAKEHOUSE_ENVIRONMENT=uat`; optional `WIDGET_LIST = [...]` and `%run ../common/jupyter_input_widget_helper.py`; `%run ../common/jupyter_environment_resolver.py` gives `spark` and `config`; the job's code calls `parse_task_args(...)`, which reads the widgets (or `TASK_ARGS`).
3. **Delivery order**: platform images first (the current repository code keeps its own catalog settings and still imports `lakehouse_broker_client` in Jupyter, now through the `.pth`), then the repository change.
