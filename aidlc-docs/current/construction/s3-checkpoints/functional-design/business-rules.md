# Business Rules — s3-checkpoints

## Policy and identity (C3)
- **R1 Policy document**: exactly two allow statements, nothing else:
  1. `s3:ListBucket` on `arn:aws:s3:::<bucket>` with `StringLike` `s3:prefix` in `["checkpoints", "checkpoints/*"]`;
  2. `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` on `arn:aws:s3:::<bucket>/checkpoints/*`.

  There are no wildcards in bucket names, no `admin:` actions and no `ListAllMyBuckets`. `s3:AbortMultipartUpload` and `s3:ListMultipartUploadParts` on the same object resource are added only if Build and Test shows S3A needs them for checkpoint files (small files use single PUTs).
- **R2 One user per bucket**: user `ckpt-<bucket>`, enabled, with exactly the policy `checkpoints-<bucket>` attached. Converge removes any other attachment.
- **R3 Converge is idempotent**: an existing user whose stored key authenticates is `unchanged`; a missing user is `created` with a new secret; a user whose stored key is missing or doesn't match is re-keyed (`rotated`) with a notice. A run never prints a secret.
- **R4 Rotation**: `--rotate` writes a new secret to the user first, then atomically replaces the stored and staged files. If the RustFS call fails, the files are unchanged. The output names the bucket and the restarts needed (Airflow runs of that product environment; Jupyter servers of that product's owners and developers for `dev`).
- **R5 Removal**: `--remove` deletes the user, then the policy, then the stored and staged files. A missing item is not an error. It runs before the product's buckets are removed.
- **R6 Scope**: C3 acts only on buckets of the product model (all products, or `--product <name>`). Staged files for buckets no longer in the model are deleted.
- **R7 Root key**: C3 runs on the host with the RustFS root key read from `.runtime/credentials/` (as `bootstrap-policies.py` does); the root key never leaves the host process.

## Files
- **R8 Stored files**: `.runtime/credentials/checkpoint-keys/` mode 700, files 600; written to a temporary file in the same folder, then renamed.
- **R9 Staged files**: `.runtime/container-mounts/checkpoint-keys/` mode 755, files 644 (containers run as another user), written the same way.
- **R10 Key file format**: a JSON object with exactly `access_key` (equal to `ckpt-<file name>`) and `secret_key` (non-empty string). Anything else is invalid.

## Delivery
- **R11 Airflow**: `create_cluster` mounts `<host dir>/<bucket(product, env)>` read-only at `/run/secrets/lakehouse-checkpoints/<bucket>`. The task fails before any container starts if the staged file is missing, is a symlink, or is not a regular file. No other key is mounted.
- **R12 Jupyter**: at spawn, the Hub computes `dev` buckets from the user's current groups (owner or developer group of a product) and mounts each staged file read-only. A user with no such product gets none (the spawn continues). An eligible bucket with a missing or unsafe file fails the spawn with a message naming the bucket. `uat` and `prod` files are never mounted, whatever the groups.
- **R13 Host paths**: Airflow and the Hub receive the host folder path (`LAKEHOUSE_CHECKPOINT_KEYS_HOST_DIR`, `JUPYTERHUB_CHECKPOINT_KEYS_HOST_DIR`). They validate it is absolute and ends in `checkpoint-keys`, and check files through a read-only in-container mount of the same folder (`/run/secrets/checkpoint-keys`), as for the broker CA.

## Spark session (C2)
- **R14 FileIO**: every catalog's `io-impl` is `org.apache.iceberg.io.ResolvingFileIO`; all other catalog settings are unchanged.
- **R15 Global S3A settings**: always set, whether or not keys are mounted: `fs.s3ckpt.impl`, endpoint `http://rustfs:9000`, `endpoint.region` from `AWS_REGION` (default `us-east-1`), path-style access, SSL off, credentials provider `SimpleAWSCredentialsProvider`, and no global `access.key` or `secret.key`.
- **R16 Per-bucket keys**: for each valid mounted file, `spark.hadoop.fs.s3a.bucket.<bucket>.access.key` and `.secret.key`. Invalid files (R10, symlinks, non-files, names failing the bucket pattern) stop session creation with an error naming the file, never its content. An absent folder means no per-bucket keys.
- **R17 Redaction**: the existing redaction regex (`secret|password|token|access[.]?key|credential`) covers the new settings in the Spark UI and logs. The settings are not printed by platform code.
- **R18 Fail closed**: an `s3ckpt://` path in a bucket without a per-bucket key fails at its first S3 call (no credentials). `s3://` and `s3a://` are not mapped to S3A.

## Product contract
- **R19**: products set `checkpoint_path: s3ckpt://<bucket>/checkpoints` in `configs/<env>.yml`, using their own environment bucket, and append their own subpath. The platform README documents this, the scheme, the Jupyter and Airflow key delivery, and the Iceberg `streaming-skip-*` options for sources with delete or overwrite snapshots.

## Startup checks
- **R20**: `lakehouse.sh start` (when Jupyter is enabled) and `start-airflow` check that every product environment bucket has a staged key, and fail with a hint to run the product bootstrap. They create no keys themselves.

## Property-based tests (PBT partial)
- **P1** (R1): for any valid bucket name, the policy names only that bucket, only `checkpoints` prefixes or `checkpoints/*` objects, and exactly the listed actions.
- **P2** (R12): for any generated product model and group set, the selected buckets are a subset of `dev` buckets of products where a group is the owner or developer group. They never include `uat` or `prod`.
- **P3** (R15, R16): for any set of valid key files, the settings contain exactly one access and one secret key per bucket, and no global key.
- **P4** (R10): any key file that isn't exactly the two valid fields is rejected (round trip of valid files accepted).
