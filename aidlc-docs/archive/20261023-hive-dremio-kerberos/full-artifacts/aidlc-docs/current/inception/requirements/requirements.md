# Requirements — Hive Catalog and Kerberos Authorization PoC

## Intent Analysis

- **User request**: Replace Nessie with Hive 3.x as the Iceberg catalog in `hive-dremio-rustfs`, add Kerberos impersonation, demonstrate database access restrictions through Dremio and Spark/Jupyter, and create platform admin and write-service users. The writer must create objects in Dremio Spaces over JDBC; Airflow/Jenkins integration is deferred.
- **Request type**: Brownfield infrastructure and security enhancement / catalog migration.
- **Scope estimate**: Multiple services and integration paths: Hive Metastore, Kerberos KDC, Dremio Community, Spark, RustFS, and JupyterHub.
- **Complexity estimate**: Moderate to complex. Catalog configuration is cross-cutting, and user-level authorization must be consistent across two query engines.

## Goals

1. Replace Nessie with a Hive 3.x Metastore catalog while retaining Iceberg tables in RustFS.
2. Configure Kerberos authentication for the Hive access path and per-user identity propagation/impersonation.
3. Add JupyterHub to this PoC using the existing `jupyter-platform/` setup as its baseline.
4. Demonstrate that two users have different access to two Hive databases from both Dremio and Spark in Jupyter.
5. Create an admin identity for the in-scope components and a write-service identity that can create objects in a designated Dremio Space over JDBC.

## Functional Requirements

### Platform administration and write-service identity

- **FR-19**: In addition to the two test users, provision a Kerberos `admin` principal and a distinct `write-service-account` principal in the disposable realm.
- **FR-20**: Map `admin` to the administrative role/account required to administer each in-scope platform component: Kerberos/KDC, Hive Metastore, PostgreSQL metastore backend, Dremio, Spark, JupyterHub, and RustFS. Keep component-native credentials separate where a component does not use Kerberos; do not reuse the Kerberos keytab as a web/S3 password.
- **FR-21**: Create the `write-service-account` Kerberos principal and corresponding Dremio local user now. The account is reserved for future Airflow-triggered Spark use; adding or changing Airflow/Jenkins infrastructure and wiring jobs to this identity are deferred.
- **FR-22**: The Dremio `write-service-account` user must be able to connect over JDBC and create objects (at minimum tables) in a designated existing Dremio Space. It must not receive platform-administrator privileges.
- **FR-23**: Create the write-service identity in the in-scope identity systems needed for Spark ETL: Kerberos and RustFS, as well as the Dremio local user specified in FR-21. Grant it only the Hive permissions needed to create/populate `databaseA` and `databaseB` and the RustFS permissions needed for their Iceberg warehouse paths. Use this identity for the sample ETL in this intent. Do not configure Airflow/Jenkins or add Airflow job credential injection.

### Catalog and storage

- **FR-01**: Hive 3.x Hive Metastore is the catalog for Spark-created Iceberg tables; Nessie and its PostgreSQL database service are removed from the active Compose topology.
- **FR-02**: Run a standalone Hive Metastore service in Docker Compose. HiveServer2 is not required for the selected PoC scope.
- **FR-03**: Use PostgreSQL in Compose for Hive Metastore metadata persistence. Select a Hive 3.x image/version compatible with the selected Spark, Dremio Community, and metastore schema during planning.
- **FR-04**: Preserve RustFS as the S3-compatible location for Iceberg table data.
- **FR-05**: Update Spark catalog configuration, TPCH loading/registration scripts, Jupyter Spark configuration, service dependencies, and operator documentation so no active runtime path depends on Nessie.

### Kerberos identity and impersonation

- **FR-06**: Add a disposable local Kerberos KDC to the Compose PoC.
- **FR-07**: Generate test principals and keytabs through the local KDC initialization flow. Do not commit generated keytabs, passwords, or other credential material.
- **FR-08**: Configure Dremio's Hive source connection to authenticate to the Hive Metastore using a Kerberos service identity/SASL.
- **FR-09**: Retain Dremio Community's local user accounts. Map Dremio query usernames to the corresponding Hive identities and configure Hive/Hadoop proxy-user rules with explicit test-user, group, and host allow-lists.
- **FR-10**: Configure each Jupyter test user's Spark session to authenticate to Hive using that user's distinct Kerberos principal/keytab. Mount the matching keytab read-only into that user's single-user notebook container.
- **FR-11**: Configure the group/user identity mapping so Hive sees the same test usernames for Dremio impersonation and Spark's Kerberos-authenticated sessions.

