# API and Protocol Inventory

## Existing Service Interfaces

| Component | Interface | Use |
|---|---|---|
| Hive Metastore | Thrift, internal `hive-metastore:9083` | Iceberg catalog metadata |
| RustFS | S3-compatible HTTP, internal `object-store:9000` | Iceberg metadata/data objects |
| PostgreSQL | PostgreSQL protocol, internal `metastore-db:5432` | HMS backing database |
| Kerberos KDC | Kerberos/Kadmin, internal network | Service and workload authentication |
| Spark | Spark SQL / `spark-submit` | ETL and notebook compute |
| JupyterHub | HTTP, host loopback port 8008 | Notebook access |

## Proposed StarRocks Interfaces

StarRocks is expected to expose its MySQL-compatible SQL protocol and HTTP/UI endpoints to local clients. It will consume HMS and RustFS interfaces. Exact ports, credentials, TLS/authentication mode, SQL grants, and query engine version are not yet requirements-approved.

## Adjacent Airflow Integration

The existing Airflow DockerOperator launches a Spark image on `iceberg-poc-net`, passing AWS key environment variables. Its sample Spark catalog is Nessie at `nessie:19120`; no StarRocks connection or query task is present in the inspected example.
