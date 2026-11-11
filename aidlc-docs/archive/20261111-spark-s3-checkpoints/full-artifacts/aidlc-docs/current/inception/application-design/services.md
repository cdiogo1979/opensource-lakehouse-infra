# Services — Spark S3 Checkpoints

No new runtime service. The work runs inside existing services and commands.

## Provisioning (C3, from C6)
1. `bootstrap-default-product.sh`, `create-data-product.sh`: after RustFS buckets and policies, converge one checkpoint key per product environment bucket, then stage the copies. `lakehouse.sh start` and `start-airflow` only check that every bucket has a staged key. Airflow and the Hub need no recreate: keys are mounted when each run or server starts (resolved in Functional Design).
2. `remove-data-product.sh`: remove the product's keys before its buckets.
3. `rotate-checkpoint-keys`: replace secrets; the old secret is refused at once, so running Airflow runs and open Jupyter servers fail their next checkpoint access until restarted.

## Airflow run (C4 → C2)
1. `create_cluster` mounts the one key for the run's product and environment (`prod` from the `-main` bundle, `uat` from `-uat`).
2. The job calls `start_spark_job` → `create_spark_session`; C2 reads the mounted key and sets the per-bucket S3A key.
3. Iceberg reads and writes tables with Polaris-vended credentials (`ResolvingFileIO` → `S3FileIO`). Spark's checkpoint files and Iceberg's `offsets/0` under `s3ckpt://` go through S3A with the checkpoint key.

## Jupyter session (C5 → C2)
1. At spawn, the Hub mounts the `dev` keys of the user's owner or developer products.
2. In a notebook, `create_spark_session` sets one per-bucket key per mounted file; the product's `dev.yml` names the bucket, so S3A picks the matching key. Notebooks of two products work in the same kernel.
3. A product added to the user later needs a server restart, as with the Hub's product model today.
