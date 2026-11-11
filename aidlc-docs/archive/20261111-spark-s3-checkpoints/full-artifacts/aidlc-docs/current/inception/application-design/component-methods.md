# Component Methods — Spark S3 Checkpoints

Signatures and purpose only; rules and edge cases are detailed in Functional Design.

## C2 `lakehouse_spark`
| Method | Input → Output | Purpose |
|---|---|---|
| `catalog_settings(default_catalog)` (changed) | `str` → `dict[str, str]` | As today, with `io-impl` = `org.apache.iceberg.io.ResolvingFileIO` for every catalog |
| `checkpoint_key_files(directory=CHECKPOINT_KEY_DIR)` (new) | `Path` → `dict[str, CheckpointKey]` | Read `/run/secrets/lakehouse-checkpoints/<bucket>` files; refuse symlinks, non-files, bad names or fields; an absent folder gives `{}` |
| `checkpoint_settings(keys, region)` (new) | `dict[str, CheckpointKey]`, `str` → `dict[str, str]` | Global S3A settings plus `spark.hadoop.fs.s3a.bucket.<bucket>.access.key/secret.key` per key |
| `create_spark_session(app_name, catalog)` (changed) | as today | Merges `checkpoint_settings` into the session builder |

Global S3A settings: `fs.s3ckpt.impl=org.apache.hadoop.fs.s3a.S3AFileSystem`, `fs.s3a.endpoint=http://rustfs:9000`, `fs.s3a.endpoint.region=<AWS_REGION>`, `fs.s3a.path.style.access=true`, `fs.s3a.connection.ssl.enabled=false`, `fs.s3a.aws.credentials.provider=org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider` (no global keys, so a bucket without its own key fails). `s3://` and `s3a://` are not mapped to S3A.

## C3 `bootstrap-checkpoint-keys.py`
| Method | Input → Output | Purpose |
|---|---|---|
| `checkpoint_policy(bucket)` | `str` → `dict` | ListBucket with prefix `checkpoints/*` or `checkpoints`; Get/Put/DeleteObject on `<bucket>/checkpoints/*` |
| `ensure_key(client, bucket, *, rotate=False, dry_run=False)` | → `str` (`created`, `unchanged`, `rotated`) | Converge policy, user, policy attachment and the stored secret; with `rotate`, write a new secret |
| `remove_key(client, bucket, dry_run=False)` | → `str` | Remove user and policy, delete stored and staged files |
| `stage_keys(buckets)` | `Iterable[str]` → `None` | Write the staged copies for container mounts; remove stale ones |
| `main(argv)` | CLI: `--product`, `--rotate`, `--remove`, `--dry-run`, `--list` | Entry point used by C6 |

## C4 factory
| Method | Input → Output | Purpose |
|---|---|---|
| `_checkpoint_key_volume(product, environment)` (new) | → `dict[str, dict]` | Host path of the run's key file → `/run/secrets/lakehouse-checkpoints/<bucket>` (ro); fails when absent |
| `_create_spark_container(...)` (changed) | as today | Adds that volume |

## C5 spawner
| Method | Input → Output | Purpose |
|---|---|---|
| `checkpoint_buckets(groups, products)` (new) | `Iterable[str]`, products → `tuple[str, ...]` | `dev` buckets where a group is the product's owner or developer group |
| `check_current_admission(spawner)` (changed) | as today | Adds one read-only volume per bucket |

## C6 operations
- `lakehouse.sh start` and the product commands: call C3 (converge and stage) after RustFS policies.
- `lakehouse.sh rotate-checkpoint-keys [--product <name>]`: C3 with `--rotate`; prints which Jupyter servers and Airflow runs must restart.

## C7 verification
- `scripts/verify/checkpoint-keys.py`: per key, allowed and refused S3 operations (own prefix, other prefix, other buckets, ListAllMyBuckets).
- Smoke stream: Iceberg availableNow stream with an `s3ckpt://` checkpoint, run twice, resumes with no reprocessing.
