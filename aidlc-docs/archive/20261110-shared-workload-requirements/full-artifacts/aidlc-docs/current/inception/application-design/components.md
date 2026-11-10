# Components — Shared Workload Requirements

| # | Component | Location | Status | Responsibility |
|---|---|---|---|---|
| C1 | Workload Python lock | `infra/workload-python/` | new | `requirements.in` (top-level pins), the generated `requirements.lock`, and `workload_python.py`, a standard-library module and CLI that parses the lock, checks a venv against it, checks and resolves product extras, and installs them |
| C2 | Lock generator | `scripts/setup/lock-workload-python.sh` | new | Regenerates `requirements.lock` from `requirements.in` in the pinned base image of the Spark runtime (same Python 3.10.16, aarch64, glibc 2.31) |
| C3 | Spark runtime image | `infra/spark-runtime/Dockerfile` | changed | Builds `/opt/lakehouse/venv` from its Python 3.10.16 with exactly the lock; ships the lock and `workload_python.py`; `PYSPARK_PYTHON`, `PYSPARK_DRIVER_PYTHON` and `PATH` point at the venv; fails the build unless the venv equals the lock |
| C4 | Jupyter single-user image | `infra/jupyter/singleuser/` | changed | Adds conda-forge Python 3.10.16 at `/opt/lakehouse/python3.10` (not on `PATH`), the same venv, the lock and module; replaces the `python3` kernel spec with "Lakehouse (Python 3.10)"; disables the server's native kernel; adds the per-user extras path and `lakehouse-install-requirements`; fails the build unless the venv equals the lock |
| C5 | DAG factory | `infra/airflow/lakehouse_dags/factory.py` | changed | New task `install_requirements` between `create_cluster` and `validate_environment`; the config check calls the venv's Python explicitly |
| C6 | CI validator | `infra/jenkins/bin/lakehouse-validate-workflows`, `compose.jenkins.yml` | changed | After the workflow rules, checks `requirements.txt` (when present) with C1 against the lock, mounted read-only |
| C7 | Parity verifier | `scripts/verify/workload-python-parity.sh` | new | Checks that both built images report Python 3.10 and exactly the lock in `/opt/lakehouse/venv` |
| C8 | Workload repository | `cdiogo1979/opensource-lakehouse` (scratchpad clone) | changed | `requirements.txt` (`duckdb==1.5.6`), `notebooks/workload/generate_tpch.py`, `workflows/generate_tpch.json`, README, AGENTS.md, tests |

**Not changed**: `sparse_dirs`. Git's cone mode always checks out files at the repository root, so `requirements.txt` already reaches `/opt/lakehouse-bundle` (both `default` checkouts contain `README.md` and `Jenkinsfile` today). A file entry is not valid in cone mode anyway. FR-4's `sparse_dirs` clause is satisfied without a change, and Airflow needs no recreation for it.
