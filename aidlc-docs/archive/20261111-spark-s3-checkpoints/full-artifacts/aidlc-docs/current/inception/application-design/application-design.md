# Application Design — Spark S3 Checkpoints

Consolidates [components.md](components.md), [component-methods.md](component-methods.md), [services.md](services.md) and [component-dependency.md](component-dependency.md). Requirements: [requirements.md](../requirements/requirements.md), as amended by CR-1.

## Problem (from the probes)
A Structured Streaming job needs a durable checkpoint. Three gaps blocked one on S3:
1. The images have no Hadoop S3 filesystem.
2. Polaris vends credentials only for table locations.
3. Iceberg 1.10.2 reads and writes the stream's `<checkpoint>/sources/0/offsets/0` through the source table's FileIO (`S3FileIO` with table-scoped credentials).

Spark's own checkpoint files, Kafka or file sources, and Iceberg sinks were affected only by gaps 1 and 2.

## Decisions
| # | Decision | Reason |
|---|---|---|
| D1 | Add `hadoop-aws` 3.3.4 and `aws-java-sdk-bundle` 1.12.262 to the Spark runtime image | Matches the image's Hadoop client 3.3.4; Hadoop 3.4 (SDK v2) is not supported with Spark 3.5.5. Cost: about 280 MB per image |
| D2 | Every Polaris catalog uses Iceberg's `ResolvingFileIO` instead of `S3FileIO` | It sends `s3`, `s3a`, `s3n` to `S3FileIO` (vended credentials, prefix and bulk operations kept) and other schemes to `HadoopFileIO`; no custom FileIO |
| D3 | Checkpoints use the scheme `s3ckpt://`, mapped to S3A; `s3://` and `s3a://` stay unmapped | Routes Iceberg's `offsets/0` to S3A; table paths are unaffected |
| D4 | One static key per product environment bucket: RustFS user `ckpt-<bucket>` with the canned policy `checkpoints-<bucket>` (`checkpoints/` of that bucket only) | Least custom code (the user's choice over STS); no runtime credential flow |
| D5 | Key files named by bucket; `lakehouse_spark` sets S3A per-bucket keys and no global key | Several products in one Jupyter kernel; fail closed for any other bucket |
| D6 | Airflow run containers get only their run's key (`prod` or `uat`); Jupyter servers get the `dev` keys of the user's owner or developer products; analysts get none | Narrowest delivery; uat and prod keys never reach Jupyter |
| D7 | Jupyter and Airflow use the product's `checkpoint_path` as is | User: dev is a sandbox. In practice they don't overlap, since Airflow runs only `prod` and `uat` |
| D8 | Rotation replaces the secret in place | Probed: the old secret is refused at once; restart running jobs and servers |

## Exception to the canonical access rule
The canonical rule "Workloads never receive root or static RustFS credentials" (`knowledge/.../lakehouse-product-access.md`, `application-design.md`) gains one bounded exception: **checkpoint keys**, which are static, non-root, and limited to `checkpoints/` of one bucket. Table data access still goes only through Polaris vending. The canonical texts are updated at closure.

## Probe evidence (`audit.md`, probes 1 to 6)
| Probe | Result |
|---|---|
| STS with the writer token | Refused: RustFS 1.0.4 trusts only the audience `rustfs`, and every audience must be trusted |
| Token exchange to `rustfs`, STS with session policy | Credentials limited to `checkpoints/` (other prefixes and buckets refused); kept as the later STS option |
| S3A + `S3FileIO` | Spark checkpoint metadata written; Iceberg `offsets/0` 403 |
| S3A + `ResolvingFileIO` + `s3ckpt://` | availableNow stream ran (batch 0, 28 rows) and resumed (batch 1, 0 rows); writes outside `checkpoints/` refused |
| Static key (service account, then plain user) | The same stream works; own `checkpoints/` allowed, table prefix, other prefixes and other buckets refused, ListAllMyBuckets refused; rotation refuses the old secret |

Every temporary realm change, key, user and policy was removed after its probe.

## Accepted limits
- **Shared keys**: a key belongs to a product environment, not to a person. Code in a Jupyter server can read that server's dev keys.
- **Rotation**: manual, through `rotate-checkpoint-keys`, with restarts.
- **Membership changes**: a new product membership needs a Jupyter server restart.
- **Delete snapshots**: streams from tables with delete or overwrite snapshots need Iceberg's `streaming-skip-delete-snapshots` and `streaming-skip-overwrite-snapshots`, which are the product's choice (documented).
- **Image size**: about 280 MB more per image.

## Later options (not in scope)
- STS per identity: token exchange in both brokers, plus a JVM S3A credentials provider beside `LakehouseTokenAuthManager`. Only the platform's credential settings change.
- An upstream Iceberg issue proposing that `offsets/0` be written through the checkpoint's Hadoop filesystem, which would make D3's scheme unnecessary.

## Canonical knowledge impact (updated inventory)
| Path | Action | Reason |
|---|---|---|
| `application-design.md` | UPDATE | Spark storage access: `ResolvingFileIO`, `s3ckpt://`, checkpoint keys, and the exception to the static-credential rule |
| `functional-design/lakehouse-product-access.md` | UPDATE | Checkpoint policies and users per bucket, delivery by role, lifecycle and rotation |
| `functional-design/workload-python-environment.md` | UPDATE | Session settings and the `checkpoint_path` contract |
| `functional-design/airflow-workflows.md` | UPDATE (was RETAIN) | The run container mounts the run's checkpoint key |
| `functional-design/jenkins-ci-access.md`, `starrocks-sql-access.md` | RETAIN | Unaffected |

## Security Baseline compliance (Application Design)
| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | Compliant (documented limit) | Internal HTTP to RustFS, as today |
| SECURITY-02, 04, 07, 14 | N/A | No new intermediary, web application, network rule or alerting |
| SECURITY-03 | Compliant (design) | Failures are logged by bucket and reason, never with key values |
| SECURITY-05 | Compliant (design) | Key files and bucket names validated (C2, C4, C5) |
| SECURITY-06 | Compliant | One bucket, one prefix, exact actions per key (D4, D6) |
| SECURITY-08 | Compliant (design) | RustFS enforces the policies; C7 verifies refused cases, including the cross-product misuse case |
| SECURITY-09 | Compliant | No root or default keys in Spark; endpoint pinned |
| SECURITY-10, 13 | Compliant (design) | Pinned versions; Maven strict checksums |
| SECURITY-11 | Compliant | Responsibilities isolated in C2 and C3; misuse case verified |
| SECURITY-12 | Compliant | Generated keys, none hard-coded; files mode 600, mounts read-only, redacted in Spark |
| SECURITY-15 | Compliant | No global or fallback key (D5) |

## Property-Based Testing (partial)
PBT-02, 03, 07, 08 and 09 apply in Functional Design and Code Generation:
- policy generation (`checkpoint_policy`: only its bucket, only `checkpoints/`);
- bucket selection (`checkpoint_buckets`: never `uat` or `prod`, never non-member products);
- settings generation (`checkpoint_settings`: one per-bucket key per file, no global key).

No PBT rule applies at this stage.

## Open points for Functional Design
- The exact admin API calls and idempotency rules for C3, and the staging-folder permissions (container users must read the files).
- How the Hub validates host paths for the key files (the broker CA pattern).
- Whether `lakehouse.sh start` recreates Airflow and the Hub when the staged set changes, as it does for writers.
