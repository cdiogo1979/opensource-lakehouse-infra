# Focused Reverse Engineering — Spark S3 Checkpoints

Intent `20261111-spark-s3-checkpoints`, opened for the paused `opensource-lakehouse-sample-dp` intent `20261111-tpch-medallion` (its silver notebook needs Spark Structured Streaming with a durable checkpoint). Captured 2026-11-11.

## Probe results (2026-11-11, Spark runtime image, writer `srv-default-writer`, dev)
- `spark.range(1).write.json("s3a://bucket-default-dev/checkpoints/...")`: `ClassNotFoundException: org.apache.hadoop.fs.s3a.S3AFileSystem`. The image has `hadoop-client-api`/`hadoop-client-runtime` 3.3.4 and no `hadoop-aws` or AWS SDK bundle.
- Iceberg streaming source with a local checkpoint: `Invalid S3 URI, cannot determine scheme: file:/tmp/...`. Iceberg 1.10.2 writes the source's offsets into `<checkpoint>/sources/0` through the table's FileIO (`S3FileIO`, `s3://` only).
- Checkpoint at `s3://...`: `UnsupportedFileSystemException: No FileSystem for scheme "s3"` (Spark's own checkpoint files use Hadoop).
- Works: Iceberg tables at explicit locations, appends, `MERGE INTO`, incremental batch reads between snapshots, table properties.

## What a checkpoint needs
1. **A Hadoop filesystem for S3** in the Spark runtime image (also copied into the Jupyter image): `hadoop-aws` 3.3.4 and its `aws-java-sdk-bundle` (1.12.262), with the `s3`/`s3a` scheme mapped to S3A (so Spark's checkpoint files and Iceberg's offsets share one path form), path-style access to RustFS (`http://rustfs:9000`).
2. **Credentials for the checkpoint prefix**, in Airflow runs (writer identity, run-scoped) and in Jupyter (the user's identity). Today Spark has none outside Polaris-vended, per-table credentials; the canonical design states "no RustFS root credential is handed to Spark" and "Workloads never receive root or static RustFS credentials".

## Existing pieces
- **RustFS OIDC**: `RUSTFS_IDENTITY_OPENID_*` with Keycloak (client `rustfs`, claim `groups`); `infra/rustfs/bootstrap-policies.py` maps each `groups` value to a policy of the same name (console use). RustFS supports STS (`scripts/verify/rustfs-sts.py` verifies `AssumeRole` with a session policy limited to one environment prefix, using root keys).
- **Token flow**: Airflow runs get a writer access token and renewal from the run broker; Jupyter gets the user's token from the Hub broker; `LakehouseTokenAuthManager` (Java) renews tokens for Iceberg.
- **Buckets**: one per product and environment (`bucket-default`, `-uat`, `-dev`), Polaris table locations under `s3://<bucket>/<catalog>/<namespace>/`.

## Unknowns for the design
- Whether RustFS 1.0.4 `AssumeRoleWithWebIdentity` accepts the writer's and users' Keycloak tokens (audience, `groups` claim), and how policies limit them to a checkpoint prefix.
- A Hadoop S3A credential provider that renews from the existing token sources.
