# Business Rules — Retained Lakehouse Workload

1. The TPCH Spark ETL remains the supported sample data writer and continues to use `write-service-account`.
2. Hive Metastore remains the catalog for the retained sample tables; RustFS remains their object storage.
3. Removing Dremio must not remove or rewrite Hive metadata, table objects, TPCH inputs/results, notebook workspaces, or non-Dremio identities.
4. Dremio-specific JDBC work is not part of ETL success or failure after removal.
5. Existing table names, schemas, and write behavior remain unchanged by this cleanup.
6. The implementation must not silently broaden cleanup to all Compose volumes or reset the KDC.

## Failure Behavior

Failures in retained Spark, Hive, Kerberos, or RustFS operations remain visible through their existing commands/logs. Dremio connection failures and Dremio-specific status output are removed along with the JDBC phase. Runtime cleanup must target only the identified Dremio principal, Dremio-only credential files, and Dremio data volume.
