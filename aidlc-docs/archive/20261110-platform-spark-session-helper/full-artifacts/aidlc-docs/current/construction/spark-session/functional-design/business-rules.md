# Business Rules — spark-session

## Session (platform `lakehouse_spark`, BR-S)
- **BR-S1 Settings**: for each catalog `c` in `lakehouse`, `lakehouse_uat`, `lakehouse_dev`: `spark.sql.catalog.c` = `org.apache.iceberg.spark.SparkCatalog`, and `.type` `rest`, `.uri` `http://polaris:8181/api/catalog`, `.warehouse` `c`, `.rest.auth.type` `local.lakehouse.spark.auth.LakehouseTokenAuthManager`, `.io-impl` `org.apache.iceberg.aws.s3.S3FileIO`, `.header.Polaris-Realm` `lakehouse`, `.header.X-Iceberg-Access-Delegation` `vended-credentials`. Also `spark.sql.extensions` (Iceberg), `spark.sql.defaultCatalog`, and `spark.redaction.regex` and `spark.sql.redaction.options.regex` = `(?i)secret|password|token|access[.]?key|credential`. No setting holds a token or credential.
- **BR-S2 Default catalog**: the `catalog` argument, else `LAKEHOUSE_POLARIS_CATALOG`, else `lakehouse`; it must be one of the three, otherwise `ValueError`.
- **BR-S3 Token source**:
  - `LAKEHOUSE_TOKEN_PROVIDER=airflow`: `LAKEHOUSE_INITIAL_ACCESS_TOKEN`, `LAKEHOUSE_TOKEN_BROKER_URL`, `LAKEHOUSE_TOKEN_BROKER_CA`, `LAKEHOUSE_RUN_HANDLE` and `LAKEHOUSE_RUN_CAPABILITY` must all be non-empty; otherwise `RuntimeError` naming the missing variables (names only).
  - `LAKEHOUSE_TOKEN_PROVIDER=jupyter`, or unset with `JUPYTERHUB_API_TOKEN` set: the user's token from the Hub broker; the module sets `LAKEHOUSE_TOKEN_PROVIDER=jupyter`, `LAKEHOUSE_INITIAL_ACCESS_TOKEN`, and, when unset, the Hub broker URL and CA.
  - Any other provider value, or neither: `RuntimeError` ("Start Spark from an Airflow run or a JupyterHub server").
- **BR-S4 Existing session**: an active session whose `spark.sql.defaultCatalog` equals the requested catalog is returned unchanged; a different one raises `RuntimeError` ("restart the kernel to switch catalogs"). No new token is requested for a returned session.
- **BR-S5 Application name**: 1 to 100 printable characters; otherwise `ValueError`.
- **BR-S6 `spark-defaults.conf`** keeps only `spark.sql.extensions` and the two redaction settings, with the same values as BR-S1.

## Job start (repository `job_runtime`, BR-J)
- **BR-J1 Context**: Jupyter when `ipykernel` is in `sys.modules`.
- **BR-J2 Jupyter**: environment from `LAKEHOUSE_ENVIRONMENT` (`dev` when unset; `uat`, `prod` allowed; anything else `ValueError`); the clone's `configs/<env>.yml`; `LAKEHOUSE_PRODUCT` is ignored.
- **BR-J3 Airflow and scripts**: `parse_args(argv)` (`--environment`, `--config-dir`); product from `LAKEHOUSE_PRODUCT`.
- **BR-J4 Session**: `create_spark_session(f"{env}-{app_name}", config["catalog_name"])`; a config without `catalog_name` is a `ValueError` naming the key. The config is returned with every key.
- **BR-J5 Removed**: `spark-files`, `LAKEHOUSE_BUNDLE_CONFIG_DIR`, `LAKEHOUSE_CONFIG_DIR`; no catalog, token or redaction settings in the repository.

## Task arguments (repository `cli`, BR-A)
- **BR-A1 Declaration**: a mapping; names `[a-z][a-z0-9_]{0,49}`, distinct after `_` → `-`; spec keys only `required` (bool) and `default` (string); `required: True` with a `default` is invalid. Any problem → `TaskArgumentError` before parsing.
- **BR-A2 Syntax**: `--option value` or `--option=value`. A value may start with `-` only in the `=` form.
- **BR-A3 Structural problems**, all reported together: a token that is not a declared option; a positional token; an option given twice; an option without a value; a required option not given. No value is converted or checked otherwise (CR-2).
- **BR-A4 Sources**:
  - script context: `task_args(argv)` (after `--`);
  - Jupyter: the notebook's `LAKEHOUSE_WIDGETS` when it holds any widget: each widget's text, empty meaning not given; a widget whose name is not declared is a problem. Otherwise the notebook's `TASK_ARGS` (a list of strings, else a problem), parsed as in the script context. Otherwise nothing.
- **BR-A5 Result**: a read-only mapping with every declared name: the given string, else the default, else `None`.
- **BR-A6 Errors**: the message lists every problem, then `usage: <prog> --entity ENTITY [--scale-factor SCALE_FACTOR]` (required first, in declaration order). `<prog>` is the entry point's file name (`sys.argv[0]`, or the notebook from `JPY_SESSION_NAME`). Script context: printed to stderr, exit status 2. Jupyter: `TaskArgumentError` raised.
- **BR-A7 `task_args()`** in Jupyter returns `TASK_ARGS` (validated as in BR-A4) or `[]`; in the script context it is unchanged.

## Widgets (repository `jupyter_input_widget_helper`, BR-W)
- **BR-W1**: acts only under `%run` in a kernel; on import it defines functions only.
- **BR-W2**: `WIDGET_LIST` must be a list of distinct names valid under BR-A1; otherwise `ValueError` and no widget changes.
- **BR-W3**: `LAKEHOUSE_WIDGETS` holds exactly the listed names, in list order: existing widgets keep their text; new ones are empty `Text` widgets labelled with the name; names no longer listed are dropped. The widgets are shown as one vertical box.

## Environment resolver (repository `jupyter_environment_resolver`, BR-R)
- **BR-R1**: acts only under `%run` in a kernel.
- **BR-R2 Root**: the nearest folder at or above the kernel's working directory holding `notebooks/common/job_runtime.py` and a `configs/` folder; none → `FileNotFoundError` ("open the notebook inside a clone of the repository"). The root is put first on `sys.path` once.
- **BR-R3 Name**: the notebook's file stem from `JPY_SESSION_NAME`, else `notebook`.
- **BR-R4**: `spark, config = start_spark_job(name)`; it prints the environment and the config file used, never values.

## Entry points (BR-E)
- **BR-E1** `generate_tpch.py`: declaration `{"entity": {"required": True}, "scale_factor": {"default": "0.01"}}`; `WIDGET_LIST = ["entity", "scale_factor"]` in its Jupyter cell; it keeps its own entity and scale-factor checks (`ValueError` in Jupyter, exit 2 in Airflow).
- **BR-E2** Every entry point runs `%run ../common/jupyter_environment_resolver.py` where it ran `jupyter_helper.py`; `count_sample_rows.py` loses the Airflow guard.
