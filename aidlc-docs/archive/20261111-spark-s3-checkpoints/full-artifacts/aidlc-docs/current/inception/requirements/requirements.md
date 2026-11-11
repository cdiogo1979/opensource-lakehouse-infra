# Requirements — Spark S3 Checkpoints

## Intent Analysis
- **Request** (from the paused `opensource-lakehouse-sample-dp` intent `20261111-tpch-medallion`, Q5 and its probe follow-up): Spark Structured Streaming with a durable checkpoint location from the product's YAML config; the user chose to add S3 checkpoints to the platform.
- **Type**: platform enhancement with a new credential path (security-relevant). **Depth**: standard.
- **Answers**: Q1 to Q4 in `requirement-verification-questions.md`.

## Functional Requirements
- **FR-1 S3 filesystem in Spark** (amended by CR-1): the Spark runtime image (and so the Jupyter image, which copies `/opt/spark`) gains Hadoop S3A (`hadoop-aws` 3.3.4 and the matching AWS SDK bundle), verified by checksum at build. The platform maps the checkpoint scheme `s3ckpt://` to S3A (endpoint `http://rustfs:9000`, path-style access, region) and switches every Polaris catalog to Iceberg's `ResolvingFileIO`, so table paths (`s3://`) keep using `S3FileIO` with vended credentials while Iceberg's streaming offsets under `s3ckpt://` go through S3A.
- **FR-2 Checkpoint keys** (replaced by CR-1; was STS with the job's own token): one RustFS user per product environment bucket, `ckpt-<bucket>`, whose only policy allows `checkpoints/` of that bucket. Its keys are generated at bootstrap, stored under `.runtime/`, and mounted as one file per bucket; Spark selects the key by the checkpoint's bucket (S3A per-bucket settings). No root key and no key with table access reaches Spark.
- **FR-3 Location** (Q2 A; scheme amended by CR-1): checkpoints live under `checkpoints/` of each product environment bucket, outside the Polaris table locations, addressed as `s3ckpt://<bucket>/checkpoints/...`; products choose paths below it.
- **FR-4 Access** (Q3 A; amended by CR-1): a key allows object read, write, delete and listing only under `checkpoints/` of its one bucket. Airflow run containers receive only the key of their run's product and environment (`prod` or `uat`); Jupyter servers receive the `dev` keys of the products where the user is owner or developer, and no `uat` or `prod` key; analysts receive none. Jupyter and Airflow use the same `checkpoint_path` from the product's config (dev is a sandbox; accepted).
- **FR-5 Product contract**: products set `checkpoint_path` (for example `s3ckpt://bucket-default-dev/checkpoints`) in `configs/<env>.yml` and use it as the base of Spark's `checkpointLocation`; documented in the platform README.
- **FR-6 Verification**: a verifier exercises the allowed and refused cases per key (own `checkpoints/`, other prefixes, other buckets), and a streaming read of an Iceberg table with `trigger(availableNow=True)` resumes from its S3 checkpoint across two separate Spark sessions, in an Airflow run and in Jupyter.

## Non-Functional Requirements
- **NFR-1 Least privilege** (SECURITY-06): policies name exact buckets and the `checkpoints/` prefix and exact S3 actions; read and write in separate statements.
- **NFR-2 Key handling** (SECURITY-12; replaced by CR-1): keys are generated, never hard-coded; stored with mode 600 under `.runtime/credentials/`; staged read-only for containers; never in configs, images, logs, the Spark UI (redaction) or command lines; rotated by a platform command that replaces the secret (the old one is refused at once). Accepted limit: code in a Jupyter server can read that server's dev keys.
- **NFR-3 Fail closed** (SECURITY-15): a checkpoint in a bucket without a mounted key fails; there is no global key, no environment, instance or root credential fallback.
- **NFR-4 Supply chain** (SECURITY-10, SECURITY-13): exact versions, checksum-verified downloads from Maven Central.
- **NFR-5 Compatibility**: Iceberg table access keeps using Polaris-vended credentials; DAG runs and notebooks that don't use checkpoints are unaffected.

## Security Compliance (Requirements stage)
| Rule | Status | Note |
|---|---|---|
| SECURITY-01 Encryption | N/A for new data stores; in transit: RustFS is reached on the internal Docker network over HTTP, as today (local-only stack, documented limit) |
| SECURITY-02, 04, 07, 14 | N/A | no new network intermediary, web application, network rule or alerting |
| SECURITY-03 Logging | Required | the provider logs failures without token or credential values |
| SECURITY-05 Input validation | Required | key files are validated (regular file, not a symlink, expected fields) and bucket names checked against the product model |
| SECURITY-06 Least privilege | Required | NFR-1 |
| SECURITY-08 Access control | Required | FR-4, enforced by RustFS policies, verified by FR-6 |
| SECURITY-09 Hardening | Required | no default or root keys; path-style endpoint pinned |
| SECURITY-10, 13 Supply chain | Required | NFR-4 |
| SECURITY-11 Secure design | Required | key creation lives in the RustFS bootstrap, key selection in `lakehouse_spark`; a misuse case (one product reaching another's prefix) is verified |
| SECURITY-12 Credentials | Required | NFR-2: generated keys, no hard-coded credentials; password and session rules N/A (no new login) |
| SECURITY-15 Fail closed | Required | NFR-3 |

## Unknowns (Application Design probes) — resolved, see CR-1
- RustFS 1.0.4 `AssumeRoleWithWebIdentity` with the writer's and a user's Keycloak tokens (audience, claims), and how it maps them to policies.
- Whether checkpoint statements can join the existing group-named RustFS policies (used for the console) without widening console access, or need their own mapping.

## Change Record
### CR-1 (Application Design, 2026-11-11): static checkpoint keys instead of STS
- **Why**: probes showed (1) RustFS 1.0.4 STS accepts only tokens whose every audience is `rustfs`, so the job's token needs a Keycloak token exchange in both brokers plus a JVM credential provider with renewal; (2) Iceberg 1.10.2 writes `offsets/0` through the table's FileIO, fixed by `ResolvingFileIO` and a non-`s3` checkpoint scheme. The user chose the option with the least custom code: static per-bucket checkpoint keys ("lets proceed with static keys"), with the same checkpoint path in Jupyter dev ("Same path: simple; acceptable if dev is a sandbox.").
- **Changed**: FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, NFR-2, NFR-3, SECURITY-05, 11, 12 notes. Q1 A (job's own token) is superseded; STS stays a later option that changes only the platform's S3A credential settings.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes | Requirements Analysis (Q4: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q4: A) |
| Resiliency Baseline | No | Requirements Analysis (Q4: A) |
| Workflow Conventions | Yes (always enforced) | Workflow start |
