# Reverse Engineering — Architecture

## Current system

The project is a single-host Docker Compose lakehouse PoC. PostgreSQL stores Hive Metastore metadata; Hive Metastore provides the catalog; RustFS stores S3-compatible Iceberg objects; Spark and the TPCH workload profile create sample tables. A disposable MIT Kerberos KDC issues service and user identities. JupyterHub spawns isolated Spark notebook containers. Dremio is an additional query service and JDBC target.

## Service relationships

- `hive-metastore` depends on PostgreSQL schema initialization, KDC, and bucket initialization.
- `spark` uses Hive Metastore, RustFS, and Kerberos.
- `jupyterhub` and its single-user image use Spark, Hive, RustFS, and per-user Kerberos/storage credentials.
- `tpch-loader` runs Spark ETL as `write-service-account`.
- `tpch-jdbc` is a separate optional Dremio integration that creates/validates Dremio Spaces and views.
- `dremio` uses Hive connector configuration and a Dremio Kerberos identity; its state is in the named `dremio-data` volume.

## Dremio removal boundary discovered

Removing only the Compose `dremio` service is insufficient. Dremio is also referenced by the KDC entrypoint and healthcheck, Dremio-specific Hive proxy properties, Compose secret/port/volume definitions, TPCH JDBC service and driver extraction stage, writer/admin/user password bootstrap, identity provisioning helper, startup and reset messages, SQL scripts, README, and current canonical design documents. Runtime Dremio state additionally exists in local credential files/keytabs, KDC persistent state, and the Docker named volume. Cleanup scope for runtime data is not yet approved.

## Intended remaining architecture

Pending user clarification. The recommended default is to retain Hive, PostgreSQL, RustFS, Kerberos, Spark/JupyterHub, and the Spark TPCH workload while removing Dremio-only components and the optional JDBC phase. This default is not yet approved.
