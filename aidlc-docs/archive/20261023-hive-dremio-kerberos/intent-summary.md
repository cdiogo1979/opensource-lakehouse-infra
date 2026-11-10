# Intent Summary: Hive, Kerberos, Dremio, RustFS, and JupyterHub PoC

## Intent
Hive, Kerberos, Dremio, RustFS, and JupyterHub PoC (`20261023-hive-dremio-kerberos`)

## Objective
Replace the active Nessie catalog path with Hive 3.x, configure Kerberos identities and impersonation, provision admin and write-service identities, and add isolated per-user Spark notebooks while retaining RustFS as Iceberg storage.

## Date
2026-10-24

## Scope
Local Docker Compose proof of concept. Airflow/Jenkins integration and production deployment are excluded. The user accepted closure with verification waived; no deployment was performed.

## Units / workstreams
Unit 1: Hive catalog and local platform foundation, Unit 2: component identities and permissions, Unit 3: Spark sample ETL and Dremio objects, Unit 4: Dremio Hive identity and authorization path, Unit 5: JupyterHub and per-user Spark sessions, Deploy: local operator handoff

## Major requirements
- Use Hive 3.x Metastore backed by PostgreSQL as the Iceberg catalog, with Iceberg data in RustFS.
- Use a disposable Kerberos realm and distinct admin, write-service-account, and test-user identities.
- Run sample Spark ETL as write-service-account and provide Dremio and Jupyter query paths.
- Attempt per-user database authorization for user_a and user_b; preserve the known Dremio authorization failure and partial notebook evidence.
- Add local-only JupyterHub sessions with per-user keytab and RustFS credentials.

## Architecture and design decisions
- Standalone Hive Metastore with PostgreSQL; HiveServer2 is not in the baseline.
- RustFS remains the S3-compatible Iceberg warehouse; Kerberos and S3 credentials remain separate identity systems.
- Dremio Community uses local identities and a Kerberos-authenticated Hive source; source/space RBAC is not available in this Community edition.
- JupyterHub uses a development-only DummyAuthenticator and is bound to localhost.
- Airflow/Jenkins integration and direct RustFS authorization as a user-facing test are excluded.

## Implementation decisions
- Provision component-native identities through the repository's local identity setup and keep generated credentials under ignored runtime paths.
- Use write-service-account for sample Spark ETL and Dremio JDBC object creation paths; do not use admin as a fallback.
- Give notebook sessions separate identity mounts, per-user RustFS credentials, and separate persistent work volumes.
- Retain the approved Compose startup/stop and deployment handoff instructions.

## Deviations
- Unit 5 Build and Test is partial under a user-accepted waiver; the workflow is closed without claiming full acceptance.
- Dremio user_a access to databaseB is a confirmed failure of the required authorization matrix; effective identity and RustFS credential path remain unresolved.
- Notebook user_a's reported databaseB denial is not classified; multiple security, isolation, and capacity checks remain pending.
- No deployment, credential rotation, or volume reset was performed.

## Verification
User explicitly accepted closure with verification waived. Build and Test remains partial, not passed. Dremio user_a was confirmed able to query databaseB, contrary to the required deny matrix. Notebook user_a databaseB denial was reported but not classified; notebook user_a databaseA access, unknown-label rejection, complete mount/socket review for all users, workspace isolation/persistence, and three-session concurrency remain unverified. User-reported user_b notebook reads in both databases and the recorded admin sample query are retained as evidence with their stated limits. No deployment was performed.

## Canonical documents updated
- aidlc-docs/knowledge/hive-dremio-rustfs/application-design.md
- aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/lakehouse-workload-and-access.md

## Superseded decisions
- The inherited Nessie catalog path from the source PoC was replaced by the Hive 3.x Metastore path for this intent.

## Archived artifacts
- aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/aidlc-docs/current/compaction/20261023-hive-dremio-kerberos/manifest.json
- aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/README.md
- aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/.env.example
- aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/.gitignore
- aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/docker-compose.yml
- aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/infra
- aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/scripts
- aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/spark
- aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/sql
- aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/tpch
- aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/tpch-generator

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261023-hive-dremio-kerberos/full-artifacts/`
