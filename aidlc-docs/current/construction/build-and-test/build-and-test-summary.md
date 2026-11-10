# Build and Test Summary — Repository Rename

Run on 2026-11-10.

## Tests
- Host suite: 530 passed, 3 skipped (after the rename edits, and again after CR-1).
- Workload repository: 85 passed, 1 skipped (DuckDB); lint clean.

## Live
| Check | Result |
|---|---|
| Workload `932feee` (Initialization path) pushed to `main` and `uat` (approved) | fast-forward from `42de0f3` |
| `./scripts/lakehouse.sh start` and `start-airflow` from `/Users/carlosdiogo/code_repo/opensource-lakehouse-infra` | both exit 0; Airflow verified `default-main` and `default-uat` (both DAGs each) |
| Containers left on the old folder | `keycloak-db`, `polaris-db`, `airflow-postgres`, `polaris-group-reconciler` (not recreated by `start`); force-recreated with `--no-deps` from the new folder, no DAG run active, named volumes kept; all services healthy afterwards |
| Old-folder references | **0** containers mount or set a path under `opensource-lakehouse-infra-v2` |
| Bundles | `default-uat` at `932feee`, then `cb80fc5`, from `opensource-lakehouse-sample-dp` |
| CR-1, CR-2: images rebuilt with `rest-metrics-reporting-enabled=false`; workload `cb80fc5` pushed (approved) | parity OK; UAT on `cb80fc5`: `test_environment` 8/8, `generate_tpch` 13/13; Polaris: 40 table requests, **0** metrics requests (4 in the hour before); no `RESTMetricsReporter` lines; the new log message |
| Jenkins `default_ci` `main` #9 and `uat` #9 at `cb80fc5` | SUCCESS, cloning `github.com/cdiogo1979/opensource-lakehouse-sample-dp` |
| JupyterHub | healthy; admits `role-default-analyst`, `role-default-developer`, `role-platform-admin` |

## Not run
- The user's own clones (local and in Jupyter) follow the rename by the user (commands given).
- A production run.
