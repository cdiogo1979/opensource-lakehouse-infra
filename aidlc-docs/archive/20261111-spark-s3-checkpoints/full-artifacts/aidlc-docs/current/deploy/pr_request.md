# PR request — Spark streaming checkpoints on RustFS (`s3ckpt://`)

## Problem
Spark Structured Streaming jobs had no durable checkpoint location. The images had no Hadoop S3 filesystem; Polaris vends credentials only for table locations; and Iceberg 1.10.2 writes a stream's `sources/0/offsets/0` through the source table's `S3FileIO`, so even an S3 checkpoint got 403. Requested by the paused `opensource-lakehouse-sample-dp` intent `20261111-tpch-medallion` (bronze to silver streaming).

## Solution
- Every Polaris catalog uses Iceberg's `ResolvingFileIO`. `s3://` table paths keep `S3FileIO` with vended credentials; checkpoints use the dedicated scheme `s3ckpt://`, which `ResolvingFileIO` hands to Hadoop and the platform maps to S3A.
- One static checkpoint key per product environment bucket: RustFS user `ckpt-<bucket>` with only the policy `checkpoints-<bucket>`. Chosen over STS with token exchange (proven in probes) because it needs the least custom code; STS remains a later option that changes only the platform's S3A credential settings.
- Delivery: an Airflow run mounts only its own environment's key; a Jupyter server mounts the `dev` keys of the user's owner or developer products; no global key, so other buckets fail closed. S3A selects the key per bucket, so several products work in one kernel.
- Products set `checkpoint_path: s3ckpt://<bucket>/checkpoints` in `configs/<env>.yml`.

## Main changes
- `infra/spark-runtime/Dockerfile`: `hadoop-aws` 3.3.4 and `aws-java-sdk-bundle` 1.12.262 (Maven strict checksums); Jupyter inherits them.
- `infra/workload-python/python/lakehouse_spark.py`: `ResolvingFileIO`, checkpoint key files and per-bucket S3A settings (marker retention `keep`), quieter known-harmless stream loggers.
- New `infra/rustfs/bootstrap-checkpoint-keys.py` (converge, rotate, remove, staged files and `.buckets.json`); `bootstrap-policies.py` compares condition values order-insensitively.
- `infra/airflow/lakehouse_dags/factory.py`, `compose.airflow.yml`: one key per run container.
- `infra/jupyter/hub/lakehouse_policy.py`, `lakehouse_spawner.py`, `jupyterhub_config.py`, `compose.jupyter.yml`: dev key mounts at spawn.
- `scripts/lakehouse.sh` (`rotate-checkpoint-keys`, key checks), product bootstrap, create and remove scripts.
- Verifiers `scripts/verify/checkpoint-keys.py`, `scripts/verify/checkpoint-stream.sh`; README "Streaming checkpoints"; tests (P1 to P4).

## Verification
- `python3 -m pytest -q tests`: 583 passed, 3 skipped (existing skips).
- Live: key bootstrap idempotent; key verifier 27/27; rotation refuses the old secret at once; stream verifier (batch 0, resume with 0 rows, a bucket without a key refused, cleanup); Airflow `default-uat-test_environment` 8/8 tasks with only the uat key mounted; the user's Jupyter check as `joe-developer` (`(0, 28) (1, 0)`, clean logs after the fixes).
- Not run: the uat refusal inside a notebook (covered by the verifier); a second product (only `default` exists).

## Deployment
Ordered steps are required: see [deploy_instructions.md](deploy_instructions.md).

## Risks and limitations
- Keys are shared per product environment, not per person; code in a Jupyter server can read its dev keys. A notebook and a dev stream with the same path share the checkpoint (accepted: dev is a sandbox).
- Rotation is manual (`rotate-checkpoint-keys`) and needs restarts of affected runs and servers.
- A new product membership needs a Jupyter server restart.
- Images grow by about 280 MB (AWS SDK v1 bundle next to Iceberg's SDK v2).
- Streams from Iceberg tables with delete or overwrite snapshots need `streaming-skip-*` options.
- Follow-up: an upstream Iceberg issue so `offsets/0` uses the checkpoint's filesystem.
