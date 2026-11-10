# PR Request — Shared workload requirements

_Proposed PR description for this infrastructure repository. No pull request has been created, because this workspace has no git metadata. The companion workload changes are already on `main` and `uat` of `cdiogo1979/opensource-lakehouse` (`8ef716f` and `0bc9ecd`, pushed on the user's approval); `opensource-lakehouse.patch` holds them for reference._

## Problem
- **Two different Pythons**: workload code ran on Python 3.10 with 146 unpinned base-image packages in Airflow's Spark containers, and on Python 3.13 without pandas, numpy or pyarrow in the Jupyter kernel. Code that worked in one could fail in the other, and a base-image update could change packages silently.
- **No product dependencies**: a product repository had no way to add a package.

## Solution
- **One pinned environment**: `infra/workload-python/requirements.in` (PyYAML, requests, pandas, numpy, pyarrow, ipykernel, jupytext) and the generated `requirements.lock` (53 packages, resolved in the runtime's base image by `scripts/setup/lock-workload-python.sh`). PySpark comes from `/opt/spark`.
- **The same venv in both images**: `/opt/lakehouse/venv` (Python 3.10.16) in the Spark runtime and the Jupyter single-user image, used through `PYSPARK_PYTHON`. Each build fails unless the venv equals the lock. Jupyter gets Python 3.10.16 from conda-forge, and its only kernel is "Lakehouse (Python 3.10)" (under the name `python3`, so existing notebooks open with it).
- **Product extras**: an optional root `requirements.txt` with plain requirements only (no options, URLs, paths, or `pyspark`/`py4j`/`pip`/`setuptools`/`wheel`), prebuilt aarch64 wheels only, always constrained by the lock.
  - **Airflow**: a new task `install_requirements` between `create_cluster` and `validate_environment` (2 retries, 30 s), into the run's own container; nothing without the file.
  - **CI**: `lakehouse-validate-workflows` resolves the file against the lock for the runtime platform; the lock is mounted read-only into Jenkins.
  - **Jupyter**: `lakehouse-install-requirements [PATH] [--reset]` into `~/.local/lakehouse/python3.10`, for the current server session (CR-5).
- **Shared module**: `infra/workload-python/workload_python.py` (standard library) implements the lock, venv, extras-line and install rules for the image checks, CI, Airflow and Jupyter.
- **Change requests**:
  - CR-1: `pytpch` 0.2.0 has only an x86_64 glibc 2.34 wheel; `duckdb==1.5.6` is the example extra.
  - CR-2: the workload `generate_tpch` (DuckDB TPC-H generation, one task per entity, checked row counts).
  - CR-3: the Airflow token broker re-signs in once when its cached Viewer token is refused (401/403); before, every run failed after `start-airflow` until the broker restarted.
  - CR-4: `git` and JupyterLab Git (`jupyterlab-git==0.55.0`) in the Jupyter image.
  - CR-5: Jupyter extras last one server session (only `~/work` is a volume); documented.
  - CR-6: Git bundles get `subdir: dags`, so the DAG processor no longer imports repository code under `notebooks/`.
- **Decisions**: Q1 clean venv at one path; Q2 today's Airflow data stack; Q3 extras each run; Q4 a documented Jupyter command; Q5 one kernel; Q6 image, CI and parity checks; Q7 docs plus the example, pushed on approval; Q8 partial property-based testing; wheels only (Application Design); adding with `--reset`, and 2 retries (Functional Design).

## Main changes
| Area | Paths |
|---|---|
| Environment | `infra/workload-python/{requirements.in,requirements.lock,workload_python.py}`, `scripts/setup/lock-workload-python.sh`, `scripts/verify/workload-python-parity.sh` |
| Images | `infra/spark-runtime/Dockerfile`; `infra/jupyter/singleuser/{Dockerfile,requirements.txt,kernel.json,lakehouse-kernels.json,lakehouse-user-extras.pth,lakehouse-install-requirements}` |
| Airflow | `infra/airflow/lakehouse_dags/factory.py` (`install_requirements`, venv interpreter); `infra/products/data_products.py` and `infra/airflow/validate-bundle-config.py` (`subdir`); `infra/airflow-token-broker/app.py` (CR-3) |
| Jenkins | `infra/jenkins/bin/lakehouse-validate-workflows`, `compose.jenkins.yml` |
| Docs and tests | `README.md`; `tests/workload_env/{test_workload_python,test_workload_python_properties,test_image_contracts}.py`; `tests/airflow/{test_dag_factory,test_workflow_spec,test_token_broker_writers}.py` |
| Workload reference | `aidlc-docs/current/deploy/opensource-lakehouse.patch` (= `9cbd6f8..0bc9ecd`) |

## Verification
- **Suites**: host 517 passed, 3 skipped (458 before); Airflow image 51 passed; broker image 13 passed; workload repository 51 passed on Python 3.10 with duckdb, lint clean.
- **Live**:
  - both images built with their checks; the parity verifier passed;
  - `default-uat-test_environment` 8/8 (no extras: nothing installed);
  - `default-uat-generate_tpch` 13/13 with `duckdb==1.5.6` installed and all eight TPC-H counts correct, also after CR-6;
  - CR-3: after a second `start-airflow`, without a broker restart, a run passed (403, re-sign-in, 200);
  - CR-6: the DAG processor parses only `dags/lakehouse.py` in each bundle;
  - Jenkins `default_ci` `main` #3 and `uat` #3 at `8ef716f` succeeded, with the extras check and the DuckDB test;
  - user-confirmed in JupyterHub (`joe-developer`): the kernel on `/opt/lakehouse/venv` 3.10.16, `git clone`, `lakehouse-install-requirements`, and the `generate_tpch` notebook.
- **Not run**: a production run of `generate_tpch`; a CI refusal on a pushed branch (tests and a Jenkins-image validator run cover it).

## Deployment
Ordered steps are required (image rebuilds, Airflow and Jenkins recreation, user server restarts): see [`deploy_instructions.md`](deploy_instructions.md). They have already been carried out on this local stack.

## Risks and limitations
- **Packages removed from workload code**: the runtime base image's other packages (scipy, matplotlib, pyiceberg and others) are no longer importable unless added to `requirements.in`.
- **Extras need PyPI**: no private index or cache; each run with a `requirements.txt` installs it again; DuckDB downloads its `tpch` extension in each run.
- **Wheels only, aarch64**: packages without a suitable wheel can't be used (for example `pytpch`).
- **Jupyter extras are per session** (CR-5), and old user servers keep the previous image until restarted.
- **Image size**: the runtime image grows by about 160 MB and the Jupyter image by about 200 MB (compressed).
- **Follow-ups**: the JupyterHub product model reload; the enforcing bundle class (now limited to `dags/`); the platform Spark session helper (from the analysis of `notebooks/common`).
