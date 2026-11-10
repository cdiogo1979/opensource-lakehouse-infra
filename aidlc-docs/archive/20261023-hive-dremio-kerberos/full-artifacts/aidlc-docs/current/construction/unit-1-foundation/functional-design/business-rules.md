# Unit 1 Functional Design — Business Rules

## Catalog and Service Lifecycle

1. Hive Metastore is the catalog for Spark-created Iceberg tables; active Nessie catalog dependencies are retired.
2. Hive Metastore metadata is persisted in PostgreSQL. PostgreSQL metadata credentials do not grant access to RustFS objects.
3. Hive Metastore is not considered ready until its metadata schema and Kerberos service authentication prerequisites are ready.
4. Bucket initialization is ensure-only: it may create the configured bucket but must preserve existing objects.
5. The bucket initializer does not use the sample ETL writer's broad object-write credential unless required by its explicitly scoped bucket operation.

## Identity and Authorization

6. `write-service-account` creates and owns `databaseA`, `databaseB`, and their sample Iceberg tables. `admin` is not used for the sample ETL.
7. Before ETL, `write-service-account` receives only the Hive and RustFS rights required to create/populate the two databases and their warehouse paths.
8. `user_a` receives read access to `databaseA` only; `user_b` receives read access to both databases. Reader grants are applied after the databases exist, using component-owned mechanisms.
9. The identity/permission provisioner coordinates setup; Hive Metastore and RustFS own their respective runtime authorization semantics.
10. Direct RustFS object access is not an acceptance demonstration. RustFS credentials remain a required part of Spark sessions and ETL.
11. The approved baseline excludes HiveServer2. SQL-standard authorization requiring HiveServer2 is not considered active in this design.
12. Storage-based Metastore authorization is a candidate mechanism only until effective-user checks and per-database outcomes are demonstrated with the selected RustFS and clients.
13. A shared Dremio source credential or a storage admin identity must not be treated as proof of per-user authorization.
14. If a component cannot enforce the expected allow/deny result, mark that outcome blocked and return evidence plus a proposed architecture adjustment for approval. Do not silently weaken the acceptance criterion or grant writer/admin privileges.

## Repeatability and Persistence

15. A clean Compose deployment can initialize the KDC, Hive schema, bucket, and later the sample databases/tables in documented order.
16. Safe reruns preserve existing Hive metadata and RustFS objects, report existing resources, and do not implicitly drop or overwrite table data.
17. If existing state conflicts with the current catalog/service contract and cannot be reconciled without data loss, fail with a diagnostic and preserve state for inspection.
18. Generated keytabs and credentials remain local runtime artifacts. Failure output must not include their contents.

## Failure Handling

19. Required initialization steps fail closed: dependent ETL and acceptance workflows do not continue after KDC, schema, bucket, or required permission setup failure.
20. Failure preserves named volumes and partial state for diagnosis; recovery does not automatically delete data.
21. A component may be available for diagnosis while the overall platform remains not ready. Readiness must not imply the full authorization path is valid.

## Cleanup

22. Stop-only operation preserves persistent volumes.
23. Full reset is explicit and destructive; it removes Hive metadata and RustFS object data in named volumes.
24. No normal startup, retry, or failed initialization automatically invokes full reset.

## Observability

25. Initialization output identifies the component/step and whether it was created, already present, ready, or failed.
26. Authorization demonstration output identifies the effective user and allow/deny result while never printing passwords, secret keys, or keytab contents.
