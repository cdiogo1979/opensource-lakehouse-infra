# Unit 3 Spark Runtime and Sample ETL — Technology Decisions

## Decisions

| Area | Decision | Rationale and status |
|---|---|---|
| Data scale | Use TPCH scale factor 1 and the existing eight-table source set for both Hive databases. | User selected the current generator default and fixed PoC size; no scale SLA is added. |
| Workload execution | Run generator and ETL as explicit one-shot local Compose/operator actions. | No persistent scheduler is required; Airflow/Jenkins is deferred. |
| Catalog and storage | Configure Spark's Iceberg catalog to Hive Metastore and store table data in RustFS under the approved database warehouse prefixes. | Carries forward Unit 1 and approved Unit 3 Functional Design; exact Spark configuration remains Infrastructure Design work. |
| ETL identity | Use the provisioned `write-service-account` principal and its distinct RustFS key. | Required by approved requirements. Do not expose admin, RustFS root, or metastore PostgreSQL credentials to ETL. |
| Kerberos login | Acquire a short-lived ticket from the writer keytab and provide the protected ticket-cache path to Spark local mode. | Unit 2 local-mode smoke succeeded with a cache; Spark standalone `--principal/--keytab` behavior did not. The intended execution mode must be validated before claiming keytab login compatibility. |
| Safe rerun | Create only missing databases/tables; validate existing schema and row counts; fail on conflict without replacing/appending/deleting data. | Prevents the current loader's `createOrReplace` behavior from destructively affecting persistent PoC data. |
| Dremio JDBC | Attempt Space/view setup as the non-admin writer after ETL validation; treat denied access as a separate partial result. | Preserves the approved privilege boundary and the functional design's feasibility gate. Never retry as admin. |
| Reporting | Emit concise per-database/table counts and per-Space/view status with redacted diagnostics. | Sufficient for one local operator; no separate report store or monitoring service. |
| Compatibility policy | Preserve current pinned component versions. Return unsupported behavior and the smallest proposed change for review. | Avoids changing versions or permission scope to make the run appear successful. |

## Compatibility Evidence and Validation Boundary

Unit 2 verified Spark local-mode access to the Hive namespace with a pre-authenticated Kerberos ticket cache. It did not verify writer DDL/table creation with the writer identity, full TPCH ETL, Dremio JDBC Space/view permissions, or ticket acquisition from the keytab inside the eventual Unit 3 execution wrapper. Those are Build and Test gates.

The following remain explicit verification gates:

1. Spark, Iceberg, Hive Metastore, and RustFS work together for DDL and table reads/writes with the pinned versions.
2. Writer keytab acquisition and ticket-cache delivery work in the actual local execution mode, and temporary cache material is removed on every exit path.
3. The writer is limited to the intended Hive databases and RustFS warehouse prefixes.
4. Dremio Community JDBC permits the non-admin writer to create Spaces and views. A denial remains a partial result and is not bypassed with admin credentials.
5. Existing tables can be recognized and validated without invoking destructive replacement semantics.

If a gate fails, preserve existing data and credential boundaries, record evidence, and request review for the smallest change. Do not change image versions, grant admin privileges, or reset volumes implicitly.

## Deferred Infrastructure Decisions

1. Exact Compose service/command for the one-shot generator and loader.
2. Runtime mounts and environment/file references for the writer keytab, ticket cache, and RustFS key.
3. Concrete Spark catalog, warehouse, and Kerberos configuration.
4. Deterministic source-to-table and Hive-table-to-Dremio-view path serialization.
5. Readiness probes and bounded retry timings.
6. Safe manifest persistence/output path and temporary credential cleanup implementation.

These decisions belong to NFR Design and Infrastructure Design and do not change the approved scope.
