# PR Request — Repository rename

_Proposed PR description for this infrastructure repository. No pull request has been created by this workflow (the workspace had no git metadata during the intent). The companion workload commits are on `main` and `uat` of `cdiogo1979/opensource-lakehouse-sample-dp` (`932feee`, `cb80fc5`, pushed on approval); `opensource-lakehouse-sample-dp.patch` holds them._

## Problem
- The user renamed the workload repository (`opensource-lakehouse` → `opensource-lakehouse-sample-dp`) and this workspace's folder (`opensource-lakehouse-infra-v2` → `opensource-lakehouse-infra`). The product file, docs, tests and notebooks used the old repository name; running containers bind-mounted files of the old folder.
- A misleading Iceberg `RESTMetricsReporter` warning on table-creating writes, and a stale "Nessie GC" log message.

## Solution
- `data-products/default.yaml` and the README use the new repository URL; the Jenkins and products tests follow.
- The workload notebooks' Initialization line, README and AGENTS.md use `~/work/opensource-lakehouse-sample-dp` (`932feee`).
- The stack recreated from the new folder; four containers that `start` doesn't recreate were force-recreated (volumes kept).
- CR-1: `lakehouse_spark` sets `rest-metrics-reporting-enabled=false` for the three catalogs. CR-2: `test_environment.py`'s message without Nessie (`cb80fc5`).

## Main changes
| Area | Paths |
|---|---|
| Product and docs | `data-products/default.yaml`, `README.md` |
| Session module | `infra/workload-python/python/lakehouse_spark.py` |
| Tests | `tests/jenkins/test_product_pipelines.py`, `tests/products/test_repo_and_bundles.py`, `tests/workload_env/test_spark_session.py` |
| Workload reference | `aidlc-docs/current/deploy/opensource-lakehouse-sample-dp.patch` (= `42de0f3..cb80fc5`, 2 commits) |

## Verification
- Host 530 passed, 3 skipped; workload 85 passed, lint clean.
- Live: no container refers to the old folder; bundles on the renamed repository at `cb80fc5`; UAT 8/8 and 13/13; Polaris 0 metrics requests during the runs; Jenkins `default_ci` `main` #9 and `uat` #9 SUCCESS from the new URL; JupyterHub healthy and admitting users.
- Not run: a production run.

## Deployment
Ordered steps: see [`deploy_instructions.md`](deploy_instructions.md); done on this stack except the user's own clone and notebook server.

## Risks and limitations
- `start` and `start-airflow` don't recreate the databases or the scheduled reconciler; after moving the workspace folder they need a forced recreation (or a full `stop` and `start`).
- Polaris receives no Spark scan or commit metrics.
