# Current Application Design — Hive, RustFS, Kerberos, Spark, and JupyterHub

## Purpose and scope

This repository is a local Docker Compose lakehouse proof of concept. Hive Metastore 3.x is the Iceberg catalog, PostgreSQL stores Hive metadata, RustFS stores Iceberg objects, Spark runs ETL, and JupyterHub provides isolated Spark notebooks. Airflow and Jenkins orchestration are deferred. This is not a production authentication or deployment design.

## Components and boundaries

- **Hive Metastore 3.1.3** stores catalog metadata in PostgreSQL and describes Iceberg data in RustFS. The standalone metastore is used; HiveServer2 is not part of the deployed baseline.
- **Kerberos KDC** provides service and user principals/keytabs in the local `LAKEHOUSE.LOCAL` realm. Hive uses its service identity; workload and notebook identities are provisioned separately.
- **RustFS** stores Iceberg objects in the `lake` bucket. S3 access uses RustFS access/secret keys and policies, separate from Kerberos identities.
- **Spark and TPCH loader** create and populate `databaseA` and `databaseB` as `write-service-account`, using Hive as the catalog and RustFS as the warehouse.
- **JupyterHub 5.3.0** starts isolated Spark single-user containers with per-user Kerberos and RustFS credentials. DummyAuthenticator usernames are development labels, not verified identities. The Hub binds to localhost.

## Identity and access boundaries

Kerberos principals, PostgreSQL roles, and RustFS S3 identities are separate credentials. The notebook configuration supplies each session's configured RustFS key and Kerberos identity. The writer identity is distinct from admin and user identities. Existing per-user storage authorization outcomes must only be described as verified when supported by evidence; source/user labels alone do not establish the effective identity at Hive or RustFS.

## Operations and lifecycle

Use the repository start/stop scripts and preserve named volumes and protected `.runtime/credentials` material during normal operation. Do not commit runtime secrets. The one-time Dremio removal cleanup is scoped to legacy Dremio-only runtime resources; it must not reset Hive metadata, the KDC, RustFS, TPCH data/results, or notebook workspace volumes. See the archived prior intent for historical records; its contents are preserved as history.
