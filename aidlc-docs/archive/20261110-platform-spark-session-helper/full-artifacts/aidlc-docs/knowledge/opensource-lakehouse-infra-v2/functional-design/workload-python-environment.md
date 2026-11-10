# Functional Design — Workload Python Environment

Current functional design of the shared Python environment that runs workload code in Airflow's Spark containers and in the Jupyter kernel, and of product extras. For architecture, see [`../application-design.md`](../application-design.md). History is in the [Shared Workload Requirements intent archive](../../../archive/20261110-shared-workload-requirements/intent-summary.md).

## Responsibility
One pinned Python 3.10 environment, identical in `local/lakehouse-spark-runtime` and `local/lakehouse-jupyter-singleuser`, plus a product's optional extras, which can add packages but never change a pinned version.

| Path | Role |
|---|---|
| `infra/workload-python/requirements.in` | Top-level pins: PyYAML 6.0.2, requests 2.32.3, pandas 2.2.3, numpy 1.26.4, pyarrow 17.0.0, ipykernel 6.29.5, jupytext 1.16.7 |
| `infra/workload-python/requirements.lock` | Every package, `name==version`, generated (53 packages on 2026-11-10) |
| `infra/workload-python/workload_python.py` | Standard-library module and CLI: `check-lock`, `check-venv`, `check-extras`, `install-extras` |
| `scripts/setup/lock-workload-python.sh` | Regenerates the lock in the runtime's base image (digest read from `infra/spark-runtime/Dockerfile`), wheels only, and validates it before writing |
| `scripts/verify/workload-python-parity.sh` | Both images: venv equals the workspace lock, identical `pip freeze`, one Jupyter kernel |

## Environment
- **Location**: `/opt/lakehouse/venv` (Python 3.10.16) in both images, with `/opt/lakehouse/requirements.lock` and `/opt/lakehouse/workload_python.py`. `PYSPARK_PYTHON` and `PYSPARK_DRIVER_PYTHON` point at the venv; in the runtime image the venv is first on `PATH`.
- **Spark runtime**: the venv is built from the base image's `/usr/local/bin/python3` (Debian 11, glibc 2.31). The base image's own packages stay in `/usr/local` and are not visible to workload code.
- **Jupyter**: Python 3.10.16 from conda-forge at `/opt/lakehouse/python3.10` (not on `PATH`), built with `HOME=/root`; JupyterLab stays on conda's Python 3.13. The only kernel is `python3`, display name "Lakehouse (Python 3.10)", on the venv (`kernel.json`); `/etc/jupyter/jupyter_server_config.d/lakehouse-kernels.json` sets `KernelSpecManager.ensure_native_kernel = false` and leaves the base image's `jupyter_server_config.py` in place. The image also has `git` and `jupyterlab-git` 0.55.0 (with `nbdime`).
- **PySpark**: from `/opt/spark/python` (Spark 3.5.5), never from pip.

## Rules
- **Names**: compared after PEP 503 normalization (lowercase; runs of `-`, `_`, `.` become `-`).
- **Lock**: the generator header first; then only `name==version` lines, comments and blank lines; no duplicates; never `pyspark`, `py4j`, `pip`, `setuptools`, `wheel`; not empty.
- **Venv check** (`check-venv PYTHON --lock LOCK [--allow-extra]`): Python 3.10; `pip freeze` run with `PYTHONPATH` and `PIP_*` removed (otherwise `/opt/spark/python` lists `pyspark`) equals the lock exactly; with `--allow-extra`, additional packages are allowed and listed, but every locked version must still match. Both image builds fail on any problem.
- **Extras file** (`requirements.txt` at a product repository's root; see `airflow-workflows.md` for its checkout):
  - UTF-8, at most 64 KiB and 200 requirements; every problem reported as `requirements.txt:<line>: <message>`.
  - Accepted: `name`, optional `[extras]`, optional specifiers (`==`, `!=`, `<=`, `>=`, `<`, `>`, `~=`), optional `; marker`, comments.
  - Refused: any line starting with `-` (options such as `-r`, `-e`, `--index-url`, `--hash`); URLs, `@` references, paths (`.`, `/`, `~`) and continuations; `===`; `pyspark`, `py4j`, `pip`, `setuptools`, `wheel`; a name listed twice. A locked package may be listed; the lock decides its version.
- **Resolution and installs**: always `--only-binary=:all:` and `--constraint` the lock, with `--disable-pip-version-check --no-input --no-cache-dir` and `PIP_*` removed (public PyPI only, no credentials).
  - **CI** (`check-extras`): a dry run with `--ignore-installed` for the runtime's platform: CPython 3.10, `cp310`, `manylinux2014_aarch64` and `manylinux_2_17` to `manylinux_2_31` aarch64 (pip accepts only the exact `--platform` tags given). Prints what it would add.
  - **Airflow** (`install-extras FILE --lock LOCK`): into the run container's venv; then the venv check with `--allow-extra`.
  - **Jupyter** (`lakehouse-install-requirements [PATH] [--reset]` → `install-extras ... --target ~/.local/lakehouse/python3.10`): a dry run against the kernel venv (which sees the folder through `lakehouse-user-extras.pth`, appended after site-packages so locked packages win) lists what is missing; changed projects are removed from the folder by their `RECORD` (never outside it); the missing set is installed with `--no-deps`; the folder records the lock's SHA-256 in `.lakehouse-lock.sha256`. Repeated runs add packages. After a lock change the command refuses until `--reset`, which empties only a folder it manages.
  - **No file** (or comments only): nothing to do, exit 0, no network access. A path that exists but isn't a file is a problem.

## Failure behavior
| Situation | Result |
|---|---|
| Lock malformed | the generator writes nothing; builds and checks fail with the line |
| Venv differs from the lock | the image build fails; the parity verifier fails |
| Refused extras line | CI fails listing every line; `install_requirements` fails before pip runs; the Jupyter command changes nothing |
| Conflict with the lock or no suitable wheel | pip's `ResolutionImpossible` or "No matching distribution", exit 1, in all three places |
| PyPI unreachable | CI fails; `install_requirements` retries twice, then the run stops before any workload code |
| Lock changed since a Jupyter install | the command asks for `--reset` |

## Verification and limits
- **Verified 2026-11-10**:
  - host suite 517 passed (`tests/workload_env`: examples, Hypothesis P1 to P5, image and wiring contracts), Airflow image 51 passed, workload repository 51 passed with DuckDB (P6, P7);
  - both images built with their checks and the parity verifier passed;
  - `default-uat-generate_tpch` 13/13 with `duckdb==1.5.6` installed and all eight TPC-H counts correct; a run without `requirements.txt` installed nothing;
  - Jenkins `default_ci` `main` and `uat` with the extras check and the DuckDB tests;
  - user-confirmed in JupyterHub: the kernel on the venv, `git clone`, `lakehouse-install-requirements`, the `generate_tpch` notebook.
- **Limits**:
  - Jupyter extras last one server session: the user volume is mounted at `/home/jovyan/work` only and stopped servers are removed; rerun the command after every server start.
  - Extras come from public PyPI on every run, with no cache; packages need a CPython 3.10 aarch64 wheel for glibc 2.31 or older (for example, `pytpch` 0.2.0 can't be used).
  - Servers started before an image rebuild keep the old image until restarted.
