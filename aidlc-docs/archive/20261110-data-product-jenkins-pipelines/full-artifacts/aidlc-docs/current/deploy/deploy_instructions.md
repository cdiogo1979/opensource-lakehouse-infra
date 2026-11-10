# Deploy Instructions — Data product Jenkins pipelines

All steps are manual operator commands, run from the repository root. Steps 1 to 3 were already executed on the current local stack during Build and Test; on any other copy of the stack, follow them in this order.

| # | Action and target | Prerequisites | Execution | Validation | Failure handling |
|---|---|---|---|---|---|
| 1 | **Product files** (`data-products/*.yaml`) | Only for files written before this change | Remove `apps.jenkins.owner` and every `Overall/*` permission. Keep folder permissions for `developer`, `analyst` and `writer` (default: `developer: [Job/Read, Job/Build, Job/Cancel, Job/Workspace]`, `analyst: [Job/Read]`). | `python3 infra/products/render_jenkins.py --check` prints the plan without an error | The render names the file and field; the running Jenkins keeps its files until it passes |
| 2 | **Jenkins** (image, CasC, Job DSL, state, hook mounts) | Core stack running. Jenkins restarts, which aborts running builds. | `./scripts/lakehouse.sh start`. It renders the three files, rebuilds the image with `job-dsl` and checks plugin versions, and recreates Jenkins with the new mounts. | The log shows `Applied data product folders and jobs`; `python3 scripts/verify/jenkins-oidc.py` passes 10/10 | Image build fails on a plugin mismatch: fix `plugins.txt`. Hook failure (`not applied; nothing deleted`): read the Jenkins log, fix, restart |
| 3 | **First builds** | Step 2 | Nothing to run. Each new `_ci` job scans when created and builds `prod_branch` and `uat_branch`; `_cd` builds PR branches at its 30-minute scan. | Folder `<name>` shows the jobs; the `_ci` branch builds succeed | A failing branch build is the repository's `Jenkinsfile`; check its console log |
| 4 | **Owner access** (communication) | Step 2 | Tell product owners they are now admins of their folder only, no longer Jenkins administrators | `role-<name>-owner` can configure the folder but `/manage` returns 403 | Platform admin or break-glass can still administer Jenkins |
| 5 | **Test residue**. Done on the local stack: the backups were deleted, and Airflow had already removed the DAG records. | Build and Test of this intent | **Airflow DAG records**: `docker exec lakehouse-local-airflow-scheduler-1 airflow dags delete jptest-main-test_environment -y`, the same for `jptest-uat-test_environment`. **Backups**: delete `.runtime/backups/*-remove-jptest`. | `airflow dags list` shows no `jptest-` DAG | Deleting the DAG records removes no runs (they have none) |

**Rollback** (not automated):
1. Restore the previous `render_jenkins.py`, `data_products.py`, `casc/jenkins.yaml`, `plugins.txt`, `Dockerfile`, `compose.jenkins.yml` and product files.
2. Delete the hook mount.
3. Run `lakehouse.sh start`.

The product folders stay in the home until someone deletes them (with their build history). The old matrix gave owners Jenkins-wide Administer.

**Subsequent product changes are automatic.** `create-data-product.sh` and `remove-data-product.sh` render the files and restart Jenkins only when they changed; `--no-restart` defers the restart and `--dry-run` prints the folder and job plan. Note that `--no-restart` also applies to Airflow: re-applying a product whose `repo` bundles were never applied recreates Airflow.
