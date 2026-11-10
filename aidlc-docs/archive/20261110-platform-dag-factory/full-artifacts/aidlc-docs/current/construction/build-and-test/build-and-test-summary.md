# Build and Test — Platform DAG Factory (2026-11-10)

## Offline
- **Platform, host**: `python3 -m pytest -q tests` gives **458 passed, 3 skipped**. This includes P1, P3 and P4, the spec, validator and wiring tests, and the new checkout-sync tests.
- **Platform, Airflow image**: `scripts/verify/dag-factory-tests.sh` gives **49 passed**: golden DAG, platform-only callables, no templating, task options, the ported container, broker and cleanup tests, and P2.
- **Workload repository** (`9cbd6f8`): 36 passed, including P5. Ruff, Black, Flake8 and Bandit all PASS. `lakehouse-validate-workflows .` gives `OK: 1 workflow(s)`.

## Live cut-over (FR-8)
| Step | Result |
|---|---|
| 1. Platform side live (`start-airflow`) | Airflow recreated. `lakehouse_dags` imports from the read-only mount in the scheduler and the dag-processor (`touch` gives "Read-only file system"). Both old DAGs re-verified on the in-repository factory at `515e403`. |
| Defect found: `sparse_dirs` | Airflow applies `sparse_dirs` only on the first clone, and the existing `tracking_repo` checkouts kept `configs dags notebooks`. **Fixed**: `scripts/setup/sync-bundle-checkouts.py` updates each configured bundle's `tracking_repo` before Airflow starts and is called by `start-airflow`; tests added. Live: `default-main` and `default-uat` updated, and a re-run made no change. |
| Jenkins validator | `lakehouse.sh start` recreated Jenkins. `lakehouse-validate-workflows` is on `PATH`, and an empty directory is refused. |
| 2. Push (user-approved) | `main` and `uat` fast-forwarded `515e403..9cbd6f8`. |
| 3. Bundle refresh | Both DAGs now come from `.../tracking_repo/dags/lakehouse.py` at `9cbd6f8` with unchanged DAG IDs. No import errors. Tasks: `create_cluster`, `validate_environment`, `submit_test_environment_first`, `submit_test_environment_second`, `submit_count_sample_rows`, `stop_cluster`, `verify_workloads_succeeded`. |
| UAT run 1 (`manual__2026-11-10T11:31:59`) | **failed**, 6 of 7. `validate_environment` succeeded in the container, and `first` and `count` wrote and read the UAT tables. `second` failed before running its code: the task runner's bundle refresh (`git fetch` in `tracking_repo`) hit "detected dubious ownership" while `second` and `count` started at the same moment. Run by hand, the same fetch succeeds, and uid 501 owns everything as the task user. |
| UAT run 2 (`manual__2026-11-10T11:33:42`) | **success, 7 of 7.** |
| Jenkins `default_ci` | `main` #2 and `uat` #2 **SUCCESS** at `9cbd6f8`. The "Validate workflows" stage gave `OK: 1 workflow(s)`, then lint passed and 36 tests passed. |

## Open finding
- **What**: a one-off "dubious ownership" failure of Airflow's per-task bundle refresh when two tasks start at once on the same `tracking_repo`.
- **Cause**: not established. It happened once, a few minutes after the host-side `sparse-checkout set`, and not in the next run. The parallel shape is unchanged from the previous intent's passing run.
- **Status**: **not resolved**. It is recorded as a risk to watch: retries on the `submit_` tasks would absorb it, and a repeat should be investigated, for example with the macOS file-sharing ownership mapping and concurrent `git fetch`.

## Not run
- A deliberately invalid workflow pushed to a branch, to see the `_cd` job refuse it. That would need another push, and the validator's refusals are covered offline and in Jenkins against an empty directory.
- A `default-main` (production) run.
- Interactive Jupyter use of the new `cli.task_args()`. It is unit-tested; Jupyter returns `[]`.

## Residue
- The workload repository branch `platform-dag-factory` exists only in the scratchpad clone.
- `.runtime/airflow-dag-bundles` still holds old bundle folders from earlier intents (`bttest-*`, `jptest-*`, `lakehouse-*`). They are unused, and nothing in this intent created them.
- The break-glass netrc was deleted after use.
