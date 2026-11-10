# Intent Summary: Platform Spark Session Helper

## Intent
Platform Spark Session Helper (`20261110-platform-spark-session-helper`)

## Objective
One platform-owned Spark session module (lakehouse_spark) for workload code in Airflow runs and Jupyter, with product repositories keeping their free-form configuration; declared task arguments, Jupyter widgets and environment resolution in the workload repository's notebooks/common; one notebook structure.

## Date
2026-11-10

## Scope
Included: lakehouse_spark and the broker client moved to infra/workload-python/python, lakehouse-platform.pth in both images, spark-defaults.conf trimmed, ipywidgets in the lock and jupyterlab_widgets in JupyterLab, tests, README; the workload repository's job_runtime, cli.parse_task_args, jupyter_environment_resolver (CR-1), jupyter_input_widget_helper (CR-3), declared arguments (CR-2), Initialization section (CR-4) and notebook structure (CR-5), tests and docs (ad1ca8d, 41ee812, 42de0f3, pushed to main and uat). Excluded: config loading in the platform, product folders in Jupyter, the smoke bootstrap, value validation in the parser.

## Units / workstreams
spark-session

## Major requirements
- FR-1: lakehouse_spark.create_spark_session(app_name, catalog) in both images, importable in Airflow run containers; the only copy of catalogs, token source and redaction.
- FR-2: product repositories keep free-form configs/<env>.yml; start_spark_job passes catalog_name to the platform; product folders in Airflow only.
- FR-3 and CR-1: notebooks/common/jupyter_environment_resolver.py; dev by default, LAKEHOUSE_ENVIRONMENT for uat/prod; application <env>-<notebook>.
- FR-4, CR-2, CR-3: cli.parse_task_args(declaration), strings only, structural errors only; Airflow args, Jupyter widgets (jupyter_input_widget_helper.py) else TASK_ARGS.
- CR-4, CR-5: every notebook: title, Initialization (lakehouse-install-requirements, the resolver), Imports, own sections, Execution.

## Architecture and design decisions
- The module ships with the workload environment in infra/workload-python/python and reaches Airflow run containers through a .pth in the venv, independent of PYTHONPATH.
- spark-defaults.conf keeps only extensions and redaction; the smoke bootstrap sets its own catalogs.
- Token source: airflow (all run settings required) or jupyter (Hub token); no fallback. A running session is reused only for the same catalog.
- Notebook values are read through IPython's user namespace (also during %run); the %run scripts act only under %run in a kernel.
- ipywidgets 8.1.9 in the shared lock and jupyterlab_widgets 3.0.17 in JupyterLab, the same version on both sides.

## Implementation decisions
- parse_task_args: --opt value or --opt=value; spec only required/default; usage line; exit 2 outside Jupyter, TaskArgumentError in Jupyter.
- The widget helper puts its own clone on the import path from __file__ (for notebooks that don't run the resolver first).
- Both Dockerfiles check the platform import at build time; the runtime image with PYTHONPATH=/opt/lakehouse-bundle.
- A test enforces the Initialization lines and the section order in every notebook.

## Deviations
- CR-1 to CR-5 were added by the user during Requirements Analysis, Workflow Planning and Build and Test.
- The parser's explicit argv is the task arguments themselves (found by the tests).
- The interactive JupyterHub check was not reported; covered by a throwaway-kernel check only.

## Verification
See construction/build-and-test/build-and-test-summary.md. Host 530 passed, 3 skipped; Airflow image 51 passed; workload 85 passed (84 on Python 3.10 in the image with DuckDB), lint clean, validator OK. Live: both images with lock and import checks, parity OK; previous workload code on the new images UAT 8/8 and 13/13; on ad1ca8d, 41ee812, 42de0f3 UAT 8/8 and 13/13 each and Jenkins default_ci main/uat #5 to #7 SUCCESS; a Jupyter-image kernel exercised widgets, parse_task_args and the resolver's refusal without a token. Not run: an interactive JupyterHub session on the new image (not reported by the user); a production run.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/workload-python-environment.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/airflow-workflows.md

## Superseded decisions
- Q4's TASK_ARGS-only convention became widgets first, then TASK_ARGS (CR-3).
- CR-2's typed declarations (types, choices, bounds) became structure-only parsing with string values (refinement).
- Spark session settings in each product repository's job_runtime.py and the Jupyter image's copy replaced by the platform's lakehouse_spark.

## Archived artifacts
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/aidlc-docs/current/compaction/20261110-platform-spark-session-helper/manifest.json
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/workload-python-environment.md
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/airflow-workflows.md
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/infra/workload-python/python/lakehouse_spark.py
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/infra/workload-python/python/lakehouse_broker_client.py
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/infra/workload-python/lakehouse-platform.pth
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/infra/workload-python/requirements.in
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/infra/workload-python/requirements.lock
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/infra/jupyter/singleuser/requirements.txt
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/infra/jupyter/singleuser/spark-defaults.conf
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/infra/spark-runtime/Dockerfile
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/infra/jupyter/singleuser/Dockerfile
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/README.md
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/tests/workload_env/test_spark_session.py
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/tests/workload_env/test_image_contracts.py
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/tests/jupyterhub/test_unit2_broker_client.py
- aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/tests/jupyterhub/test_unit3_spark_credential_refresh.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261110-platform-spark-session-helper/full-artifacts/`
