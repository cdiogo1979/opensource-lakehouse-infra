# Business Logic Model — Retained Lakehouse Workload

## Scope

This design records workload behavior that must remain after Dremio removal. Hive Metastore continues to hold catalog metadata, RustFS continues to store Iceberg data, and Spark continues to create and populate the TPCH sample tables as `write-service-account`. JupyterHub continues to provide notebook sessions using the existing Spark, Kerberos, and RustFS configuration.

## Retained Flow

1. TPCH input is generated or made available to the Spark loader.
2. Spark authenticates using the configured workload Kerberos identity.
3. Spark creates/populates the existing sample databases and tables through Hive Metastore and writes table data to RustFS.
4. The optional Dremio JDBC phase is absent; it must not gate or alter Spark ETL completion.
5. Jupyter Spark sessions continue to query the retained Hive catalog and RustFS data under their configured identities.

## Removed Flow

The TPCH loader no longer copies or loads a Dremio JDBC driver, connects to Dremio, creates Dremio Spaces/views, or reports a Dremio-specific phase. Dremio does not participate in retained catalog writes or notebook queries.

## Boundary

This is a removal design. No new transformation, table schema, authorization policy, or identity mapping is introduced. The existing Hive/RustFS/Spark workload contract remains the behavior baseline.
