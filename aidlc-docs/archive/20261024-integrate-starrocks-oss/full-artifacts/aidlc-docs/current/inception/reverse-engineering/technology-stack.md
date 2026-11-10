# Technology Stack

| Technology | Current version/configuration | Role |
|---|---|---|
| Docker Compose | Compose v2 | Local orchestration |
| Hive Metastore | 3.1.3 | Iceberg catalog |
| PostgreSQL | 16.14 | HMS backing metadata store |
| Spark | 3.5.5 | ETL and notebooks |
| Apache Iceberg | 1.8.1 | Table format/catalog client |
| RustFS | 1.0.0 | S3-compatible storage |
| Kerberos | MIT KDC, `LAKEHOUSE.LOCAL` | Service/workload identity |
| JupyterHub | 5.3.0 | Notebook access |
| Airflow | Sibling project, version defined in its Dockerfile | ETL orchestration |
| StarRocks OSS | Not selected or installed | Proposed analytical engine |

Hive 3.1.3 is an archived/EOL version per project documentation. The current deployment is a local PoC and should not be represented as production-ready.
