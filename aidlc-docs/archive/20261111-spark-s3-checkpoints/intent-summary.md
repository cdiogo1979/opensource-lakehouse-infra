# Intent Summary: Spark S3 Checkpoints

## Intent
Spark S3 Checkpoints (`20261111-spark-s3-checkpoints`)

## Objective
Durable Spark Structured Streaming checkpoints in each product's bucket under checkpoints/, for Airflow runs and Jupyter, including streams from Iceberg tables (requested by the paused opensource-lakehouse-sample-dp intent 20261111-tpch-medallion).

## Date
2026-11-11

## Scope
Included: S3A jars in the Spark images, ResolvingFileIO and the s3ckpt:// scheme in lakehouse_spark, per-bucket RustFS checkpoint keys (bootstrap, rotation, removal), key delivery in the DAG factory and the Hub spawner, operations scripts, verifiers, README, tests. Excluded: STS per identity (later option), per-user Jupyter checkpoint paths, an upstream Iceberg change, the sample-dp TPC-H workload itself.

## Units / workstreams
s3-checkpoints

## Major requirements
- FR-1: S3A in the Spark images; s3ckpt:// on S3A; ResolvingFileIO for every catalog.
- FR-2 (CR-1): one static checkpoint key per product environment bucket, ckpt-<bucket> with checkpoints-<bucket> only.
- FR-3/FR-5: checkpoints under <bucket>/checkpoints/; products set checkpoint_path: s3ckpt://<bucket>/checkpoints.
- FR-4 (CR-1): Airflow runs get their own prod or uat key; Jupyter gets dev keys of owner or developer products; analysts none; no global key.
- NFR: least privilege, fail closed, generated keys never printed, pinned and checksum-verified jars.

## Architecture and design decisions
- Iceberg 1.10.2 writes sources/0/offsets/0 through the source table's FileIO; ResolvingFileIO plus a dedicated non-s3 scheme routes it to Hadoop S3A without a custom FileIO.
- Static per-bucket keys chosen over STS with token exchange (least custom code); STS stays the upgrade path changing only platform S3A credential settings.
- Keys are selected per bucket by S3A, so several products work in one Jupyter kernel.
- Bounded exception to 'workloads never receive static RustFS credentials': checkpoint keys only, non-root, one bucket and prefix.
- Rejected: checkpoints in table folders, FUSE mounts, a custom Java FileIO, snapshot bookkeeping instead of streaming.

## Implementation decisions
- Plain RustFS users (not service accounts) with canned policies; rotation re-adds the user with a new secret, refusing the old one at once.
- A non-secret .buckets.json index lets the Airflow scheduler mount a run's key without the product model; the Hub uses the product model.
- S3A directory marker retention keep (parent marker deletes up to checkpoints/ were refused); known-harmless stream loggers lowered to ERROR after session start.
- canonical_policy compares condition values order-insensitively (RustFS reorders them).

## Deviations
- CR-1 replaced the approved STS requirement after probes showed RustFS trusts only the rustfs audience and the user chose static keys.
- start only warns about missing keys (first bootstrap runs start before keys exist); start-airflow refuses.
- The stream verifier app lives in infra/spark-bootstrap; P3 and P4 live in test_spark_session.py.
- Build and Test added the condition-order fix, marker retention and quiet loggers.

## Verification
construction/build-and-test/build-and-test-summary.md: host 583 passed, 3 skipped; live key bootstrap idempotent, key scope 27/27, rotation, stream verifier (batch 0, resume with 0 rows, bucket without key refused), default-uat-test_environment 8/8 with only the uat key; user-confirmed Jupyter check as joe-developer ((0, 28) (1, 0)). Not run: a second product, a production run.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/workload-python-environment.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/airflow-workflows.md

## Superseded decisions
- Q1 'STS with the job's own token' superseded by static checkpoint keys (CR-1).
- Checkpoint paths s3://<bucket>/checkpoints/ superseded by s3ckpt://<bucket>/checkpoints/ (Iceberg offsets routing).
- Catalog io-impl S3FileIO superseded by ResolvingFileIO.

## Archived artifacts
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/workload-python-environment.md
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/airflow-workflows.md
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/infra/spark-runtime/Dockerfile
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/infra/workload-python/python/lakehouse_spark.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/infra/rustfs/bootstrap-checkpoint-keys.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/infra/rustfs/bootstrap-policies.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/infra/airflow/lakehouse_dags/factory.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/infra/jupyter/hub/lakehouse_policy.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/infra/jupyter/hub/lakehouse_spawner.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/infra/jupyter/hub/jupyterhub_config.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/infra/spark-bootstrap/verify_checkpoint_stream.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/compose.airflow.yml
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/compose.jupyter.yml
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/scripts/lakehouse.sh
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/scripts/bootstrap-default-product.sh
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/scripts/operations/create-data-product.sh
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/scripts/operations/remove-data-product.sh
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/scripts/verify/checkpoint-keys.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/scripts/verify/checkpoint-stream.sh
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/README.md
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/tests/rustfs/test_checkpoint_keys.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/tests/rustfs/strategies.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/tests/workload_env/test_spark_session.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/tests/workload_env/test_image_contracts.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/tests/airflow/test_dag_factory.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/tests/jupyterhub/test_checkpoint_key_mounts.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/tests/operations/test_data_product_scripts.py
- aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/tests/operations/test_compose_modules_contract.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261111-spark-s3-checkpoints/full-artifacts/`
