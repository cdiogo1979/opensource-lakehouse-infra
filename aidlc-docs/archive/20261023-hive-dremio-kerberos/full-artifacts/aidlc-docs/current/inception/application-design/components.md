# Application Components

This document defines the high-level runtime and workload boundaries for the approved Hive/Kerberos PoC. It describes responsibilities and interfaces; detailed authorization and configuration rules belong in per-unit Functional and Infrastructure Design.

## Components and Responsibilities

| Component | Type | Purpose and responsibilities | High-level interfaces |
|---|---|---|---|
| Compose orchestrator | Infrastructure | Declares services, networks, persistent state, and startup dependencies; runs one-shot initialization in order. | Compose service graph; lifecycle scripts; health/readiness conditions. |
| Kerberos KDC | Infrastructure | Provides the disposable realm and service, user, admin, and writer principals; generates local keytabs. | Kerberos authentication; principal/keytab provisioning operations. |
| Identity/permission provisioner | One-shot setup workload | Coordinates principal and account setup plus database/storage permission initialization through component-owned interfaces. It does not make runtime authorization decisions or become a policy authority. | `provisionIdentities`; `applyHiveGrants`; `applyStoragePolicies`; `provisionDremioUsers`. |
| Metastore PostgreSQL | Infrastructure | Persists Hive Metastore metadata. Database administrator credentials remain component-native. | PostgreSQL connection for Hive Metastore; separately controlled administration connection. |
| Hive Metastore | Catalog service | Stores Hive database/table metadata for Iceberg; authenticates service connections with Kerberos/SASL and exposes metadata to Spark/Dremio. Applies the selected Hive authorization integration. | Thrift Metastore API; Kerberos/SASL; metadata and authorization operations. |
| RustFS | Object storage | Stores Iceberg warehouse data and metadata. Provides separate credentials/policies for admin, writer, and Jupyter Spark identities. | S3-compatible API; bucket/warehouse initialization; component-native credential administration. |
| Bucket initializer | One-shot setup workload | Creates the required bucket and baseline warehouse location. Does not grant broad data-write permissions to its runtime identity. | `ensureBucket`; S3-compatible administration endpoint. |
| Spark runtime | Application runtime | Supplies interactive Spark/Iceberg execution with Hive catalog settings. Notebook sessions run with each user's Kerberos and RustFS identity. | Spark session; Hive Metastore client; S3A/RustFS client. |
| TPCH generator | Workload | Produces local TPCH source files for sample ETL. | Local source-data directory. |
| TPCH loader | One-shot workload | Runs sample ETL as `write-service-account`; creates and populates `databaseA` and `databaseB` Iceberg tables in Hive/RustFS; creates matching Dremio Spaces and one view per Hive table through JDBC, subject to the documented Community feasibility gate. | Spark submit/session; Hive Metastore; RustFS S3 API; Dremio JDBC. |
| Dremio | Query engine | Connects to Hive using a Kerberos service identity, maps local usernames to Hive users, queries Iceberg data, and provides the two database-matched Spaces/views. | Hive source with SASL/Kerberos and identity mapping; JDBC; local user management. |
| JupyterHub | Notebook platform | Authenticates local demo labels using the selected DummyAuthenticator and starts isolated single-user Spark notebooks. | Hub authentication; DockerSpawner; user-scoped mounts/environment. |
| SQL workloads and operator documentation | Supporting workload/docs | Defines repeatable query examples and explains setup, identity, limitations, and manual allow/deny scenarios. | SQL files; lifecycle/operator instructions. |
| Lifecycle scripts | Supporting workload | Starts and cleans the Compose deployment in a repeatable order and explains persistent volume behavior. | `start.sh`, `clean.sh`; Compose CLI. |

## Identity Boundaries

- `admin` maps to component-specific administrative access. Non-Kerberos components use separate native admin credentials.
- `write-service-account` has separate Kerberos, RustFS, and Dremio credentials. It runs sample ETL and is not a platform administrator.
- `user_a` and `user_b` have distinct Kerberos principals/keytabs and RustFS credentials in Jupyter. Hive authorization grants `user_a` databaseA only and `user_b` both databases.
- Dremio local usernames map to the matching Hive effective user. Dremio's Hive service identity is used for SASL; it must not replace the query user's effective identity.
- DummyAuthenticator usernames are test labels, not verified identities. This topology is restricted to the local development PoC.

## Design Boundaries and Feasibility

- Hive Metastore is the catalog service; HiveServer2 is not part of the baseline.
- The identity/permission provisioner sequences setup through component-native interfaces. Hive, RustFS, Kerberos, and Dremio remain owners of their own identity/permission mechanisms.
- The TPCH loader owns sample table creation and the requested matching Dremio view creation after Hive tables exist.
- Dremio Community Space creation and non-admin JDBC view creation must be proven for the selected version. The design does not assume unavailable RBAC features or elevate the writer to administrator to make the flow appear successful.
- Hive database authorization over a standalone Metastore with RustFS-backed tables remains a technical feasibility item. Design confirmation is deferred to unit-level functional/infrastructure design and the authorized manual verification stage.
- Airflow and Jenkins remain outside this runtime and workflow boundary.
