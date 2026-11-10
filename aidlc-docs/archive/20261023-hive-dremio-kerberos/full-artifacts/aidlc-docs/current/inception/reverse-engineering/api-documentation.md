# API Documentation

## Service APIs

| Service | Protocol / path | Purpose |
|---|---|---|
| RustFS | S3-compatible HTTP API, internal port 9000 | Bucket and object operations |
| RustFS console | HTTP, internal port 9001 | Local object-store administration |
| Nessie | REST `/api/v2` on port 19120 | Catalog configuration, namespace/table metadata operations |
| Dremio | UI 9047, JDBC 31010, Flight 32010 by defaults | SQL and administration |

## Internal Interfaces

- Spark uses the Iceberg `SparkCatalog` with `org.apache.iceberg.nessie.NessieCatalog`.
- TPCH scripts issue SQL through Spark, including table creation/writes and Nessie registration procedures.
- Compose service DNS names (`object-store`, `nessie`, `nessie-db`) are internal integration endpoints.

## Data Models

The TPCH generator and loader operate on standard TPCH relations, including customer, lineitem, nation, orders, part, partsupp, region, and supplier. Iceberg namespace/catalog schemas are configured in Spark; no separate application model definitions are present.

## Authentication and Identity

RustFS currently uses static access and secret keys. Nessie uses PostgreSQL credentials. Dremio uses its first-run administrator setup. Kerberos authentication and user impersonation are not configured in the checked-in Compose or Spark settings.
