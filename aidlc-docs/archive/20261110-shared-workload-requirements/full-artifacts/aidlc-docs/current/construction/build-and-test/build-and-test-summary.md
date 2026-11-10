# Build and Test Summary — Shared Workload Requirements

Run on 2026-11-10 against the local stack (aarch64).

## Build
| Step | Result |
|---|---|
| `docker build` `local/lakehouse-spark-runtime:3.5.5_1.10.2` | OK in 42 s; build check `OK: Python 3.10, 53 locked package(s)`; 2.45 GB → 2.61 GB |
| `docker build` `local/lakehouse-jupyter-singleuser:6.1.1-spark` | OK in 59 s; same build check; 1.02 GB → 1.22 GB |
| `scripts/verify/workload-python-parity.sh` | **OK**: both venvs equal the workspace lock, identical 53 packages, one kernel "Lakehouse (Python 3.10)" |
| `./scripts/lakehouse.sh start-airflow` (twice) | OK; both bundles list `generate_tpch` and `test_environment`; the second run recreated the broker for CR-3 |
| Jenkins recreated (`up -d --no-deps jenkins`) | healthy; `/opt/lakehouse/workload-python` mounted read-only; JupyterHub untouched |

## Offline tests
| Suite | Result |
|---|---|
| Host (`python3 -m pytest -q`) | 516 passed, 3 skipped (458 before this intent) |
| Airflow image (`scripts/verify/dag-factory-tests.sh`) | 51 passed |
| Broker image (`scripts/verify/broker-unit-tests.sh`) | 13 passed (2 new, CR-3) |
| Workload repository, Python 3.10 with duckdb | 51 passed; `scripts/code_quality.sh all` clean |

## Live
| Check | Result |
|---|---|
| Jupyter server in a throwaway container of the new image | `/api/kernelspecs`: only `python3` "Lakehouse (Python 3.10)" (the config.d drop-in works with the base config); kernel on `/opt/lakehouse/venv/bin/python` 3.10.16, pandas 2.2.3 |
| `lakehouse-install-requirements` | installs `duckdb==1.5.6` only (no locked duplicates); a rerun says nothing to add; `pandas==2.2.2` refused |
| `generate_tpch` in a kernel | `TPC-H orders at scale factor 0.01: 15000 rows` |
| UAT run `default-uat-test_environment` (no `requirements.txt` yet) | 8/8 success; `install_requirements`: "No requirements.txt; nothing to install." (after one broker restart, see CR-3) |
| Push of workload `8ef716f` to `main` and `uat` (approved) | fast-forward from `9cbd6f8` |
| UAT run `default-uat-generate_tpch` | **13/13 success**; `Installed: duckdb==1.5.6`; region 5, nation 25, supplier 100, customer 1,500, part 2,000, partsupp 8,000, orders 15,000, lineitem 60,175 (eight tasks in parallel, each downloading the `tpch` extension) |
| Interactive JupyterHub (user-confirmed) | `joe-developer` signed in; server restarted on the new image (`a91226899db2`); the kernel reported `/opt/lakehouse/venv/bin/python 3.10.16 2.2.3 3.5.5` |
| CR-3: second `start-airflow` (Viewer recreated, broker not restarted), then a UAT run | 8/8 success; API log: cached token `403`, `/auth/token` `201`, DAG lookup `200` |
| Jenkins `default_ci` `main` #3 and `uat` #3 at `8ef716f` | SUCCESS; `Successfully installed duckdb-1.5.6`; `OK: 2 workflow(s)`; `requirements.txt resolves`; 51 passed (DuckDB test not skipped) |
| Interactive JupyterHub after CR-4 (user-confirmed: "it worked") | server restarted on image `1ed8eb2d9d7f`; repository cloned to `~/work/opensource-lakehouse` with git; `lakehouse-install-requirements` installed `duckdb-1.5.6` into `~/.local/lakehouse/python3.10`; the `generate_tpch` notebook ran |
| CR-4: Jupyter image rebuilt with `git` and JupyterLab Git | `git version 2.53.0` as `jovyan`; `jupyterlab_git` 0.55.0 and `nbdime` 4.0.4 server extensions and `@jupyterlab/git` lab extension enabled; parity OK; host tests 59 passed in `tests/workload_env` |

## Findings during Build and Test
- **CR-3 (fixed)**: the broker kept a Viewer token that Airflow refused with 403 after `start-airflow` recreated the Viewer, failing every run at `create_cluster`. Two UAT runs failed this way (14:01 and 14:02 UTC). The broker now signs in again and retries once.
- **JupyterHub admission (fixed by restart, outside scope)**: the Hub ran an outdated product model and admitted only platform admins; restarted with the user's confirmation. Follow-up recorded.

- **CR-5 (documented)**: Jupyter extras in `~/.local/lakehouse/python3.10` last one server session, because only `~/work` is a volume; the READMEs now say to rerun the command after each server start.

- **CR-6 (fixed)**: bundles get `subdir: dags`; before, the DAG processor imported `notebooks/workload/count_sample_rows.py` from both bundles about every 30 s. After `start-airflow` (Airflow recreated, no active runs), only `lakehouse.py` is parsed in each bundle, no `notebooks/` file; `default-uat-generate_tpch` 13/13; host 517 passed, Airflow image 51 passed.

## Not run
- Other users' servers started before the rebuild keep the old image until they are restarted.
- A production run (`default-main-generate_tpch`).
- A CI refusal of an invalid `requirements.txt` on a pushed branch (covered by tests and the Jenkins-image validator run on the scratchpad clone).
