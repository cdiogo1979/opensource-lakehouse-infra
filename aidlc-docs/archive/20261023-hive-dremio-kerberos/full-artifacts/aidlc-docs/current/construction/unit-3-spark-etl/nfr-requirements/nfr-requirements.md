# Unit 3 Spark Runtime and Sample ETL — NFR Requirements

## Scope and Operating Context

These requirements apply to the one-shot TPCH generation/load and Dremio JDBC exposure in the single-host local Compose PoC. The workload runs with the fixed `write-service-account` identity, scale factor 1, and eight existing TPCH tables in each of `databaseA` and `databaseB`. It has no production scheduling, availability, throughput, or multi-host target.

## Capacity and Performance

- **U3-NFR-01**: Support the fixed two-database/eight-table-per-database sample workload at the existing TPCH generator default scale factor 1.
- **U3-NFR-02**: Bulk datasets, concurrent ETL invocations, multi-host execution, and horizontal scaling are outside acceptance scope.
- **U3-NFR-03**: Prioritize correct identity, data integrity, safe reruns, and observable progress. No generation/load duration or throughput SLA is required.

## Availability, Durability, and Recovery

- **U3-NFR-04**: Require KDC, Hive Metastore, RustFS/bucket, and Spark readiness before ETL writes begin; require Dremio readiness before JDBC setup.
- **U3-NFR-05**: A normal rerun preserves matching existing Hive tables, Iceberg data, and matching Dremio objects. It never drops, replaces, truncates, or appends automatically.
- **U3-NFR-06**: Existing table schema/count mismatch or a conflicting Dremio object is reported as a conflict and is not automatically repaired.
- **U3-NFR-07**: Partial failure preserves all successful work. ETL failure stops subsequent data writes; JDBC failure after valid ETL reports a partial outcome without deleting Hive/RustFS data.
- **U3-NFR-08**: Retry only bounded transient readiness/availability checks and operations known to be idempotent. Authentication, authorization, data conflict, and unsupported capability errors stop or return a distinct failed/partial result promptly.
- **U3-NFR-09**: Destructive sample-data or Dremio object cleanup is a separate explicit operator action; no automated rollback or reset is required.
- **U3-NFR-10**: No HA, uptime target, failover, or disaster-recovery automation is required for this local PoC.

## Security and Exposure

- **U3-NFR-11**: The effective ETL identity is `write-service-account`. Do not use `admin`, RustFS root, or PostgreSQL metastore credentials in the ETL process.
- **U3-NFR-12**: Keep the writer Kerberos keytab/ticket cache and RustFS credentials restricted to the one-shot workload; mount files read-only where supported and remove temporary ticket material on success and failure.
- **U3-NFR-13**: Dremio JDBC uses only the non-admin writer's native account. Do not retry denied operations with admin credentials or broaden the writer's privileges implicitly.
- **U3-NFR-14**: Keytabs, ticket caches, passwords, RustFS secrets, and secret-bearing connection strings must not appear in logs, reports, command output, tracked files, or image layers.
- **U3-NFR-15**: Keep published endpoints loopback-only and workload traffic on the private Compose network. This remains a development PoC and is not production security.

## Technology Compatibility

- **U3-NFR-16**: Preserve the approved pinned Spark/Iceberg, Hive Metastore, RustFS, and Dremio versions while compatible.
- **U3-NFR-17**: Verify keytab-to-ticket-cache behavior with the actual Spark execution mode. Do not claim standalone/local `--principal/--keytab` support based solely on a pre-authenticated ticket-cache smoke check.
- **U3-NFR-18**: Verify the non-admin Dremio writer can create the required Spaces/views through the pinned JDBC interface. If unsupported, record the exact capability gap and smallest proposed adjustment for review; do not promote the writer to admin.
- **U3-NFR-19**: Any image/version change, credential-boundary relaxation, or broader permission needed for compatibility requires review before implementation.

## Reliability and Observability

- **U3-NFR-20**: Report the effective identity, run ID, scale factor, per-database/table schema and row counts, and per-Space/view JDBC status.
- **U3-NFR-21**: ETL and Dremio JDBC outcomes are reported separately. `complete` requires all requested operations; successful ETL with denied JDBC setup is `partial`.
- **U3-NFR-22**: Diagnostics identify the component and failed operation, with credential data and ticket material redacted.
- **U3-NFR-23**: No separate monitoring, alerting, or report database/service is required. Operator command output and local container logs are sufficient.

## Maintainability and Usability

- **U3-NFR-24**: Keep generator, Spark ETL, and Dremio JDBC setup responsibilities independently understandable and report per-object state.
- **U3-NFR-25**: Document prerequisites, identity use, safe rerun behavior, partial outcomes, and separately invoked cleanup.
- **U3-NFR-26**: Use an explicit one-shot operator action. Airflow/Jenkins integration and scheduled execution are excluded.

## Explicitly Excluded Targets

- Production availability, HA, DR, enterprise secret management, multi-host scheduling, and horizontal scaling.
- ETL performance SLA, benchmark, or throughput target.
- Automatic table replacement, data cleanup, destructive rollback, and automatic Dremio object replacement.
- Automatic elevation to Dremio admin or use of RustFS root credentials to bypass a permission failure.
- Airflow/Jenkins integration, reader access demonstrations, and cross-engine authorization acceptance; those belong to later units.
