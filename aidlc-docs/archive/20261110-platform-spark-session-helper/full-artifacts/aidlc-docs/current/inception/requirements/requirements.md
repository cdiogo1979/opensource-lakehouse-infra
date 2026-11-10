# Requirements — Platform Spark Session Helper

## Intent Analysis
- **Request**: the remaining items of the 2026-11-10 `notebooks/common` analysis: a platform-owned Spark session helper, and the workload helper fixes.
- **Type**: platform enhancement plus a workload-repository refactoring, brownfield.
- **Scope**: this workspace (both images, the session module, tests, README) and `cdiogo1979/opensource-lakehouse` (`notebooks/common`, `jupyter_helper.py`, two entry points, docs, tests).
- **Complexity**: moderate. **Depth**: standard.
- **Answers**: `requirement-verification-questions.md` (Q1 to Q6).

## Functional Requirements

### FR-1 One platform Spark session module (Q1 A)
- **Module**: `lakehouse_spark`, owned by this workspace and present in **both** images. It is importable from the workload venv in Jupyter kernels **and in Airflow run containers**, where the factory sets `PYTHONPATH=/opt/lakehouse-bundle` only.
- **Entry point**: `create_spark_session(app_name, catalog=...)` returns a `SparkSession` with:
  - **token source**: Airflow when the run container's broker settings are present (`LAKEHOUSE_TOKEN_PROVIDER=airflow` with the run handle, capability, initial token, broker URL and CA); Jupyter when `JUPYTERHUB_API_TOKEN` is present (it requests the user's token from the Hub broker); otherwise a clear error. Incomplete Airflow settings are an error, never a fallback to another identity.
  - **catalogs**: `lakehouse`, `lakehouse_uat`, `lakehouse_dev` (REST, Polaris, realm header, `S3FileIO`, vended credentials, the platform auth manager); `catalog` selects the default and must be one of them.
  - **redaction**: the platform's patterns for Spark and Spark SQL.
- **Existing session**: when a session is already active with the same default catalog, it is returned; with a different one, the call fails and says to restart the kernel.
- **One source of truth**: the catalog settings exist once in the platform. `spark-defaults.conf` and the module agree (Application Design decides how).
- **Compatibility**: the Jupyter example `from lakehouse_spark import create_spark_session; spark = create_spark_session()` keeps working. The Java token contract is unchanged.

### FR-2 The repository keeps its configuration (Q1 A, Q2 C)
- **Config ownership**: `configs/<env>.yml` stays repository-owned and free-form. Every key, for example a source dataset that differs per environment, reaches the job as today, in Jupyter (`dev` by default) and in Airflow (`uat`, `prod`). Only `storage_path`, `database_name` and `catalog_name` must match the platform's product file.
- **`start_spark_job(app_name, argv=None)`** keeps its name and returns `(spark, config)`: it loads the config with `config_loader`, then calls the platform's `create_spark_session` with the config's `catalog_name`. It no longer contains catalog, token or redaction settings.
- **Product folders**: `configs/<product>/<env>.yml` stays an Airflow feature (the platform sets `LAKEHOUSE_PRODUCT` from the bundle). Jupyter always reads `configs/<env>.yml`; the README says so.
- **Removed**: the `spark-files` branch, `LAKEHOUSE_BUNDLE_CONFIG_DIR` and `LAKEHOUSE_CONFIG_DIR`.

### FR-3 Jupyter environment resolver (Q3 A, CR-1)
- **Location and name** (CR-1): `notebooks/workload/jupyter_helper.py` moves to `notebooks/common/jupyter_environment_resolver.py`. Notebooks run it with `%run ../common/jupyter_environment_resolver.py` (relative to `notebooks/workload/`, where the entry points live); the old file is removed.
- **Safe to import**: it is now part of the `notebooks.common` package, which Airflow runs import; it starts Spark only when run with `%run` in a Jupyter kernel, never on import.
- **Environment**: `dev` unless the notebook sets `LAKEHOUSE_ENVIRONMENT` to `uat` or `prod` before the helper (for example `%env LAKEHOUSE_ENVIRONMENT=uat`); any other value is an error. Access stays limited by the user's own groups.
- **Repository root**: as now, the nearest folder above the notebook holding `notebooks/common/` and `configs/`; that clone's configs are used.
- **Spark application name**: `<env>-<notebook name>` instead of `dev-init_environment`.
- **Text**: no references to `init_environment.py`; the notebooks' instructions match the behavior. Switching environments in an open kernel needs a kernel restart (FR-1 rule).

