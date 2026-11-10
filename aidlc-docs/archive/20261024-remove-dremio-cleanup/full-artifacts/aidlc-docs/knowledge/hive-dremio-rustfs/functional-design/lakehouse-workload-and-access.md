# Functional Design — Lakehouse Workload and Access

## Catalog and sample workload

Hive Metastore is the catalog for Iceberg tables stored in the RustFS `lake` warehouse. The sample workload uses Spark as `write-service-account` to create and populate `databaseA` and `databaseB`. Airflow/Jenkins orchestration is deferred.

## Identity flow

- Notebook labels `user_a`, `user_b`, and `admin` map to their configured Kerberos principals and separate RustFS identities. DummyAuthenticator does not verify a person's identity.
- The Spark TPCH loader authenticates with the writer Kerberos keytab and uses the writer's RustFS credentials to write through the Hive catalog.
- Kerberos proxy-user settings, Hive authorization, and RustFS policies are separate controls. One does not automatically grant access in the others.
- The Hive metastore uses its configured RustFS service credentials to access table metadata and data. Notebook Spark sessions use their explicitly configured RustFS credentials.

## Workload behavior

The optional TPCH workload generates scale-factor-1 input, validates all required input files, and uses Spark to create or validate the existing tables in both databases. Existing tables are kept when their schema and row counts match; conflicts stop the run rather than overwrite data. The loader emits a redacted manifest containing ETL states and diagnostics without credentials.

## Data preservation and failure behavior

Removing unrelated query integrations must not change Hive databases/table schemas, existing Iceberg objects, TPCH source inputs/results, RustFS credentials, Kerberos identities other than those explicitly retired, or Jupyter workspaces. A failed ETL remains reported as failed, and existing table conflicts do not trigger replacement or cleanup.

## Local development limits

The stack is a local proof of concept. Notebook usernames are development labels, and authorization claims require tests that establish the effective Kerberos/Hive identity and storage policy. No production identity provider or workflow orchestrator is included.
