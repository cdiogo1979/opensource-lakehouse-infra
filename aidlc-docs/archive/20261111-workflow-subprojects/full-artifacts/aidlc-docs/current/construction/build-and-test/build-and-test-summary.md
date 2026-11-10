# Build and Test Summary — Workflow Subprojects

Run on 2026-11-11.

## Tests
| Suite | Result |
|---|---|
| Host | 547 passed, 3 skipped (530 before; subprojects, layer entry points, P5) |
| Airflow image (`dag-factory-tests.sh`) | 71 passed (51 before) |

## Live
| Check | Result |
|---|---|
| `start-airflow` with the subproject rules (no run active) | the flat `sample-dp` (`cb80fc5`) kept its four DAGs; no import errors |
| Workload `1b83568` (outside the intent, approved push): `workflows/sample/`, `notebooks/workload/sample/` | same four DAG IDs; UAT `test_environment` 8/8, `generate_tpch` 13/13 |
| CR-1: layer entry points `<layer>/<file>.py`; `start-airflow` | four DAGs, no import errors |
| Workload `f10156f` (approved): layer docs and tests | Jenkins `default_ci` `main` #11 and `uat` #11 SUCCESS (89 passed) |
| CR-2: `other` layer; `start-airflow`; Jenkins sees `LAYERS` with `other` | four DAGs, no import errors |
| Workload `f8c13e0` (approved): notebooks in `notebooks/workload/sample/other/`, workflows name `other/<file>.py` | UAT 8/8 and 13/13 on `f8c13e0`, no import errors; Jenkins `default_ci` `main` #12 and `uat` #12 SUCCESS (`OK: 2 workflow(s)`, 89 passed) |

## Not run
- A production run.
- A CI refusal of a repeated workflow name or an unknown layer on a pushed branch (covered by tests).
