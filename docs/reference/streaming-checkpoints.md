# Streaming checkpoints

Reference for developers writing Spark Structured Streaming jobs. Back to the [README](../../README.md).

Spark Structured Streaming jobs keep their checkpoints in their product bucket, under `checkpoints/`, in Airflow runs and in Jupyter.

- **Product contract**: set `checkpoint_path: s3ckpt://<bucket>/checkpoints` in `configs/<env>.yml` (your own environment bucket, for example `s3ckpt://bucket-default-dev/checkpoints`), and give each stream its own subpath as `checkpointLocation`, such as `<checkpoint_path>/<project>/<target_table>`.
- **Why `s3ckpt://`**: Iceberg writes a stream's initial offset through the source table's FileIO. Every catalog uses Iceberg's `ResolvingFileIO`, so `s3://` table paths go to `S3FileIO` with Polaris-vended credentials, and `s3ckpt://` goes to Hadoop S3A with the checkpoint key. `s3://` and `s3a://` checkpoints are not supported.
- **Keys**: one RustFS user per product environment bucket, `ckpt-<bucket>`, whose only policy (`checkpoints-<bucket>`) allows listing, reading, writing and deleting below that bucket's `checkpoints/`. They are created by the product bootstrap (`infra/rustfs/bootstrap-checkpoint-keys.py`), stored in `.runtime/credentials/checkpoint-keys/` and staged in `.runtime/container-mounts/checkpoint-keys/`, and never printed.
- **Who gets which key**:
  - an Airflow run gets only its product environment's key (`prod` from `<product>-main`, `uat` from `<product>-uat`), and fails at `create_cluster` if it is missing;
  - a Jupyter server gets the `dev` keys of the products where the user is owner or developer, and never a `uat` or `prod` key; analysts get none;
  - a checkpoint in a bucket without a mounted key fails: there is no global or fallback key.
- **Shared keys**: a key belongs to a product environment, not to a person, so code in a Jupyter server can read its dev keys, and a notebook and a dev stream with the same path share the checkpoint. A new product membership needs a server restart.
- **Rotation**: `./scripts/lakehouse.sh rotate-checkpoint-keys [--product FILE]` replaces the secrets. The old secrets are refused at once, so restart the affected Airflow runs and Jupyter servers.
- **Quiet logs**: `create_spark_session` logs only errors from three loggers whose stream warnings need no action (`CheckpointFileManager`'s FileContext fallback, `ResolveWriteToStream`, S3A's `MetricsConfig`). S3 renames are not atomic, so keep one writer per checkpoint. Hadoop's one `NativeCodeLoader` line per session remains.
- **Iceberg sources with deletes**: a stream fails on a source snapshot that deletes or overwrites data, unless it sets `streaming-skip-delete-snapshots` or `streaming-skip-overwrite-snapshots` (the job's choice: skipped changes are not applied).
- **Checks**: `python3 scripts/verify/checkpoint-keys.py` checks every key's allowed and refused access; `scripts/verify/checkpoint-stream.sh` runs an Iceberg stream twice in separate sessions and checks that the second resumes with no reprocessing.
