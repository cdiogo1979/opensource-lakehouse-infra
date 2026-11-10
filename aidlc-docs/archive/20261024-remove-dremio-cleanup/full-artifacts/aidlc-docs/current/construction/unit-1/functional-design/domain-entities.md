# Domain Entities — Retained Lakehouse Workload

## Existing Entities

- **Catalog database and table:** Existing Hive Metastore objects for the TPCH sample workload.
- **Iceberg table data:** Existing RustFS objects referenced by Hive catalog metadata.
- **Workload identity:** Existing `write-service-account` used by Spark ETL.
- **Notebook identity/workspace:** Existing per-user Kerberos and RustFS configuration plus Jupyter workspace state.

## Change Assessment

No new entities, relationships, schemas, or identifiers are introduced. The Dremio Space/view representation is removed because it belongs exclusively to the removed integration; Hive catalog databases/tables remain unchanged. This design does not authorize deleting any retained entity or persisted data.