### Jupyter and authorization demonstration

- **FR-12**: Add JupyterHub to `hive-dremio-rustfs`, using `jupyter-platform/` as the starting point for the Hub, DockerSpawner, and Spark single-user image configuration.
- **FR-13**: Retain DummyAuthenticator for this isolated development PoC as explicitly selected. Treat Hub usernames as test labels, not verified identities; the environment must not be presented as production authentication.
- **FR-14**: Use Spark as `write-service-account` to create and populate two Hive databases, `databaseA` and `databaseB`, with Iceberg tables stored in RustFS and queryable by both engines. The sample ETL must use this service identity, not `admin`.
- **FR-15**: Configure database-level authorization so `user_a` can read `databaseA` only and `user_b` can read both `databaseA` and `databaseB`.
- **FR-16**: Demonstrate the expected allow and deny outcomes for both users through Dremio and Spark in their Jupyter sessions.
- **FR-17**: Direct RustFS S3 access is outside the selected authorization demonstration. RustFS remains the data store used by the query paths.
- **FR-18**: Use per-user RustFS credentials/policies for Spark in Jupyter, consistent with the earlier selected identity model. Ensure each Spark user's storage policy is compatible with that user's database access.

## Non-Functional Requirements and Constraints

- **NFR-01 — Secret handling**: Keep generated keytabs, Kerberos passwords, and RustFS secret keys out of tracked source. Provide placeholder examples and use ignored local credential files or runtime-generated disposable values.
- **NFR-02 — Isolation**: Keep the KDC, test principals, and permissive local settings confined to this development PoC. Document that DummyAuthenticator does not verify the claimed username.
- **NFR-03 — Least privilege**: Restrict Hadoop proxy-user hosts and allowed users/groups to the PoC's test identities; avoid wildcard impersonation rules.
- **NFR-04 — Repeatability**: A fresh Compose deployment can initialize the KDC principals, Hive metastore schema, test databases, and sample Iceberg tables in a documented order.
- **NFR-05 — Observability**: Logs or command results must make the authenticated/effective test username and allow/deny result clear for each engine.
- **NFR-06 — PBT extension**: Partial property-based-testing rules apply to applicable pure configuration/serialization logic. Most work is Compose and service configuration; identify any pure functions before deciding whether PBT applies.
- **NFR-07 — Security/resiliency extensions**: Security Baseline and Resiliency Baseline extensions are disabled by user choice. Functional security requirements above remain in scope.
- **NFR-08 — Credential separation**: Keep administrator, test-user, and write-service credentials distinct. Do not grant the write-service user administrator privileges. Do not expose Kerberos keytabs or RustFS secrets in tracked files, logs, or image layers.

## Acceptance Criteria

1. Compose defines Hive Metastore and its PostgreSQL backing store, the disposable KDC, Dremio, RustFS, Spark/JupyterHub, and required one-shot initialization services; no active Nessie service or Nessie configuration remains.
2. The sample ETL creates `databaseA`, `databaseB`, and their Iceberg tables as `write-service-account`; Spark/Jupyter can query those tables through Hive Metastore and RustFS.
3. Dremio Community can connect to the Hive 3.x Metastore using Kerberos/SASL and query Hive-cataloged Iceberg tables.
4. The Hive authorization mapping recognizes the two test users and enforces the selected database grants.
5. `user_a` can query `databaseA` and is denied access to `databaseB` from Dremio and Spark in Jupyter.
6. `user_b` can query both databases from Dremio and Spark in Jupyter.
7. Jupyter Spark sessions use the matching user's Kerberos principal and RustFS credentials; keytabs are not shared across users.
8. Setup and cleanup documentation describes the local-only DummyAuthenticator limitation, credential lifecycle, startup sequence, and manual allow/deny demonstration.
9. A distinct `admin` principal has mapped component-admin access across the in-scope platform components; component-native credentials remain separate.
10. The `write-service-account` Kerberos principal and Dremio local user are created. Using its Dremio credentials over JDBC, it can create at least a table in the designated existing Space, without platform-admin privileges.
11. Airflow/Jenkins deployment changes and Airflow-triggered Spark execution are deferred; the created service identity is available for that future integration.
12. The sample database/table ETL authenticates as `write-service-account`, has only the intended Hive and RustFS write permissions, and does not use `admin` credentials.

