# Unit 3 Spark Runtime and Sample ETL — Business Logic Model

## Purpose

Run the existing TPCH generator and Spark loader as `write-service-account`, create equivalent Iceberg table sets in Hive databases `databaseA` and `databaseB`, store table data in RustFS, and attempt to expose each table through a same-name Dremio view in the matching Space over JDBC. ETL success and Dremio JDBC setup are separate outcomes.

## Actors and Components

| Actor/component | Responsibility |
|---|---|
| Operator | Starts the one-shot workload after Unit 1/2 prerequisites are healthy; reviews redacted manifest and partial-result status. |
| TPCH generator | Produces the existing scale-factor-controlled `.tbl` inputs. It does not access Hive, RustFS, or Dremio. |
| TPCH loader | Acquires/uses the writer Kerberos identity, configures Spark for Hive Metastore and RustFS, creates/populates the two databases, validates results, and reports table metadata/counts. |
| Kerberos KDC | Issues a short-lived ticket for the provisioned `write-service-account` principal from its protected keytab. |
| Hive Metastore | Stores database/table metadata and exposes the Iceberg catalog to Spark. |
| RustFS | Stores Iceberg data and metadata objects under the writer-approved `databaseA.db` and `databaseB.db` warehouse prefixes. |
| Dremio | Optionally receives one Space per Hive database and one view per table through the writer's local JDBC account. It owns JDBC authorization. |

## Workload Manifest

Use the existing generator output and schema definitions for all eight TPCH tables: `customer`, `lineitem`, `nation`, `orders`, `part`, `partsupp`, `region`, and `supplier`. Load the same generated input set into each database so the later authorization checks compare equivalent table names and contents. The default generator scale factor remains 1 unless separately changed in Infrastructure Design. Record source scale factor, database, table, input file identity, row count, Hive identifier, warehouse location, and Dremio outcome in a non-secret run manifest.

## Workflow

1. **Preflight.** Require healthy KDC, Hive Metastore, RustFS/bucket, and Spark runtime; provisioned writer keytab and RustFS credentials; all eight expected input files; and an initialized Dremio local writer account when JDBC setup is enabled. Verify files/config references without printing credential values.
2. **Authenticate.** Use the protected writer keytab to acquire a short-lived Kerberos ticket for `write-service-account`. In the verified Spark local execution mode, pass the resulting protected ticket cache to the Spark/Hadoop process; do not assume Spark standalone `--principal/--keytab` login works. Remove temporary cache material on completion or failure.
3. **Configure Spark.** Select the Hive Metastore catalog and the approved RustFS S3A endpoint/warehouse. Supply only the writer's named S3 credentials. Do not pass Dremio admin, RustFS root, or metastore PostgreSQL credentials to the ETL process.
4. **Create/load Hive tables.** Ensure `databaseA` and `databaseB` exist. For each of the eight table inputs in each database, calculate/record expected row count, then create the Iceberg table only if absent. If an existing table is present, validate schema and row count against the expected manifest and leave it untouched when it matches. If state conflicts or is partial, stop that table/database with a clear failure; never use `createOrReplace`, drop, overwrite, or append on automatic rerun.
5. **Validate ETL.** Read each table back through the Hive catalog, compare row counts and expected schemas, and verify the effective Kerberos identity is `write-service-account`. Record per-database/table success and observed RustFS warehouse prefix without logging secrets.
6. **Create Dremio objects.** After successful ETL, authenticate to Dremio JDBC as `write-service-account`. Ensure Spaces `databaseA` and `databaseB`; create one same-name view in each matching Space for every Hive table, using deterministic paths to the Hive tables. If an object already exists, verify its target and treat a match as present; do not replace conflicting objects. If Community denies create/list access, record the exact operation and SQLState/vendor diagnostic as a separate JDBC gate, do not retry as admin, and preserve ETL output.
7. **Report and clean up.** Emit the effective writer identity, ETL result, per-table row counts, and per-Space/view outcomes. Mark the overall run `partial` if ETL passed but JDBC setup failed. Destroy the short-lived ticket cache in all exit paths. Do not delete databases, tables, Dremio objects, or RustFS data.

## Failure and Recovery

- A failed prerequisite prevents writes from starting.
- On an ETL failure, stop further table writes and report successful and failed objects individually. Keep already-created objects; a rerun validates existing state and resumes only when safe.
- A schema/count mismatch is a conflict requiring operator review; automatic repair or replacement is prohibited.
- Dremio JDBC failure does not roll back successful Hive/RustFS ETL. Report it independently for later feasibility resolution.
- Credential values, keytab contents, Kerberos tickets, and secret-bearing connection strings never appear in logs or manifests.

## Observable Outcomes

The run reports `run_id`, effective identity, scale factor, source manifest, Hive catalog, table/schema/row-count state, RustFS warehouse prefix, and per-object Dremio JDBC state (`created`, `already-present`, `failed`, or `not-attempted`). Overall state is `complete`, `partial`, or `failed`; `complete` requires all ETL and requested JDBC operations to pass.

## Explicit Boundaries

- Unit 3 does not run Airflow/Jenkins or create a persistent scheduler.
- Unit 3 does not create reader identities/grants; Unit 2's post-ETL grant phase and later authorization units own those actions.
- Passing the writer's ETL does not prove user_a/user_b authorization or Dremio end-user impersonation.
- Spark keytab behavior and Dremio non-admin Space/view permissions remain build-and-test feasibility gates.
