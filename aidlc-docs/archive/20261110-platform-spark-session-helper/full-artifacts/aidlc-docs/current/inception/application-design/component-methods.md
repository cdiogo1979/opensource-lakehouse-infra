# Component Methods — Platform Spark Session Helper

Signatures and purpose; rules in Functional Design.

## C1 `lakehouse_spark` (platform)
| Function | Purpose |
|---|---|
| `create_spark_session(app_name="lakehouse-user", catalog=None) -> SparkSession` | `catalog` defaults to `LAKEHOUSE_POLARIS_CATALOG`, else `lakehouse` (today's notebook example keeps working) |
| `select_token_source(environ) -> str` | `airflow` or `jupyter`, or a `RuntimeError` naming what is missing |
| `catalog_settings(default_catalog) -> dict[str, str]` | every Spark setting the session gets (catalogs, default catalog, redaction); pure, for tests |
| `CATALOGS`, `REDACTION_REGEX` | the platform values |

## C6 `job_runtime` (repository)
| Function | Purpose |
|---|---|
| `start_spark_job(app_name, argv=None) -> (spark, config)` | Jupyter: environment from `LAKEHOUSE_ENVIRONMENT` (default `dev`), the shared config; Airflow: `parse_args(argv)`, product from `LAKEHOUSE_PRODUCT`; then `create_spark_session(f"{env}-{app_name}", config["catalog_name"])` |
| `jupyter_environment(environ) -> str` | `dev`, `uat` or `prod`, or a `ValueError` |

## C7 `cli` (repository)
| Function | Purpose |
|---|---|
| `parse_args(argv=None)` | unchanged |
| `task_args(argv=None) -> list[str]` | Airflow: the arguments after `--`; Jupyter: the notebook's `TASK_ARGS`, else `[]` |
| `parse_task_args(declaration, argv=None) -> Mapping[str, str | None]` | the declared names and their string values or defaults; Jupyter widgets first, then `TASK_ARGS` |
| `TaskArgumentError(ValueError)` | every structural problem and the usage, raised in Jupyter; Airflow prints it and exits 2 |

## C8, C9 (repository, run with `%run`)
| Script | Defines in the notebook |
|---|---|
| `jupyter_environment_resolver.py` | `spark`, `config`, `repository_root` |
| `jupyter_input_widget_helper.py` | `LAKEHOUSE_WIDGETS` (name → `ipywidgets.Text`), shown as a vertical box |
