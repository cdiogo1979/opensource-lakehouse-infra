# Code Summary — workload-python

## Platform (this workspace)
| File | Change | Rules |
|---|---|---|
| `infra/workload-python/workload_python.py` | new: `normalize_name`, `parse_lock`, `render_lock`, `parse_freeze`, `compare`, `check_extras_lines`, `read_extras`, `platform_args`, `check_venv`, `remove_from_target`; CLI `check-lock`, `check-venv`, `check-extras`, `install-extras` | BR-L, BR-V, BR-E, BR-R, BR-J |
| `infra/workload-python/requirements.in` | new: the seven top-level pins | FR-1 |
| `infra/workload-python/requirements.lock` | new, generated: 53 packages | BR-L |
| `scripts/setup/lock-workload-python.sh` | new: resolves the lock in the runtime's base image (digest read from the runtime Dockerfile) and validates it before writing | FR-1 |
| `infra/spark-runtime/Dockerfile` | the venv, lock and module; `PYSPARK_PYTHON`, `PYSPARK_DRIVER_PYTHON`; venv first on `PATH`; build check | FR-2, BR-I1 |
| `infra/jupyter/singleuser/Dockerfile` | conda-forge Python 3.10.16 (`HOME=/root`), the venv, lock and module, the kernel, the config drop-in, the `.pth`, the command; `PYSPARK_PYTHON`; build check | FR-2, FR-3, FR-5, BR-I1, BR-I4 |
| `infra/jupyter/singleuser/kernel.json` | new: `python3` = "Lakehouse (Python 3.10)" | FR-3 |
| `infra/jupyter/singleuser/lakehouse-kernels.json` | new: `KernelSpecManager.ensure_native_kernel = false`, installed to `/etc/jupyter/jupyter_server_config.d/` | FR-3 |
| `infra/jupyter/singleuser/lakehouse-user-extras.pth` | new: appends `~/.local/lakehouse/python3.10` to `sys.path` when it exists | BR-J |
| `infra/jupyter/singleuser/lakehouse-install-requirements` | new: `install-extras "$@" --lock ... --target ~/.local/lakehouse/python3.10` | FR-5 |
| `infra/airflow/lakehouse_dags/factory.py` | `install_command()`, `_install_requirements`, task `install_requirements` (2 retries, 30 s); config check on the venv's Python | BR-A |
| `infra/jenkins/bin/lakehouse-validate-workflows` | runs `check-extras` after the workflow rules when `requirements.txt` exists | BR-C |
| `compose.jenkins.yml` | `./infra/workload-python:/opt/lakehouse/workload-python:ro` | BR-C |
| `scripts/verify/workload-python-parity.sh` | new: both images against the workspace lock, identical freeze, one kernel | BR-I3, BR-I4 |
| `README.md` | new section "Workload Python environment"; JupyterHub, Airflow, scripts, limitations | FR-8 |
| `tests/workload_env/` | new: `test_workload_python.py` (examples), `test_workload_python_properties.py` (P1 to P5), `test_image_contracts.py` | FR-8 |
| `tests/airflow/test_dag_factory.py` | the new task in the golden graph and P2; two new tests (command and retries; redacted failure) | BR-A |
| `tests/airflow/test_workflow_spec.py` | the wrapper test now runs the wrapper (no extras: unchanged output; refused lines: exit 1) | BR-C |

| `infra/airflow-token-broker/app.py` | CR-3: on 401 or 403 from the DAG lookup, drop the cached Viewer token, sign in again and retry once | CR-3 |
| `tests/airflow/test_token_broker_writers.py` | CR-3: the fake Airflow refuses tokens issued before the Viewer was recreated; two tests | CR-3 |

| `infra/jupyter/singleuser/Dockerfile`, `requirements.txt` | CR-4: Ubuntu `git`; `jupyterlab-git==0.55.0` | CR-4 |
| `tests/workload_env/test_image_contracts.py` | CR-4: `git` and the pinned extension | CR-4 |

| `infra/products/data_products.py`, `infra/airflow/validate-bundle-config.py` | CR-6: bundle kwargs `"subdir": "dags"` | CR-6 |
| `tests/airflow/test_workflow_spec.py` | CR-6: `subdir` equals the stub's folder in both places | CR-6 |

## Workload repository (commit `8ef716f`, pushed to `main` and `uat` on 2026-11-10 after approval)
| File | Change |
|---|---|
| `requirements.txt` | new: `duckdb==1.5.6` (CR-1) |
| `notebooks/workload/generate_tpch.py` | new: `parse_scale_factor`, `expected_count`, `check_count`, `parse_task_args`, `generate_tpch` (BR-T1 to BR-T4) |
| `workflows/generate_tpch.json` | new: eight tasks `generate_<entity>` (BR-T5) |
| `tests/workload_foundation/test_generate_tpch.py` | new: examples, P6, P7, a DuckDB run (skipped without duckdb) |
| `Jenkinsfile` | the test-dependency stage installs `requirements.txt` with the mounted lock as constraint |
| `README.md`, `AGENTS.md` | the Python packages section, the new task, Jupyter kernel and command, CI, how-to, limits |

## Deviations found during generation
- **The base image's `/etc/jupyter/jupyter_server_config.py`** (listen address, umask, certificates) would have been replaced by the planned file; the setting is a `jupyter_server_config.d` JSON drop-in instead.
- **A folder named `requirements.txt`** was taken for a folder holding one; it is now refused (BR-R5), found by the tests.
- **The `generate_tpch` tasks run in parallel** (no `runs_after`), so up to eight tasks download DuckDB's `tpch` extension at once on first use, unlike Application Design decision 12 ("the first task caches it"). Probed: three rounds of eight parallel first uses in the runtime image all succeeded. No serialization is needed.

## Tests run
- Host suite: **516 passed**, 3 skipped (458 before; 58 new in `tests/workload_env`).
- Airflow image (`scripts/verify/dag-factory-tests.sh`): **51 passed** (49 before).
- Workload repository: host `.venv` (Python 3.14) 50 passed, 1 skipped (no duckdb); in the runtime image (Python 3.10, `duckdb==1.5.6`) **51 passed**; `scripts/code_quality.sh all` passed after one Black blank-line fix.
- The changed workload repository through the Jenkins image's validator with the new mounts: `OK: 2 workflow(s)`, `requirements.txt resolves`, `Would add: duckdb==1.5.6`.
