# Deployment Instructions — Spark streaming checkpoints

Target: the local lakehouse stack in this repository. All steps are manual commands from the repository root. The steps were already performed on this machine during Build and Test; they apply to any other checkout or a fresh stack.

| # | Action and target | Prerequisites | Execution | Validation | Failure handling |
|---|---|---|---|---|---|
| 1 | Rebuild the images and recreate the Hub | Stack initialized (`.runtime/` present); Maven Central reachable | `./scripts/lakehouse.sh start` | Exit 0; `/opt/spark/jars/hadoop-aws-3.3.4.jar` in both images. A NOTICE about missing keys is expected before step 2 on a new stack | Build failure: check the Maven download and checksums; the previous images stay tagged until a build succeeds |
| 2 | Create the checkpoint keys for every product | Step 1; RustFS running; root key in `.runtime/credentials/` | `python3 infra/rustfs/bootstrap-checkpoint-keys.py` (a fresh stack: `scripts/bootstrap-default-product.sh`, which includes it) | `created` or `unchanged` per bucket; a re-run reports `unchanged`; `--check-staged` exits 0 | Non-zero exit: the message names the failing RustFS step; files of the failing bucket are unchanged; rerun after fixing. Undo: `--remove --product FILE` for non-default products |
| 3 | Verify the keys | Step 2 | `python3 scripts/verify/checkpoint-keys.py` | `Checkpoint keys verified.` | Any FAIL: stop; do not start Airflow runs that use checkpoints |
| 4 | Recreate Airflow with the key folder | Step 2 | `./scripts/lakehouse.sh start-airflow` | Exit 0; DAG verification passes. Refuses to start if keys are missing | Rerun step 2, then this step |
| 5 | Verify streaming end to end | Steps 1 to 4 | `scripts/verify/checkpoint-stream.sh` | `Checkpoint stream verification passed.` | FAIL lines name the phase; the test checkpoint is under `checkpoints/_verify/` and can be deleted |
| 6 | Restart Jupyter user servers | Step 1 | Each user: Hub Control Panel → Stop My Server → Start My Server | `ls /run/secrets/lakehouse-checkpoints/` shows the user's dev buckets only | Spawn error naming a bucket: rerun step 2 |

Rotation later: `./scripts/lakehouse.sh rotate-checkpoint-keys [--product FILE]`, then restart the affected Airflow runs and Jupyter servers.
Rollback: no automated rollback is designed. Reverting the code and rebuilding the images returns catalogs to `S3FileIO`; existing checkpoint data under `checkpoints/` is left in place, and keys can be removed per product with `--remove`.
