# Code Generation Plan — workload-python

Unit: `workload-python` (one unit). Workspace root for platform code; the workload repository change is made in the scratchpad clone (`cdiogo1979/opensource-lakehouse`, branch from `9cbd6f8`) and pushed to `main` and `uat` only after approval. Rules: `construction/workload-python/functional-design/business-rules.md`.

## Platform (this workspace)
- [x] **Step 1 — Lock module** `infra/workload-python/workload_python.py` (standard library): `normalize_name`, `parse_lock`, `render_lock`, `parse_freeze`, `compare`, `check_extras_lines`, `platform_args`, `scale` helpers; CLI `check-venv`, `check-extras`, `install-extras` (venv and `--target` modes, `--reset`, the stamp). BR-L, BR-V, BR-E, BR-R, BR-J.
- [x] **Step 2 — Base set and lock**: `infra/workload-python/requirements.in`; `scripts/setup/lock-workload-python.sh` (base image digest read from `infra/spark-runtime/Dockerfile`); generate `infra/workload-python/requirements.lock` by running it.
- [x] **Step 3 — Spark runtime image** `infra/spark-runtime/Dockerfile`: venv, lock install, `COPY` of lock and module, `PYSPARK_PYTHON`, `PYSPARK_DRIVER_PYTHON`, `PATH`, the build check (BR-I1).
- [x] **Step 4 — Jupyter image** `infra/jupyter/singleuser/`: Python 3.10.16 from conda-forge (`HOME=/root`), the venv, the lock and module, `kernel.json` replacing `python3`, `jupyter_server_config.py` (`ensure_native_kernel = False`), `lakehouse-user-extras.pth`, `lakehouse-install-requirements`, the build check. `requirements.txt` (JupyterLab's own) unchanged.
- [x] **Step 5 — DAG factory** `infra/airflow/lakehouse_dags/factory.py`: `install_command()`, `_install_requirements`, task `install_requirements` (2 retries, 30 s) between `create_cluster` and `validate_environment`; `validate_command` on the venv's Python (BR-A).
- [x] **Step 6 — CI** `infra/jenkins/bin/lakehouse-validate-workflows` (BR-C) and the read-only mount `./infra/workload-python:/opt/lakehouse/workload-python:ro` in `compose.jenkins.yml`.
- [x] **Step 7 — Parity verifier** `scripts/verify/workload-python-parity.sh` (BR-I3, BR-I4).
- [x] **Step 8 — Tests**:
  - `tests/workload_python/test_workload_python.py`: examples for every BR-L, BR-V, BR-E rule and the CLI (with a fake interpreter for `check-venv`; pip itself not called);
  - `tests/workload_python/test_workload_python_properties.py`: P1 to P5 (Hypothesis, `ci` profile);
  - `tests/workload_python/test_image_contracts.py`: both Dockerfiles, the kernel spec, the `.pth`, the command, the Jenkins mount, the generator's digest matching the runtime Dockerfile, the lock passing BR-L;
  - `tests/airflow/test_dag_factory.py` (in the Airflow image): the new task, its order, retries, command; `validate_command` interpreter.
- [x] **Step 9 — README**: Airflow and JupyterHub sections, a new "Workload Python environment" section (base set, regenerating the lock, extras in Airflow and Jupyter, wheels only, checks), the scripts list, known limitations.

## Workload repository (scratchpad clone)
- [x] **Step 10** — `requirements.txt` (`duckdb==1.5.6`, with a comment), `notebooks/workload/generate_tpch.py` (Jupytext `py:percent`, BR-T1 to BR-T4, testable functions `parse_scale_factor`, `parse_task_args`, `expected_count`, `check_count`), `workflows/generate_tpch.json` (BR-T5).
- [x] **Step 11** — tests: `tests/workload_foundation/test_generate_tpch.py` (examples plus P6, P7 with Hypothesis; DuckDB itself only when importable); the workflow passes the platform validator.
- [x] **Step 12** — `README.md` and `AGENTS.md`: the platform base set, `requirements.txt` extras (constrained, wheels only, installed each run, refused lines, the `pytpch` example), the Jupyter command and the single kernel, the `generate_tpch` workflow.

## Documentation
- [x] **Step 13** — `construction/workload-python/code/code-summary.md`: files changed, how each rule maps to code, test counts.

## Not in this stage
Image builds, the parity run, live Airflow and Jupyter checks, and the push are Build and Test (push only on approval).
