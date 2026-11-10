# Unit 3 Spark Runtime and Sample ETL — Logical Components

## Component View

Concrete Compose names, image choices, commands, environment variables, mounts, readiness probes, JDBC APIs, and retry durations are deferred to Infrastructure Design.

| Logical component | Responsibility | Readiness/operation contract |
|---|---|---|
| Operator/lifecycle interface | Starts the one-shot sequence and reviews per-step result states. | Explicit invocation; does not imply success from running containers. No scheduler or persistent worker. |
| TPCH generator adapter | Generates the existing scale factor 1 `.tbl` source set. | Requires writable workload input storage; receives no component credentials. Reports generated file inventory. |
| Run coordinator | Assigns run ID, validates prerequisites, sequences generator/ETL/JDBC, and aggregates manifest state. | Sequential execution; stages remain distinct. Reports `complete`, `partial`, or `failed`. |
| Credential/ticket adapter | Reads writer keytab reference, obtains short-lived Kerberos ticket, and supplies restricted cache reference. | Requires healthy KDC and readable protected keytab. Cache is removed on all exit paths. |
| Spark ETL adapter | Uses Spark/Iceberg with Hive Metastore and RustFS; creates or validates both databases and their eight-table sets. | Requires Spark, Hive, RustFS/bucket, writer ticket, writer S3 credentials, and complete inputs. Must report effective writer identity and per-table result. |
| Hive Metastore | Owns Iceberg catalog database/table metadata. | Health is necessary but does not prove writer DDL authorization. Conflicts stop modification. |
| RustFS | Owns S3 data objects for the Iceberg tables. | Writer key is restricted to approved warehouse prefixes. Health is necessary but does not prove path authorization. |
| Dremio JDBC adapter | Ensures one matching Space per Hive database and one view per table as the non-admin writer. | Runs only after successful ETL validation and Dremio readiness. Permission denial is distinct and never retried as admin. |
| Result manifest/report | Correlates source, database/table, row count, storage prefix, and Dremio outcome. | Contains no credential material; command output/logs are sufficient, no separate state database. |

## Readiness and Execution Flow

```text
KDC + Hive + RustFS/bucket + Spark + writer credentials + source files
                              |
                    TPCH generator (scale 1)
                              |
                    Spark ETL as writer
                    /                 \
        Hive catalog metadata       RustFS Iceberg objects
                    \                 /
                   ETL schema/count validation
                              |
                Dremio healthy and JDBC credentials
                              |
            Writer creates/validates Spaces and views
                              |
               Redacted manifest and final status
```

If ETL validation fails, JDBC is `not_attempted`. If JDBC fails after ETL validation, preserve data and report the overall run as `partial`.

## Credential and Data Boundaries

- Generator sees source-data paths only.
- Spark ETL sees the writer Kerberos keytab/cache reference and RustFS writer credential; it does not receive Dremio admin, RustFS root, or metastore PostgreSQL credentials.
- Dremio JDBC receives the Dremio writer credential only; no admin fallback exists.
- Hive owns metadata, RustFS owns table objects, and Dremio owns Space/view permissions. The run coordinator does not act as an authorization authority.
- Temporary ticket-cache material is isolated from generated source/data and reports, and is removed after the invocation.

## Failure Boundaries

- Missing readiness, incomplete source inputs, or unreadable protected credentials prevents ETL mutation.
- A table conflict stops writes to that target; completed earlier targets remain for diagnosis and safe rerun.
- Authentication/authorization failures are surfaced without broadening permissions or automatic retries.
- Dremio denial does not roll back Hive/RustFS output; it produces a partial result with the failed object/operation.
- No automatic deletion, replacement, rollback, or volume reset is performed.

## Cross-Cutting Constraints

- One sequential invocation on the local Compose host; no scale-out or performance SLA.
- Preserve pinned versions unless a capability gap is documented and reviewed.
- Keep published ports loopback-only and service calls private to the Compose network.
- Logs/manifests show identity and object outcomes while redacting credentials and ticket contents.