### FR-4 Task arguments in Jupyter (Q4 A)
- **`task_args()` in Jupyter** returns the notebook's `TASK_ARGS` list (strings), for example `TASK_ARGS = ["--entity", "orders"]`, and `[]` when it is not set. A `TASK_ARGS` that isn't a list of strings is an error. Outside Jupyter, behavior is unchanged (the arguments after `--`).
- **Declared task arguments** (CR-2, refined): `notebooks/common/cli.py` gains one generic parser. An entry point declares its task arguments once, as a mapping of names to `required` or a `default` (for example `{"entity": {"required": True}, "scale_factor": {"default": "0.01"}}`), and one call parses `task_args()` in both contexts: the workflow's `args` after `--` in Airflow, `TASK_ARGS` in Jupyter. Names map to options (`scale_factor` → `--scale-factor`). The result is a read-only mapping of every declared name to its **string** value, or the default.
  - **Sources** (CR-3): in Airflow, the workflow's `args` after `--`. In Jupyter, the input widgets (FR-4a) when they exist; otherwise the notebook's `TASK_ARGS`; otherwise nothing, so defaults apply and required names are reported. An empty widget counts as not given.
  - **No value validation**: the parser never converts or checks values (no types, choice lists, bounds or formats). A notebook that needs that does it itself.
  - **Errors** (structure only): unknown options, a missing required option, an option given twice or without a value, and an invalid declaration are reported together, with the job's usage. In Airflow the job exits with status 2; in Jupyter the call raises an error instead of ending the kernel.

### FR-4a Jupyter input widgets (CR-3)
- **Helper**: `notebooks/common/jupyter_input_widget_helper.py`. A notebook defines `WIDGET_LIST = ["entity", ...]` and then runs `%run ../common/jupyter_input_widget_helper.py`; the helper reads `WIDGET_LIST` from the notebook's namespace and shows one text widget per name, labelled with the name.
- **Values**: strings, read by the common parser when it is called (FR-4); widgets are matched to declared arguments by name. Running the helper again keeps the values already typed.
- **Rules**: `WIDGET_LIST` must be a list of distinct names in the declaration's naming (`[a-z][a-z0-9_]*`); otherwise the helper fails with a clear message. Outside a Jupyter kernel it does nothing; on import it does nothing.
- **Platform**: the shared lock adds `ipywidgets` (so both images carry it), and JupyterLab's environment adds `jupyterlab_widgets`, so widgets render.

- **`generate_tpch.py`** declares `entity` and `scale_factor` this way, defines `WIDGET_LIST = ["entity", "scale_factor"]` for Jupyter (`TASK_ARGS` still works without widgets), instead of `ENTITY`, `SCALE_FACTOR` and its own `parse_task_args`; it keeps its own checks of the entity and the scale factor, and its TPC-H functions.

### FR-5 Cleanup and tests
- **`count_sample_rows.py`**: the `"airflow" not in sys.modules` guard is removed (bundles use `subdir: dags`).
- **Platform tests**: the module's settings for each catalog, both token sources and their errors, the existing-session rule, its presence and import in both images.
- **Workload tests**: `start_spark_job` (config passed through, catalog handed to the platform, no platform settings left), the helper's environment and root rules, `task_args()` in Jupyter.

### FR-6 Documentation
- **Platform README**: the session module for notebooks and workloads.
- **Workload README and AGENTS.md**: the ownership split, environment selection in Jupyter, `TASK_ARGS`, product folders in Airflow only.

