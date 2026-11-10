# StarRocks Integration — User Stories

Stories are organized by feature, sized as independently testable capabilities, and use numbered measurable acceptance criteria as selected in the approved story plan. They map to the approved requirements and do not add Ranger or changes to the sibling Airflow/Jenkins project.

## Feature: Query Existing Iceberg Data

### US-01 — Query the shared Iceberg lake

**As** an authorized analyst, **I want** to query existing Iceberg tables in StarRocks through SQL, **so that** I can analyze shared lakehouse data without moving it into a separate engine-owned copy.

**Personas**: `user_a`, `user_b`  
**Requirements**: FR-2, FR-3, FR-6

**Acceptance Criteria**

1. StarRocks discovers `databaseA` and `databaseB` through the Hive Metastore Iceberg catalog.
2. `user_a` can query an existing sample table in `databaseA`.
3. `user_b` can query existing sample tables in both `databaseA` and `databaseB`.
4. Read queries retrieve the table data stored in RustFS and return valid results.
5. An access failure is reported as an authorization denial only when catalog connectivity and storage access are healthy.

## Feature: Write Iceberg Data

### US-02 — Write Iceberg data as the ETL service account

**As** the `write-service-account` ETL identity, **I want** to write Iceberg data in both approved databases through StarRocks, **so that** pipeline-produced data can be committed to the shared lakehouse catalog and storage.

**Personas**: ETL Writer Service Account  
**Requirements**: FR-3, FR-4, FR-6

**Acceptance Criteria**

1. The StarRocks SQL identity `write_service_account` (or documented valid equivalent) can write to Iceberg tables in `databaseA` and `databaseB`.
2. A write test uses a designated disposable test table or explicitly reversible test data; it does not overwrite or drop existing sample tables.
3. StarRocks can query the committed test result after the write completes.
4. The StarRocks RustFS credential has the required read/write access only within the approved Iceberg warehouse prefix.
5. `user_a` and `user_b` cannot perform writes through StarRocks.

## Feature: Enforce SQL Authorization

### US-03 — Restrict query access by StarRocks identity

**As** a data owner, **I want** StarRocks SQL permissions to match the existing Spark/Jupyter database access matrix, **so that** each identity can access only the datasets permitted for its role.

**Personas**: `user_a`, `user_b`, ETL Writer Service Account, StarRocks Administrator  
**Requirements**: FR-6

**Acceptance Criteria**

1. `user_a` can read `databaseA` and receives an authorization denial when querying `databaseB`.
2. `user_b` can read both `databaseA` and `databaseB`.
3. `user_b` receives an authorization denial when attempting a write.
4. `write_service_account` can read and write both databases but cannot manage StarRocks users or configuration.
5. `admin` has full access within StarRocks.
6. These grants apply to SQL access through StarRocks; the story makes no claim that StarRocks grants control direct Spark, Hive, or RustFS access.

## Feature: Configure Identities and Catalog Access

### US-04 — Connect StarRocks using dedicated service credentials

**As** a platform operator, **I want** StarRocks to use its own Kerberos service principal for HMS and its own scoped RustFS identity for Iceberg objects, **so that** the query service can access the catalog and data without borrowing human or unrelated service credentials.

**Personas**: Platform Operator  
**Requirements**: FR-2, FR-4, FR-5, FR-6, NFR-1, NFR-2

**Acceptance Criteria**

1. StarRocks obtains and refreshes a Kerberos ticket using its dedicated service keytab when accessing the secured Hive Metastore.
2. No user or notebook keytab is mounted into StarRocks.
3. StarRocks accesses RustFS with its dedicated service identity, scoped to read/write the Iceberg warehouse prefix.
4. Native StarRocks SQL users are provisioned separately from Kerberos and RustFS identities.
5. Generated passwords and keytabs are stored under ignored runtime credentials, are not committed, and are redacted from output.
6. Re-running identity provisioning preserves existing credentials and does not rotate them implicitly.

## Feature: Operate the Local Query Service

### US-05 — Run StarRocks in the local PoC

**As** a platform operator, **I want** a pinned single-FE/single-BE StarRocks service with persistent state and loopback-only host endpoints, **so that** I can use the SQL engine locally without disturbing the existing lakehouse services or exposing it on the network.

**Personas**: Platform Operator, StarRocks Administrator  
**Requirements**: FR-1, FR-7, NFR-1, NFR-2, NFR-3, NFR-4, NFR-5, NFR-6

**Acceptance Criteria**

1. Compose uses an explicit supported StarRocks OSS version/digest, not a floating `latest` tag.
2. The StarRocks SQL and UI endpoints bind to host loopback only.
3. FE/BE data uses named volumes and remains available after container recreation.
4. Startup, readiness, resource requirements, and connection details are documented.
5. Existing Hive, PostgreSQL, KDC, RustFS, Spark, JupyterHub services, volumes, and sample data remain intact.
6. Compose validation and StarRocks health checks pass before catalog/query integration is considered ready.

## INVEST Review

- **Independent**: Each feature story represents a separately testable outcome.
- **Negotiable**: Details such as exact image release and port numbers remain implementation decisions within the approved requirements.
- **Valuable**: Each story enables query, write, access control, service identity, or local operations.
- **Estimable**: Stories are grouped by bounded service capability and requirement IDs.
- **Small**: Each story can be designed and verified within this integration intent without touching the Airflow/Jenkins sibling project.
- **Testable**: Numbered criteria define allowed/denied access, query/write results, credential boundaries, and Compose behavior.