## Scope Exclusions

- Direct S3/RustFS access is not an acceptance path for this intent.
- HiveServer2 is not included unless planning finds it necessary to satisfy database-level authorization; such a scope change must be reviewed before implementation.
- External identity providers, production-ready authentication, and production KDC deployment are out of scope.
- Airflow/Jenkins integration is deferred. This intent does not change the sibling `airflow-spark-jenkins/` deployment or launch Airflow-triggered Spark jobs.
- No claim of production security or organization-wide identity federation is made.

## Technical Constraints and Feasibility Items

- Dremio Community supports Hive Metastore as a source and local identities. Dremio's current edition matrix distinguishes Community from Enterprise identity-provider and RBAC features. The selected design therefore relies on Hive source impersonation and Hive/Hadoop authorization rather than Dremio-managed role grants. See [Dremio editions](https://docs.dremio.com/editions/) and [Dremio Hive source configuration](https://docs.dremio.com/current/data-sources/lakehouse-catalogs/hive/).
- Dremio JDBC connectivity is required for the writer use case, but Dremio documents SQL `GRANT`/`REVOKE` RBAC commands as Enterprise features. The requested ability for a non-admin Community user to create objects in a Space must be verified against the exact Dremio version and available Community permissions before implementation; if Community cannot provide it, planning must return with the smallest viable option for review rather than silently granting admin access.
- Hive storage-based authorization relies on permissions for the filesystem paths corresponding to databases and tables. The selected backing store is S3-compatible RustFS, so the exact integration among Hive Metastore authorization checks, per-user Spark S3 credentials, and Dremio's Hive source must be validated before treating the allow/deny scenario as achieved. See [Apache Hive storage-based authorization](https://cwiki.apache.org/confluence/display/hive/storage%2Bbased%2Bauthorization%2Bin%2Bthe%2Bmetastore%2Bserver).
- The sample ETL must perform Hive database/table creation and RustFS writes as `write-service-account`. Verify the selected Spark/Hive/RustFS configuration can grant this identity the required DDL and object-store permissions without administrator credentials; direct RustFS authorization remains outside the user demonstration.
- Hive SQL-standard authorization is associated with HiveServer2 query authorization; HiveServer2 is excluded from the selected baseline. If the standalone metastore plus storage-based authorization cannot enforce the required database outcomes across Dremio and Spark, planning must present the smallest necessary architecture adjustment for approval before implementation.
- The currently inspected `jupyter-platform/` configuration points Spark to Nessie and injects shared RustFS admin credentials. These settings must be replaced; copying them unchanged would not meet the per-user identity requirement.
- The existing Airflow Compose/DockerOperator setup currently passes shared RustFS admin credentials to Spark and uses Nessie catalog settings. It is outside this intent; future integration must replace those settings with the distinct service identity and Hive/RustFS write path.
- The Dremio writer requirement is direct object creation through the Dremio JDBC interface in an existing Space. It is separate from Spark writing the Hive catalog and RustFS.

## User Decisions Recorded

- Standalone Hive Metastore in Compose; no HiveServer2 in the baseline.
- Hive 3.x with PostgreSQL; compatible release to be selected during planning.
- Disposable local KDC and generated test keytabs.
- Dremio Community local accounts; Kerberos service identity for Hive connection; per-user Hive impersonation.
- JupyterHub based on `jupyter-platform/`; DummyAuthenticator retained for the isolated demo.
- Separate Kerberos identities for each user's Spark session.
- Direct RustFS authorization checks excluded; per-user RustFS credentials remain required for Spark in Jupyter.
- `user_a`: databaseA only. `user_b`: databaseA and databaseB.
- Additional principals/users: `admin` with component-specific administrator mappings; a `write-service-account` Kerberos and RustFS identity plus a Dremio local user. It runs sample Spark ETL to create/populate both Hive databases and can create objects in a designated existing Dremio Space over JDBC. Airflow/Jenkins integration is deferred.
- Security Baseline off; Property-Based Testing partial; Resiliency Baseline off.
