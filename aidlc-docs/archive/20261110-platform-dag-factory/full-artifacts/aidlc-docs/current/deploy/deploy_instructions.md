# Deploy Instructions — Platform DAG factory

All steps are manual operator commands, run from the repository root. They were all executed on the current local stack during Build and Test; for any other copy of the stack, follow them in this order.

| # | Action and target | Prerequisites | Execution | Validation | Failure handling |
|---|---|---|---|---|---|
| 1 | **Platform side**: package, mounts, `sparse_dirs`, checkout sync | No DAG run in progress, because Airflow is recreated | `./scripts/lakehouse.sh start-airflow`. It runs `sync-bundle-checkouts.py` before starting Airflow, then recreates the dag-processor and the scheduler with the `lakehouse_dags` mount | `start-airflow` prints `Verified Bundle ...` for each bundle; `python -c "import lakehouse_dags"` works in both containers; each `tracking_repo`'s `git sparse-checkout list` includes `workflows` | The old in-repository DAGs keep working on their own factory, so nothing is lost. Fix and rerun |
| 2 | **Jenkins validator** | Step 1 | `./scripts/lakehouse.sh start`, which recreates Jenkins with the package and wrapper mounts | `docker exec lakehouse-local-jenkins-1 lakehouse-validate-workflows /tmp` exits 1 ("dags/lakehouse.py: is missing") | Check the two mounts in `compose.jenkins.yml` |
| 3 | **Workload repository** (each product repository) | Steps 1 and 2; write access | For `cdiogo1979/opensource-lakehouse` this is done: `9cbd6f8` is on `main` and `uat`. For another repository: add `workflows/*.json` and the stub (`lakehouse_dags.spec.STUB_TEXT`), remove its own DAG code, and add the "Validate workflows" `Jenkinsfile` stage. `aidlc-docs/current/deploy/opensource-lakehouse.patch` is the reference | `lakehouse-validate-workflows .` prints `OK`; after about 5 minutes the DAGs' `fileloc` is `.../dags/lakehouse.py`, with no import errors | An import error lists every problem by file and field. Revert the commit to undo |
| 4 | **Run check** | Step 3 | Trigger `<product>-uat-<workflow>` | All tasks succeed, `validate_environment` included | A one-off "dubious ownership" at a task's bundle refresh was seen once (see the build-and-test summary). Rerun, and investigate if it repeats |

**Rollback**:
1. Revert the workload commit on `main` and `uat`. The old `dags/dag_factory.py` comes back and parses as before.
2. Platform side: removing the mounts and `PYTHONPATH` is optional; the package is harmless while no repository uses the stub. Keep `workflows` in `sparse_dirs`, or set it back and rerun `start-airflow`.

**Afterwards**: product repositories change DAGs only through `workflows/*.json`. Platform changes to `infra/airflow/lakehouse_dags` take effect for all products at the next `start-airflow`; run `scripts/verify/dag-factory-tests.sh` first.
