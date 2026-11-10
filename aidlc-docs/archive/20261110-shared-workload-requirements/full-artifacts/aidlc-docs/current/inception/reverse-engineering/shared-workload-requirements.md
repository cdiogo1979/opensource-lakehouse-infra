# Focused Reverse Engineering — Shared Workload Requirements

Intent `20261110-shared-workload-requirements` (the CR-2 decisions of the previous intent). Scope: which Python environment runs workload code in Airflow's Spark containers and in Jupyter, where their packages come from, and what a shared, pinned requirements file plus product extras needs. Captured 2026-11-10.

## Today
| | Airflow Spark run container | Jupyter user server |
|---|---|---|
| Image | `local/lakehouse-spark-runtime:3.5.5_1.10.2` (`infra/spark-runtime/Dockerfile`, base `tabulario/spark-iceberg:3.5.5_1.8.1`) | `local/lakehouse-jupyter-singleuser:6.1.1-spark` (`infra/jupyter/singleuser/Dockerfile`, base `jupyterhub/singleuser`; it copies `/opt/spark` and the JVM from the runtime image) |
| OS / glibc | Debian 11 / 2.31 | Ubuntu 26.04 / 2.43 |
| Python running workload code | `/usr/local/bin/python3` **3.10.16** (`spark-submit` driver; `PYSPARK_PYTHON` is unset) | the kernel `python3` = `/opt/conda/bin/python` **3.13.16** (the only kernel) |
| PySpark | 3.5.5 (pip) and `/opt/spark/python` | `/opt/spark/python` from the runtime image (PySpark 3.5 officially supports Python up to 3.11) |
| Package source | **146 packages from the base image, unpinned by us**: pandas 2.2.3, numpy 1.26.4, pyarrow 17.0.0, scipy 1.14.1, matplotlib 3.9.2, pyiceberg 0.7.1, PyYAML 6.0.2, requests 2.32.3, plus JupyterLab, ipykernel and others | 166 packages: the base image plus `infra/jupyter/singleuser/requirements.txt` (`jupyterlab`, `notebook`, `ipykernel`, `jupytext`); **no pandas, numpy or pyarrow**; PyYAML 6.0.3, requests 2.34.2 |
| Network | `airflow-spark` and `data-access` networks, not internal: **PyPI reachable** (HTTP 200) | `jupyter-user` and `data-access` networks, not internal |

- **Existing pattern**: `infra/jupyter/hub/` installs `requirements.txt` with `--constraint requirements-lock.txt`.
- **Workload code**: the workload repository (`opensource-lakehouse` `9cbd6f8`) imports `yaml` in `config_loader`, plus `pyspark`. Its own `requirements-dev.txt` holds test tools only. The README tells developers that entry points get only the Spark image's packages.

## Consequences
1. **Different environments**: notebook code that works in Jupyter (3.13) can fail in Airflow (3.10), and the reverse. Pandas, numpy and pyarrow exist only in Airflow.
2. **Unpinned base**: the base image decides the packages, so a base update could silently change them.
3. **Copying the runtime's Python into Jupyter is risky**: it is built for Debian's glibc 2.31 on a different OS, so it would need its own Python 3.10 build.

## What the decisions need (CR-2)
- **The platform base file**: `requirements.in` (top-level packages) and a fully pinned lock for Python 3.10, installed identically in both images. The runtime image's extra base packages either stay outside it or are isolated; that's an Application Design question.
- **A Python 3.10 kernel in Jupyter**: for example a conda or venv environment on Python 3.10 with ipykernel and the same lock, registered as the default kernel and used by local Spark (`PYSPARK_PYTHON`). JupyterLab itself can stay on 3.13.
- **Product extras**: an optional `requirements.txt` in the product repository, installed at run start with `--constraint <platform lock>`, so extras can't change platform pins.
  - **Airflow**: in the run's Spark container, before `validate_environment`. PyPI is reachable. The time and the failure mode need deciding.
  - **Jupyter**: explicit or automatic installation into the user's environment, under the same constraint.
- **Checks**: CI could resolve the product extras against the lock (Jenkins has Python 3.10 and network access). A platform test could check that both images hold exactly the locked versions.
