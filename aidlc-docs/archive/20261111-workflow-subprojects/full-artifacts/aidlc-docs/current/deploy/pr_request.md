# PR Request — Workflow subprojects

_Proposed PR description for this infrastructure repository; no pull request was created by this workflow. The companion workload commits (made outside the intent, at the user's request) are on `main` and `uat` of `cdiogo1979/opensource-lakehouse-sample-dp`: `1b83568`, `f10156f`, `f8c13e0`; `opensource-lakehouse-sample-dp.patch` holds them._

## Problem
Product repositories could hold workflows only in `workflows/<name>.json` and entry points only directly in `notebooks/workload/`, so the subproject and medallion-layer layout of the user's `test_aidlc` conventions was refused by CI and Airflow.

## Solution
- **Subprojects**: `workflows/<project>/<name>.json` with entry points in `notebooks/workload/<project>/`, next to the unchanged flat layout. DAG IDs stay `<bundle>-<name>`, so names are unique across the repository.
- **Layers** (CR-1, CR-2): an `entrypoint` may be `<layer>/<file>.py` with layer `bronze`, `silver`, `gold`, `ops`, `deploy` or `other`; workflows have no layer folders.
- **Refused**: invalid or nested folders, other files, unknown layers, `..`, repeated names (both files named).

## Main changes
| Area | Paths |
|---|---|
| Rules | `infra/airflow/lakehouse_dags/spec.py` (`PROJECT`, `LAYERS`, `ENTRYPOINT`, `Workflow.project`, `entrypoint_path`, subproject discovery, unique names) |
| Factory | `infra/airflow/lakehouse_dags/factory.py` (`submit_` uses `entrypoint_path`) |
| Tests | `tests/airflow/{workflow_strategies,test_workflow_spec,test_dag_factory}.py` |
| Docs | `README.md` (Airflow section) |

## Verification
Host 547 passed; Airflow image 71 passed. Live: flat, subproject, and `other/` layouts each load the same four DAGs; UAT 8/8 and 13/13 on `1b83568` and `f8c13e0`; Jenkins `default_ci` `main`/`uat` #11 and #12 SUCCESS. Not run: a production run; a CI refusal on a pushed branch (tests cover it).

## Deployment
No ordered steps beyond applying the mounted package: `./scripts/lakehouse.sh start-airflow` with no DAG run active (done). Jenkins reads the same mounted package. No `deploy_instructions.md` is needed.

## Risks and limitations
- Workflow names are unique per repository, not per subproject (DAG IDs don't include the subproject).
- The layer folder list is fixed in the platform; a new layer needs a platform change.
