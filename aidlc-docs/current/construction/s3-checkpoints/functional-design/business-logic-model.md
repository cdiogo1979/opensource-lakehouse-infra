# Business Logic Model — s3-checkpoints

## 1. Converge keys (C3, `bootstrap-checkpoint-keys.py [--product P] [--rotate] [--remove] [--dry-run]`)
```text
buckets = buckets of the product model (or of product P)
for bucket in buckets:
    validate bucket name                       -> refuse run on mismatch
    if --remove: remove user, policy, files    (R5); continue
    ensure canned policy checkpoints-<bucket>  == R1 document (put if absent or different)
    stored = read stored key (R10) or none
    if --rotate or user absent or stored none or stored key fails to authenticate:
        secret = new random secret
        add-user ckpt-<bucket> with secret     (create or replace)
        write stored then staged file          (R8, R9)
        report created | rotated
    else report unchanged
    attach exactly policy checkpoints-<bucket> to ckpt-<bucket>   (R2)
    ensure staged file equals stored file
delete staged files whose bucket is not in the model             (R6; full runs only)
```
The authentication check is a signed `ListObjectsV2` on `<bucket>?prefix=checkpoints/` with the stored key (expect 200). `--dry-run` reports the actions without RustFS writes or file changes.

## 2. Product lifecycle (C6)
- `bootstrap-default-product.sh`, `create-data-product.sh`: run C3 for the product right after `bootstrap-policies.py`.
- `remove-data-product.sh`: run C3 `--remove` for the product before `bootstrap-buckets.py --remove`; dry runs pass `--dry-run`.
- `lakehouse.sh rotate-checkpoint-keys [--product P]`: run C3 `--rotate`, then print the restart notice (R4).
- `lakehouse.sh start` / `start-airflow`: the R20 check only.

## 3. Airflow run (C4)
```text
create_cluster:
    bucket = product.environment(env).bucket      # env from the bundle: main -> prod, uat -> uat
    file = container view /run/secrets/checkpoint-keys/<bucket>
    require regular file, not symlink              (R11)
    volumes += { <LAKEHOUSE_CHECKPOINT_KEYS_HOST_DIR>/<bucket> : /run/secrets/lakehouse-checkpoints/<bucket> ro }
    create the container as today
```

## 4. Jupyter spawn (C5)
```text
check_current_admission:
    groups = current Keycloak groups (already read for admission)
    for product in products where groups contain product owner or developer group:
        bucket = product.environment("dev").bucket
        require staged file safe                    (R12, R13)
        volumes += { host/<bucket> : /run/secrets/lakehouse-checkpoints/<bucket> ro }
```

## 5. Spark session (C2)
```text
create_spark_session(app_name, catalog):
    settings = catalog_settings(catalog)            # io-impl ResolvingFileIO (R14)
    keys = checkpoint_key_files(/run/secrets/lakehouse-checkpoints)   # R10, R16
    settings += checkpoint_settings(keys, AWS_REGION)                 # R15, R16
    build the session as today
```
Iceberg table I/O: `s3://` goes through `ResolvingFileIO`, then `S3FileIO` with vended credentials. Spark checkpoint files and Iceberg `offsets/0` under `s3ckpt://<bucket>/…` go through `ResolvingFileIO`, then `HadoopFileIO`, then S3A with the per-bucket key.

## 6. Failure behavior
| Situation | Behavior |
|---|---|
| Staged key missing for a run | `create_cluster` fails, naming the bucket; no container is created |
| Staged key missing for an eligible Jupyter product | Spawn fails, naming the bucket |
| Invalid mounted key file | `create_spark_session` raises, naming the file |
| Checkpoint in a bucket without a key | S3A fails on first access (no credentials) |
| Checkpoint outside `checkpoints/` or in another bucket | RustFS refuses (403) |
| Key rotated while a job runs | The job's next checkpoint access fails (403); the run is retried or the server restarted |
| C3 RustFS call fails | Non-zero exit; files unchanged for that bucket; other buckets already done stay done |
| Notebook doesn't use checkpoints | No change in behavior (keys set but unused) |
