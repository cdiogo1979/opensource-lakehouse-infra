# Build and Test Summary — Platform Spark Session Helper

Run on 2026-11-10 against the local stack (aarch64).

## Build
| Step | Result |
|---|---|
| `local/lakehouse-spark-runtime:3.5.5_1.10.2` | built; `OK: Python 3.10, 56 locked package(s)`; import check with `PYTHONPATH=/opt/lakehouse-bundle` passed |
| `local/lakehouse-jupyter-singleuser:6.1.1-spark` | built; the same lock check; import check of `lakehouse_spark`, `lakehouse_broker_client`, `ipywidgets` passed |
| `scripts/verify/workload-python-parity.sh` | **OK**: both venvs equal the workspace lock (56 packages); one kernel |

## Offline tests
| Suite | Result |
|---|---|
| Host | 530 passed, 3 skipped (517 before; 13 new: session module, image contracts) |
| Airflow image | 51 passed |
| Workload repository, host `.venv` | 83 passed, 1 skipped (DuckDB); lint clean; validator `OK: 2 workflow(s)` |
| Workload repository, new runtime image (Python 3.10, venv, duckdb) | **84 passed** |

## Live
| Check | Result |
|---|---|
| Compatibility: old workload code `0bc9ecd` on the new runtime image | `default-uat-test_environment` 8/8; `default-uat-generate_tpch` 13/13 |
| `lakehouse_spark` in the runtime venv with `PYTHONPATH=/opt/lakehouse-bundle` | imports from `/opt/lakehouse/python`; `ipywidgets` 8.1.9 present |
| Jupyter image, throwaway kernel with the new workload code | widget manager `@jupyter-widgets/jupyterlab-manager` 5.0.16 enabled; the helper emitted widget views; `parse_task_args` read `{'entity': 'orders', 'scale_factor': '0.01'}`; an empty required field raised `TaskArgumentError` with the usage; the resolver without a Hub token stopped with "No token source" |
| Push of workload `ad1ca8d` to `main` and `uat` (approved) | fast-forward from `0bc9ecd` |
| UAT runs on `ad1ca8d` | `default-uat-test_environment` 8/8 (application `uat-test_environment`); `default-uat-generate_tpch` 13/13 with all eight TPC-H counts (entity from the declared arguments) |
| Jenkins `default_ci` `main` #5 and `uat` #5 at `ad1ca8d` | SUCCESS; `OK: 2 workflow(s)`; extras resolve; 84 passed |
| CR-4: workload `41ee812` (Initialization section in every notebook), pushed to `main` and `uat` (approved) | Jupytext opens all three notebooks with `!lakehouse-install-requirements ~/work/opensource-lakehouse` and `%run ../common/jupyter_environment_resolver.py` as the first code cells; workload tests 84 passed, lint clean; UAT on `41ee812`: 8/8 and 13/13; Jenkins `default_ci` `main` #6 and `uat` #6 SUCCESS |
| CR-5: workload `42de0f3` (Initialization, Imports, own sections, Execution in every notebook), pushed to `main` and `uat` (approved) | workload tests 85 passed, lint clean; UAT on `42de0f3`: 8/8 and 13/13; Jenkins `default_ci` `main` #7 and `uat` #7 SUCCESS |
| Interactive JupyterHub check | not run: the user approved Build and Test without reporting it (the same image and code were checked in a throwaway kernel) |

## Not run
- A production run.
- An interactive JupyterHub session on the new image: not reported by the user; covered only by the throwaway-kernel check (widgets, parser, resolver up to the token step).
