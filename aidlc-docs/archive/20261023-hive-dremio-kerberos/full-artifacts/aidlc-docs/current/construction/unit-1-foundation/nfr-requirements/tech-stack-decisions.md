# Unit 1 Technology Stack Decisions

## Decisions

| Area | Decision | Rationale and status |
|---|---|---|
| Orchestration | Keep Docker Compose and the existing shell lifecycle scripts. | Approved local single-host deployment; no independent deployment target. |
| Spark baseline | Preserve existing image `tabulario/spark-iceberg:3.5.5_1.8.1` where compatible. | Existing Compose pin; exact Hive Metastore client and Iceberg integration must be verified against the selected Hive 3.x release. |
| Dremio baseline | Preserve existing `dremio/dremio-oss:26.0.5` where compatible. | Existing Compose pin; current Dremio documentation (26.x) lists Hive 3.x and Storage Based with User Impersonation support, while SQL Based Hive authorization is not supported by the Hive source configuration. Verify against the pinned Community image. |
| Hive catalog | Use standalone Hive Metastore, Hive 3.x, with HiveServer2 excluded from the approved baseline. | User-approved scope. SQL-standard Hive authorization is HiveServer2 based; no-HiveServer2 enforcement depends on Metastore/storage-based authorization and remains a feasibility gate. |
| Hive version candidate | Evaluate Hive Metastore 3.1.3 as a candidate, not a locked decision. | Apache Spark 3.5 documentation lists Hive Metastore 3.0.0 through 3.1.3 as supported client versions. Exact Spark 3.5.5 image/JAR behavior, Hive schema compatibility, and container availability still require validation. |
| Hive metastore database | PostgreSQL in Compose; select and pin the exact compatible version during Infrastructure Design. | Hive metadata must persist in a separate relational database. Existing PostgreSQL 17 was used by Nessie and is not automatically considered compatible with the selected Hive schema/image. |
| Object storage | Preserve RustFS image `rustfs/rustfs:1.0.0` where compatible and use its S3-compatible API for the `lake` bucket/warehouse. | Existing pin and approved data location. Do not assume S3 API compatibility implies Hive filesystem permission semantics; validate separately. |
| Kerberos | Add a disposable local KDC; exact KDC image/distribution is deferred until Infrastructure Design. | Approved identity model; runtime credentials must be generated locally and kept out of source/image layers. |
| Credentials | Use distinct component-native credentials, generated or supplied from ignored local runtime files. | Required by approved secret-separation and least-privilege constraints. No external secret manager is required for this local PoC. |
| Network exposure | Publish required developer-facing ports on loopback only. | User selected local host use; do not expose services to other hosts by default. |
| Monitoring | Compose health/readiness and actionable local logs/status only. | No monitoring stack or alerting requirement was selected. |

## Compatibility Evidence

- Dremio's current Hive source documentation lists Hive 3.x as supported and offers “Storage Based with User Impersonation”; it lists “SQL Based” as not currently supported. It also describes Hive table storage support, with S3 configuration guidance specifically referencing S3 on Amazon EMR. This supports evaluating the Dremio metastore/user-impersonation path but does not establish RustFS compatibility. See [Dremio Hive source documentation](https://docs.dremio.com/current/data-sources/lakehouse-catalogs/hive/).
- Apache Spark 3.5 documentation lists Hive Metastore client versions 3.0.0 through 3.1.3 and describes selecting the client JAR/version through Spark configuration. The cited detailed page is Spark 3.5.6; the existing image uses Spark 3.5.5, so validate the exact image configuration rather than assuming patch-level equivalence. See [Spark Hive Tables](https://spark.apache.org/docs/3.5.6/sql-data-sources-hive-tables.html).
- Apache Iceberg documents the Spark 3.5 integration artifact family and Hive catalog configuration. Confirm that the existing Iceberg 1.8.1 runtime and selected Hive client libraries do not introduce conflicting dependencies. See [Iceberg 1.8.1 Spark Getting Started](https://iceberg.apache.org/docs/1.8.1/spark-getting-started/).
- Apache Hive documentation identifies storage-based authorization as using underlying path permissions, while SQL-standard authorization is configured through HiveServer2. RustFS path-permission behavior and effective-user preservation across both clients remain unproven. See [Hive Metastore Storage-Based Authorization](https://cwiki.apache.org/confluence/display/hive/storage%2Bbased%2Bauthorization%2Bin%2Bthe%2Bmetastore%2Bserver) and [Hive Authorization](https://cwiki.apache.org/confluence/display/Hive/LanguageManual+Authorization).

## Deferred Technology Decisions

The following decisions require Infrastructure Design and compatibility validation before any implementation is treated as complete:

1. Exact Hive 3.x image/tag, Java runtime, metastore schema initialization mechanism, and PostgreSQL JDBC driver.
2. Exact Hive Metastore client JAR selection and security configuration for Spark 3.5.5.
3. Dremio Community 26.0.5 Hive plugin configuration/classpath, Kerberos SASL behavior, and effective-user propagation.
4. Whether Dremio and Spark can both use the selected RustFS paths while preserving per-user authorization semantics.
5. Whether the selected Hive Metastore authorization provider can enforce databaseA/databaseB policy over RustFS.
6. Exact KDC implementation and secure, repeatable local principal/keytab generation.

If any compatibility gate requires changing an existing pinned Spark or Dremio version, return the proposed version and impact for review before implementation.
