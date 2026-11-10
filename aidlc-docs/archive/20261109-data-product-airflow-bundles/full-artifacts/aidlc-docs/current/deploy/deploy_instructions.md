# Deploy Instructions — Data product Airflow bundles

All steps are manual operator commands from the repository root. On the current local stack they were all executed during Build and Test; this is the order for any other copy of the stack.

| # | Action and target | Prerequisites | Execution | Validation | Failure handling |
|---|---|---|---|---|---|
| 1 | Workload contract in each bundle repository (`cdiogo1979/opensource-lakehouse` `main` and `uat`) | Write access to the repository | Done: `fedf0bc` on both branches. For another repository: `git apply aidlc-docs/current/deploy/opensource-lakehouse.patch` on its prod and UAT branches, commit, push | `git ls-remote --heads <url> main uat` shows the patched commit | Do not continue to step 3 without it: the DAG check would time out. Revert the commit to undo |
| 2 | Product files (`data-products/*.yaml`) | Products applied (writer password files exist) | Add or keep a `repo` block per product; `default.yaml` already has one | `python3 scripts/setup/stage-airflow-writers.py --list` lists `<name>-main` and `<name>-uat` per product | Fix the reported validation error |
| 3 | Airflow and the token broker | Core stack running; step 1 done; no DAG runs in progress (containers are recreated) | `./scripts/lakehouse.sh start-airflow` (creates the Viewer secret once, rebuilds the broker image, stages writers, recreates Airflow, records the fingerprint) | "Verified Bundle ..." for every bundle; `.runtime/state/airflow-bundles.json` written; `airflow users list` shows `lakehouse-broker` with Viewer only | On a timeout, inspect `airflow dags list-import-errors` in `airflow-dag-processor`; nothing is recorded, so rerun after the fix |
| 4 | Broker check | Step 3 | `scripts/verify/broker-unit-tests.sh`; optionally a run of a UAT DAG | 11 passed; the run's `create_cluster` task succeeds | A refused run fails at `create_cluster` with its reason (`unknown_product`, `unknown_dag`, `bundle_mismatch`) |
| 5 | Stale DAG records (optional) | Step 3 | `docker exec lakehouse-local-airflow-scheduler-1 airflow dags delete <dag_id> -y` for the old `main-`/`uat-`/`dev-` IDs, or delete them in the UI | `airflow dags list` shows only `<bundle>-...` DAGs | Deleting removes the DAG's run history; skip if it is needed |

**Rollback**: no automated rollback. To go back, restore the previous versions of the changed files and rerun `start-airflow`; the old `lakehouse-main`/`lakehouse-uat` names and `main-`/`uat-` DAG IDs still work in the patched workload repository, but the old single-writer broker would need the previous `app.py` and compose settings (`srv_default_writer_password` secret).

**Subsequent product changes** are automatic: `create-data-product.sh` and `remove-data-product.sh` recreate Airflow when the bundles or writers change (`--no-restart` to defer).
