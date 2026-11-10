# Reverse Engineering — Component Inventory

| Component | Current responsibility | Dremio coupling / cleanup note |
|---|---|---|
| `kdc` | Disposable MIT Kerberos KDC and principal/keytab bootstrap | Creates/tests `dremio@REALM`, stores Dremio principal in persistent KDC database |
| `identity-provisioner` | Creates workload Kerberos, RustFS, and PostgreSQL identities | Iterates a Dremio principal and grants its extraction ACL |
| `metastore-db` | PostgreSQL Hive metadata backend | No Dremio-specific responsibility |
| `hive-metastore` | Hive 3.1.3 Thrift catalog with S3A configuration | Core-site template includes Dremio proxy-user entries |
| `object-store` / `create-bucket` | RustFS object store and ensure-only bucket initializer | Shared with all workloads; retain unless user narrows scope |
| `spark` | Spark 3.5.5 and Iceberg 1.8.1 runtime | Shared foundation for TPCH and notebooks |
| `jupyterhub` / single-user image | Isolated notebook sessions | Independent of Dremio; retain by recommended default |
| `infra/tpch-generator/` | Generates scale-factor-1 input | Independent of Dremio |
| `tpch-loader` | Runs Kerberized Spark ETL as writer | Dockerfile extracts Dremio JDBC driver; workload runs a subsequent JDBC phase |
| `tpch-jdbc` | Optional Dremio Spaces/views phase | Dremio-only; remove if Dremio is removed |
| Dremio | Hive source query service and UI/JDBC/Flight endpoints | Entire service/config/state should be removed from project scope |

Supporting paths include `docker-compose.yml`, `README.md`, `infra/hive/`, `infra/kerberos/`, `infra/identity-provisioner/`, `infra/spark/`, `infra/tpch-loader/`, `infra/tpch-generator/`, `scripts/`, `.env.example`, and `.runtime/`.
