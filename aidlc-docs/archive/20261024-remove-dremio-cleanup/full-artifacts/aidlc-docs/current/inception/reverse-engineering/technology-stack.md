# Reverse Engineering — Technology Stack

Observed in the current repository:

- Docker Compose v2 for local service orchestration.
- Hive Metastore 3.1.3 and PostgreSQL 16 for catalog metadata.
- MIT Kerberos KDC with realm default `LAKEHOUSE.LOCAL`.
- RustFS 1.0.0 S3-compatible object store.
- Spark 3.5.5 with Iceberg 1.8.1.
- Dremio Community 26.0.5 with JDBC client driver extracted from its image.
- JupyterHub 5.3.0, DockerSpawner 14.0.0, and a Spark single-user image.
- Python and Bash automation for bootstrap, identity provisioning, TPCH loading, and service lifecycle.

Removing Dremio also removes the Dremio JDBC-driver image dependency. The exact remaining image/build inventory depends on the approved cleanup scope.
