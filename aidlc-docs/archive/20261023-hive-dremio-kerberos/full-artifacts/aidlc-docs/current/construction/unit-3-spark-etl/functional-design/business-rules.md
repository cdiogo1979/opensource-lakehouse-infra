# Unit 3 Spark Runtime and Sample ETL — Business Rules

## Catalog and Data

1. Hive Metastore is the Spark Iceberg catalog; active ETL paths do not use Nessie.
2. RustFS is the Iceberg data store. Spark uses `write-service-account`'s distinct RustFS key and only the approved warehouse prefixes.
3. Create exactly the approved sample databases `databaseA` and `databaseB` in this unit.
4. Each database receives the same eight existing TPCH tables: `customer`, `lineitem`, `nation`, `orders`, `part`, `partsupp`, `region`, and `supplier`.
5. Both databases use the same generated source data/scale factor, enabling like-for-like later authorization checks. Row counts and schemas are recorded per database/table.

## Identity and Credentials

6. The effective ETL identity is `write-service-account`; output must make that identity observable.
7. Acquire a short-lived Kerberos ticket from the writer keytab. In Spark local mode, use the verified ticket-cache path; do not rely on standalone `--principal/--keytab` login until proven in the actual execution mode.
8. RustFS writer credentials, Kerberos keytab/ticket, Dremio writer password, and PostgreSQL service credentials are distinct. ETL receives only the credentials it needs.
9. ETL never uses `admin`, RustFS root, or PostgreSQL metastore credentials.
10. Temporary ticket caches are protected and removed on success and failure. No credential or ticket material is logged, serialized in the manifest, or included in an image.

## Idempotency and Data Safety

11. Ordinary reruns never drop, replace, truncate, or append to an existing Hive table.
12. A missing database/table may be created. An existing table is accepted only when schema and expected row count match; otherwise the run reports conflict and stops modifying that target.
13. A partially completed run preserves successful objects and reports their individual status. Rerun may resume only after validating existing state.
14. Cleanup of databases, tables, Dremio objects, or RustFS data is not part of the automatic workload and requires a separately approved action.

## Dremio JDBC

15. Attempt Dremio JDBC setup only after successful ETL validation.
16. Use the non-admin `write-service-account` Dremio local account. Never retry a denied operation as `admin` or elevate the writer implicitly.
17. Create one Space per Hive database (`databaseA`, `databaseB`) and one same-name view per table in its matching Space, with deterministic source paths.
18. Existing Dremio objects are accepted only when they match the expected target; conflicting objects are reported and not replaced.
19. Dremio JDBC failure is a distinct partial integration result; successful Hive/RustFS data remains intact.

## Reporting and Scope

20. The redacted manifest records run ID, effective identity, scale factor, database/table, schema, row count, RustFS prefix, and Dremio object outcome.
21. Overall success requires ETL and every requested Dremio JDBC object operation. ETL success with a JDBC permission failure is `partial`, not full success.
22. Unit 3 creates no Airflow/Jenkins services, no reader grants, and no cross-engine authorization claim. Those remain deferred to their owning units.