### FR-7 Delivery (Q6 A)
- **Order**: platform side first. The current workload code (its own session settings) must keep working with the new images, so the repository change can follow.
- **Push**: the workload change is prepared and tested in the scratchpad clone and pushed to `main` and `uat` only after approval.

## Change request CR-1 (2026-11-10, during Requirements Analysis)
- **Request**: "the jupyter_helper should be moved inside the common folder and be renamed as jupyter_environment_resolver."
- **Decision**: FR-3 as above. Every entry point's `%run` line, the README, AGENTS.md and the tests follow the new path.

## Change request CR-2 (2026-11-10, during Workflow Planning)
- **Request**: "can we make the argument parser more generic and move also the functions to the common folder?"
- **Answers** (interactive): a declarative mapping (not an argparse object per job); move the argument helpers; job-specific functions (TPC-H) stay in their notebooks; session and config as already planned.
- **Refinement**: "do not validate args types, leave this to the notebook if the developer wants to handle them". The parser handles only option structure (names, required, defaults) and returns strings; type, choice, bound and format checks stay in the notebook, so no value helpers move to `common`.
- **Decision**: FR-4 as above. Functional Design defines the declaration format and the structural errors.

## Change request CR-3 (2026-11-10, during Workflow Planning)
- **Request**: "for jupyter create a jupyter_input_widget_helper and place it on common . By running this notebook inside a notebook , text widgets with the name from the list WIDGET_LIST=["entity"] defined before should be created . The argument parser should parse the widgets if they exist (in jupyter) or from command line(airflow)".
- **Answer** (interactive): widgets first, otherwise `TASK_ARGS` (Q4 is kept as the fallback).
- **Decision**: FR-4a; FR-4's sources. Platform impact: `ipywidgets` in `infra/workload-python/requirements.in` (the lock is regenerated, both images rebuilt, the parity check rerun) and `jupyterlab_widgets` in the Jupyter server requirements.

## Change request CR-4 (2026-11-10, during Build and Test)
- **Request**: "by default the !lakehouse-install-requirements ~/work/opensource-lakehouse and the %run ../common/jupyter_environment_resolver.py should be added to the top of all notebooks in a initialization section and included in the readme file that indication".
- **Decision**: every notebook in `notebooks/workload/` starts, after its title, with an "Initialization" section: `# !lakehouse-install-requirements ~/work/opensource-lakehouse` and `# %run ../common/jupyter_environment_resolver.py`, as Jupytext-commented cells (active in Jupyter, comments under `spark-submit`). The section says that a first install needs a kernel restart, and that `%env LAKEHOUSE_ENVIRONMENT=...` goes before it. The README's "Working in Jupyter" and "Writing an entry point" describe the section; a test checks it in every notebook. The resolver therefore also runs in `generate_tpch.py`.

## Change request CR-5 (2026-11-10, during Build and Test)
- **Request**: "align the notebooks structure in the workload folder so that they have "Initialization" , "Imports" (specific sections) and "Execution"".
- **Decision**: every notebook in `notebooks/workload/` has the `##` sections: Initialization, Imports, the job's own sections (settings and functions only), Execution (only the `if __name__ == "__main__":` block). README, AGENTS.md and a test follow.

## Non-Functional Requirements
- **NFR-1 One configuration**: Airflow and Jupyter sessions use identical catalog and redaction settings.
- **NFR-2 No secrets**: no token or credential in code, configs, logs or Spark's public configuration; tokens stay in process environment, as today.
- **NFR-3 Fail closed**: a missing or incomplete token source is an error with a clear message.
- **NFR-4 Compatibility**: DAG and task IDs, the workflow JSON, the config format and the Java token contract are unchanged.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q5: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q5: A) |
| Resiliency Baseline | No | Requirements Analysis (Q5: A) |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Out of scope
- Moving config loading to the platform (Q1 B).
- Selecting product folders in Jupyter (Q2 C).
- The smoke-table bootstrap (`infra/spark-bootstrap/`), which authenticates as the writer client on purpose.
- Distributed Spark, Spark or Iceberg upgrades.
