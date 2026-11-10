# Build and Test Summary — Unit 1 Foundation

## Status

**COMPLETE — Unit 1 Foundation build and runtime gates passed.** The Compose file validates, all custom images build, Hive schema initialization succeeds, and the full stack starts with Hive Metastore healthy under amd64 emulation. A Kerberos-authenticated Spark client can read and write namespace metadata through the Hive catalog. The temporary smoke-test namespace and credential copies were removed after verification.

## Scope

- Build: Docker Compose configuration and the KDC, Hive, and bucket-initializer images.
- Integration: KDC service identity, PostgreSQL schema, Hive readiness, Spark-to-Hive Kerberos client behavior, RustFS bucket ensure, and host-port exposure.
- Unit tests: not applicable; this infrastructure unit has no unit-test harness or test files.
- Performance: not applicable; no target is specified.
- Security: configuration-boundary review only; no scanner is configured.

## Results

### Passed

- `docker compose config --quiet` — configuration rendered successfully after local credentials were bootstrapped.
- `docker compose build kdc create-bucket hive-schema-init hive-metastore` — all custom images built successfully, including Hive 3.1.3 with PostgreSQL JDBC 42.7.14 and Hadoop 3.1.0-matched S3A/AWS SDK jars.
- KDC health check — healthy; `kinit` using the Hive Metastore keytab obtained a ticket for `hive/hive-metastore@LAKEHOUSE.LOCAL`.
- PostgreSQL and RustFS health checks — healthy.
- Bucket initializer — exited successfully and preserves existing bucket contents.
- `schematool -dbType postgres -initSchema`, followed by `-info` — initialized PostgreSQL and reported Hive Metastore schema version 3.1.0.
- Hive Metastore — healthy; port 9083 is reachable inside the container.
- Spark SQL `SHOW NAMESPACES IN iceberg` with a Kerberos ticket cache — returned the `default` namespace.
- Spark SQL `CREATE NAMESPACE iceberg.codex_smoke_kerberos` — succeeded. The matching row was confirmed in PostgreSQL's Hive `DBS` table, demonstrating a metadata write through the external Hive Metastore.
- Spark SQL `DROP NAMESPACE iceberg.codex_smoke_kerberos` — succeeded; PostgreSQL confirmed the temporary row was removed. Temporary smoke-test keytab and ticket-cache copies were deleted.
- Dremio, Hive Metastore, KDC, PostgreSQL, RustFS, and Spark — running. Hive, KDC, PostgreSQL, and RustFS report healthy.
- Dremio, RustFS, and Spark host-published ports — bound to loopback (`127.0.0.1`).

### Resolved during build

Initial Hive startup exposed missing S3A classes, missing `DB_DRIVER=postgres`, and Hadoop Kerberos authentication not being enabled in `core-site.xml`. These were corrected. The Metastore now reaches healthy status and Spark can authenticate to it with Kerberos.

## Deferred integration gates

Later units must verify provisioning and permissions for `admin`, `write-service-account`, `user_a`, and `user_b`; creation and population of sample databases and Iceberg tables as `write-service-account`; Hive storage writes over RustFS; Dremio Hive integration and effective-user behavior; database-level allow/deny outcomes; Dremio JDBC Space object creation; Jupyter user sessions; and RustFS `1.0.0-glibc` API equivalence. Unit 1 did not create sample data or claim those outcomes as verified.

Security scans and performance tests were not run: no scanner or performance target is defined for this infrastructure unit. Runtime secrets remain under ignored `.runtime/credentials/`; do not copy their values into reports.
