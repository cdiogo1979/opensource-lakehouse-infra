# Application Design — Shared Workload Requirements

Consolidates [components.md](components.md), [component-methods.md](component-methods.md), [services.md](services.md) and [component-dependency.md](component-dependency.md). Decisions are backed by the probes below (throwaway containers, 2026-11-10; no running service changed).

## Decisions
1. **One module, one lock** (`infra/workload-python/`): `requirements.in`, the generated `requirements.lock`, and `workload_python.py` (standard library, CLI). Both images copy the lock to `/opt/lakehouse/requirements.lock` and the module to `/opt/lakehouse/workload_python.py`; Jenkins mounts the directory read-only. One implementation of the rules serves the image check, CI, Airflow and Jupyter.
2. **The lock is resolved in the runtime's base image** (`tabulario/spark-iceberg` at the pinned digest, Python 3.10.16, Debian 11, aarch64) by `scripts/setup/lock-workload-python.sh`: venv, wheels-only install of `requirements.in`, then `pip freeze` with `PYTHONPATH` unset. Result today: 53 packages (no `pip`, `setuptools` or `pyspark`).
3. **Spark runtime**: `/usr/local/bin/python3 -m venv /opt/lakehouse/venv`, install the lock with `--no-deps --only-binary=:all:`. `ENV PYSPARK_PYTHON=PYSPARK_DRIVER_PYTHON=/opt/lakehouse/venv/bin/python` and `PATH=/opt/lakehouse/venv/bin:$PATH`. The base image's own packages stay in `/usr/local` but are not on the workload's path.
4. **Jupyter's Python 3.10**: `mamba create -p /opt/lakehouse/python3.10 -c conda-forge python=3.10.16` (127 MB), run with `HOME=/root` so the build leaves nothing in `/home/jovyan`. The venv is created from it. It is not put on `PATH`; JupyterLab stays on conda's 3.13.
5. **The kernel keeps the name `python3`**: its `kernel.json` is replaced (display name "Lakehouse (Python 3.10)", the venv's interpreter, `PYSPARK_PYTHON` in `env`), and `/etc/jupyter/jupyter_server_config.py` sets `KernelSpecManager.ensure_native_kernel = False`. Notebooks saved with the old kernel name open with the new kernel without prompting. `PYTHONPATH` (`/opt/lakehouse`, `/opt/spark/python`, py4j) is inherited unchanged.
6. **Extras in Airflow go into the run container's own venv**: the container runs as root and is removed at `stop_cluster`, so the image is never changed. pip then sees the installed lock and installs only what is missing. After the install, `check-venv --allow-extra` confirms every locked version is unchanged.
7. **Extras in Jupyter go to `~/.local/lakehouse/python3.10`** with `--target`, in the user's home volume. A `.pth` file in the venv adds that directory at the end of `sys.path` when it exists, so the venv's locked packages always take precedence. Because `--target` reinstalls dependencies that are already locked (same versions), the command first resolves what is missing against the venv and installs only those packages, with `--no-deps` (rules in Functional Design).
8. **Wheels only** (Q1 A): every extras resolution and install uses `--only-binary=:all:`. CI resolves for the runtime's platform tags explicitly: pip accepts only the exact `--platform` tags given, so the list is `manylinux2014_aarch64` plus `manylinux_2_17` to `manylinux_2_31` aarch64, with `--python-version 3.10 --implementation cp --abi cp310`.
9. **`pyspark` is refused in extras**: it comes from `/opt/spark`; a pip copy would shadow it.
10. **`sparse_dirs` stays as it is**: root files are always in a cone-mode checkout (see components.md). No Airflow recreation is needed for this intent; the factory change takes effect through the existing read-only mount.
11. **The config check uses the venv explicitly** (`/opt/lakehouse/venv/bin/python`), not whatever `python3` the exec environment resolves.
12. **DuckDB's extension cache**: tasks of one run share the container and its `HOME=/root`; the first `generate_<entity>` task downloads the `tpch` extension to `/root/.duckdb/extensions/v1.5.6/linux_arm64/` and the others reuse it.

## Probe results
| Probe | Result |
|---|---|
| Lock in the runtime image | venv from Python 3.10.16; 53 packages; venv 545 MB (pandas 217 MB, pyarrow 119 MB). With `PYTHONPATH` set, `pip freeze` also lists `pyspark` from `/opt/spark/python`, so checks unset it |
| Same lock in the Jupyter image | conda-forge Python 3.10.16 (OpenSSL 3.6.5) installed in 6 s; the lock installed; `pip check` clean; `pip freeze` **identical** to the runtime's |
| `spark-submit` on the venv | driver and executors use `/opt/lakehouse/venv/bin/python`; Arrow `toPandas()` works; arguments after `--` arrive intact |
| Extras in the run container | `duckdb==1.5.6` in 1.9 s; the 53 locked versions unchanged; `pandas==2.2.2` and `numpy>=2` refused (`ResolutionImpossible`, exit 1) |
| DuckDB TPC-H | `CALL dbgen(sf=0.01)`: 60,175 `lineitem` rows; the extension is cached under `/root/.duckdb`; a second session reuses it |
| Jupyter per-user extras | `--target ~/.local/lakehouse/python3.10` plus the `.pth` works as `jovyan`; `duckdb` imports; `requests` still comes from the venv; a conflict is refused. The build must run with `HOME=/root` (otherwise a root-owned `~/.local` blocks the user) |
| Kernel | one kernel, `python3` "Lakehouse (Python 3.10)"; a started kernel reports `/opt/lakehouse/venv/bin/python` 3.10.16, pandas 2.2.3, PySpark 3.5.5, `PYSPARK_PYTHON` set; `lakehouse_spark` imports |
| CI resolution in the Jenkins image | Python 3.10.22, aarch64. With the full tag list: `duckdb` (and `requests-toolbelt`) resolve; `pytpch==0.2.0` "from versions: none"; both conflicts refused |
| Bundle checkout | `default-uat` checkouts contain root files (`README.md`, `Jenkinsfile`, `pyproject.toml`) with cone-mode `sparse_dirs` |

## Consequences
- **Image sizes**: the runtime image grows by about 545 MB (the venv); the Jupyter image by about 670 MB (Python 3.10 and the venv).
- **Workload code loses** the base image's unpinned packages (scipy, matplotlib, pyiceberg and others) unless `requirements.in` adds them.
- **Runs with extras** need PyPI; runs without extras make no network call for packages.
- **Jupyter extras** are tied to Python 3.10 and the lock: after a lock change, users rerun the command (documented).

## Canonical knowledge
As planned: UPDATE `application-design.md`, `airflow-workflows.md` and `jenkins-ci-access.md`; CREATE `functional-design/workload-python-environment.md`. One refinement to the airflow-workflows update: `sparse_dirs` does not change.
