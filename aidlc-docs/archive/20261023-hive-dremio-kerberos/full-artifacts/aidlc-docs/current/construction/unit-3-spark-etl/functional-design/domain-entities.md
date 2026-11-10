# Unit 3 Spark Runtime and Sample ETL — Domain Entities

## ETL Run

Represents one invocation of sample data generation/loading and optional JDBC setup.

| Attribute | Description |
|---|---|
| `run_id` | Non-secret identifier for this invocation. |
| `effective_identity` | Expected Kerberos identity `write-service-account`; no ticket or keytab data. |
| `scale_factor` | TPCH generator scale factor used for the input files. |
| `started_at` / `finished_at` | Run timestamps. |
| `etl_state` | `not_started`, `running`, `complete`, `partial`, or `failed`. |
| `jdbc_state` | `not_attempted`, `complete`, `partial`, or `failed`. |
| `overall_state` | `complete`, `partial`, or `failed`. |
| `diagnostic` | Redacted failure description without credentials or ticket material. |

## Database Dataset

Represents one Hive database's expected TPCH table set.

| Attribute | Description |
|---|---|
| `database_name` | `databaseA` or `databaseB`. |
| `catalog_name` | Configured Hive-backed Iceberg catalog identifier. |
| `warehouse_prefix` | Expected RustFS `lake/warehouse/<database>.db` prefix. |
| `lifecycle_state` | `missing`, `created`, `present_and_valid`, `conflict`, or `failed`. |
| `tables` | The eight `Table Load` outcomes for this database. |

## Table Load

Represents one TPCH source file loaded or validated as an Iceberg table.

| Attribute | Description |
|---|---|
| `table_name` | One of `customer`, `lineitem`, `nation`, `orders`, `part`, `partsupp`, `region`, `supplier`. |
| `source_file` | Input `.tbl` filename/reference; no secret data. |
| `expected_schema` | Schema from the existing loader definition. |
| `expected_row_count` | Count from the source data for the current scale factor. |
| `observed_row_count` | Count read back through Hive after create or validation. |
| `hive_identifier` | `<catalog>.<database>.<table>`. |
| `rustfs_location` | Expected table data location under the database prefix. |
| `lifecycle_state` | `created`, `already_valid`, `conflict`, or `failed`. |

## Dremio Exposure

Represents a Space or view creation/validation attempt through JDBC.

| Attribute | Description |
|---|---|
| `space_name` | Matching Hive database name. |
| `view_name` | Matching Hive table name. |
| `hive_target` | Fully qualified catalog/database/table target. |
| `jdbc_identity` | Dremio local `write-service-account`; no password data. |
| `operation_state` | `created`, `already_present`, `failed`, or `not_attempted`. |
| `diagnostic` | Redacted JDBC status/SQLState/vendor code; no connection secret. |

## Relationships and Boundaries

```text
ETL Run 1 ─── 2 Database Dataset
Database Dataset 1 ─── 8 Table Load
Table Load 1 ─── 0..1 Dremio Exposure
```

- Hive owns catalog metadata and RustFS owns Iceberg objects; the ETL Run records outcomes but does not become an authorization authority.
- A Dremio Exposure is independent of the Hive Table Load result. A denied JDBC operation does not invalidate or delete valid Hive/RustFS data.
- Credential artifacts are represented only by identity/reference. No secret values are part of these entities.
