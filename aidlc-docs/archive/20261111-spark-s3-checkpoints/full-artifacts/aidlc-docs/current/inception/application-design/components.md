# Components — Spark S3 Checkpoints

All components exist today except C3, which is a new script inside the existing RustFS bootstrap component. One unit of work: `s3-checkpoints`.

| ID | Component | Location | Change |
|---|---|---|---|
| C1 | Spark images | `infra/spark-runtime/Dockerfile` (the Jupyter image copies `/opt/spark`) | Add `hadoop-aws` 3.3.4 and `aws-java-sdk-bundle` 1.12.262 |
| C2 | Platform Spark session | `infra/workload-python/python/lakehouse_spark.py` | `ResolvingFileIO` for every catalog; `s3ckpt://` on S3A; per-bucket checkpoint keys from mounted files |
| C3 | RustFS checkpoint keys | new `infra/rustfs/bootstrap-checkpoint-keys.py` | Policy, user and key per product environment bucket; rotate; remove; stage |
| C4 | Airflow DAG factory | `infra/airflow/lakehouse_dags/factory.py` | Mount the run's one key file into the run container |
| C5 | JupyterHub spawner | `infra/jupyter/hub/lakehouse_spawner.py`, `jupyterhub_config.py` | Mount the user's `dev` key files |
| C6 | Platform operations | `scripts/lakehouse.sh`, `scripts/bootstrap-default-product.sh`, `scripts/operations/create-data-product.sh`, `remove-data-product.sh`, `compose.*.yml` | Run C3 in the product lifecycle; key check at start; mount the staging folder into Airflow and the Hub; a `rotate-checkpoint-keys` command |
| C7 | Verification and docs | `scripts/verify/`, `tests/`, `README.md` | Checkpoint verifier; contract tests; product contract `checkpoint_path` |

## Responsibilities
- **C1** provides the S3A filesystem classes to every Spark process (driver and executors, Airflow and Jupyter). Downloads are pinned and checksum-verified by Maven (`--strict-checksums`).
- **C2** remains the only place that configures Spark storage access. It keeps Polaris-vended credentials for table data and adds checkpoint access only for buckets whose key file is mounted. It sets no global key, so any other `s3ckpt://` bucket fails.
- **C3** owns the RustFS identities for checkpoints: canned policy `checkpoints-<bucket>`, user `ckpt-<bucket>` with only that policy, a generated secret stored in `.runtime/credentials/checkpoint-keys/<bucket>` (mode 600), and a staged copy in `.runtime/container-mounts/checkpoint-keys/<bucket>` for container mounts. It converges idempotently with the product model and never prints secrets.
- **C4** chooses exactly one key, `bucket(product, environment)` of the run, and bind-mounts it read-only. A missing key file fails the run's `create_cluster` task.
- **C5** at spawn chooses the `dev` buckets of the products where the user's current groups include owner or developer, and bind-mounts those files read-only. A user with no such product gets no key. A missing key file for an eligible product fails the spawn.
- **C6** wires C3 into the existing ordering (after the RustFS buckets and policies; before Airflow and the Hub start), and removes keys before buckets on product removal.
- **C7** proves the allowed and refused cases and the resume behavior, and documents the contract.

## Interfaces
- **Key file** (C3 → C4, C5 → C2): `<dir>/<bucket>`, JSON `{"access_key": "ckpt-<bucket>", "secret_key": "<generated>"}`; container path `/run/secrets/lakehouse-checkpoints/<bucket>`.
- **Product contract** (products → C2): `checkpoint_path: s3ckpt://<bucket>/checkpoints` in `configs/<env>.yml`; products append their own subpath, such as `<project>/<target_table>`.
- **Spark settings** (C2 → Spark): see component-methods.md.
