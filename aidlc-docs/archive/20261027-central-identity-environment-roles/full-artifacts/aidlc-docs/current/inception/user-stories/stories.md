# User Stories — Central Identity and Environment Access

Stories turn the approved role matrix into outcomes that can be verified across identity, metadata, object storage, interactive access, and StarRocks. Requirements are linked by section because the approved requirements do not yet assign individual requirement IDs.

## Feature: Identity and role lifecycle

### US-01 — Manage human identities and role membership centrally

**As a platform identity administrator,** I want human identities and their role-group membership managed in FreeIPA, **so that** access assignments have one authoritative source.

**Acceptance criteria**

- `developer-user` and `analyst-user` resolve to their approved FreeIPA role groups.
- `write-service-account` is a service identity and is not allowed to log into JupyterHub.
- `admin` retains platform administration privileges independently from the data-user groups.
- Account and role-group changes can be verified in FreeIPA and are consumed by the configured identity synchronization path.

**Persona**: Platform Identity Administrator  
**Requirements**: Identity and role matrix; Identity and integration requirements

### US-02 — Reconcile group membership to data-access policies

**As a platform identity administrator,** I want FreeIPA role-group membership reflected in RustFS and supported query authorization, **so that** granting or revoking a role changes the user’s effective data access.

**Acceptance criteria**

- Adding a user to a role group grants only the read/write scope defined for that role.
- Removing a user from a role group removes that role’s access after the configured reconciliation and credential/session invalidation process.
- A user’s access is denied by the enforcing service when the user is outside the relevant role group; hiding a source or UI object alone does not count as enforcement.
- Reconciliation failures are visible to the operator and do not silently broaden access.
- Preserve the existing `write-service-account` RustFS S3 access key. Its Kerberos keytab is reissued under FreeIPA as approved; the service principal name is preserved where compatible.

**Persona**: Platform Identity Administrator; Lakehouse Operator  
**Requirements**: Identity and role matrix; Identity and integration requirements; Authorization requirements; Migration and safety constraints

## Feature: Environment storage and database boundaries

### US-03 — Keep production data in the existing lake bucket

**As a lakehouse operator,** I want production databases to continue using the existing `lake` bucket, **so that** current production objects remain in place and available under the approved production boundary.

**Acceptance criteria**

- Existing objects in `lake` are preserved; provisioning does not migrate or delete them.
- Production database locations are explicitly under `s3a://lake/warehouse/`.
- A conflicting production database location causes provisioning to stop with a clear error before mutation.

**Persona**: Lakehouse Operator  
**Requirements**: Approved storage layout; Migration and safety constraints; Implementation assumptions

### US-04 — Isolate development and UAT data in separate buckets

**As a developer,** I want development and UAT databases stored in their environment buckets, **so that** writes and reads can be scoped independently from production.

**Acceptance criteria**

- Provisioning creates `lake-dev` and `lake-uat` only when absent and preserves contents if they already exist.
- Development database locations, including `lhdev*`, are explicitly under `s3a://lake-dev/warehouse/`.
- UAT database locations are explicitly under `s3a://lake-uat/warehouse/`.
- New database locations do not silently fall back to the production bucket.

**Persona**: Developer; Lakehouse Operator  
**Requirements**: Approved storage layout; Authorization requirements; Migration and safety constraints; Implementation assumptions

## Feature: Direct Spark and RustFS authorization

### US-05 — Enforce developer read-all and development-write access

**As a developer,** I want Spark to let me read all approved environments and write only development data, **so that** I can build and validate workloads without changing UAT or production.

**Acceptance criteria**

- `developer-user` can read approved paths in `lake`, `lake-dev`, and `lake-uat`.
- `developer-user` can create and modify objects under approved `lake-dev` paths.
- Writes by `developer-user` to `lake` and `lake-uat` are denied by the object-storage authorization layer.
- Metastore metadata access and Spark data access agree with the environment/database mapping.

**Persona**: Developer  
**Requirements**: Identity and role matrix; Authorization requirements; Verification acceptance criteria

### US-06 — Enforce analyst read-only production access

**As an analyst,** I want Spark and approved query tools to expose production data read-only, **so that** analysis cannot alter production or access non-production data.

**Acceptance criteria**

- `analyst-user` can read approved production databases and paths in `lake`.
- Reads from `lake-dev` or `lake-uat` are denied.
- Writes to all three buckets are denied by the object-storage authorization layer.
- A denied operation is reported as an authorization failure and does not change objects or metadata.

**Persona**: Analyst  
**Requirements**: Identity and role matrix; Authorization requirements; Verification acceptance criteria

### US-07 — Run ETL with the dedicated writer service identity

**As an ETL workload owner,** I want Airflow-triggered Spark jobs to use `write-service-account`, **so that** scheduled workloads can read and write the approved data paths without depending on a human identity.

**Acceptance criteria**

- The service identity can read and write approved paths in `lake`, `lake-dev`, and `lake-uat`.
- Its credentials are not available to interactive human users through JupyterHub.
- Credentials are supplied through the approved secret/keytab mechanism and do not appear in workload bundles, source code, or ordinary logs.
- Production data, the writer's RustFS S3 access key, and its service-principal name remain intact through identity cutover; its Kerberos keytab is reissued under FreeIPA and dependent services are updated in a staged cutover.

**Persona**: ETL Workload Owner; Lakehouse Operator  
**Requirements**: Identity and role matrix; Identity and integration requirements; Migration and safety constraints

## Feature: JupyterHub and Spark identity

### US-08 — Authenticate human notebook users with FreeIPA

**As a developer or analyst,** I want to sign in to JupyterHub with my FreeIPA credentials, **so that** the notebook platform uses the central human identity source.

**Acceptance criteria**

- Valid members of the approved human-user groups can authenticate over TLS.
- Invalid credentials and users outside the approved groups are rejected.
- Data-user login does not grant JupyterHub platform-administrator privileges.
- `write-service-account` cannot authenticate interactively.

**Persona**: Developer; Analyst; Platform Identity Administrator  
**Requirements**: Identity and integration requirements; Verification acceptance criteria

### US-09 — Use the requesting user’s identity for notebook Spark access

**As a notebook user,** I want Spark access to use my own authorized identity, **so that** my FreeIPA role boundaries apply to direct metastore and RustFS access.

**Acceptance criteria**

- A notebook session obtains and uses a Kerberos identity for its signed-in user without storing the user’s password.
- A session cannot use another user’s Kerberos ticket or RustFS credentials.
- Spark reads and writes are denied or allowed according to the user’s role matrix, even if a resource is reachable through a manually issued query.
- Logging out or revoking the user prevents subsequent access according to the documented ticket, credential, and session expiry/revocation behavior.

**Persona**: Developer; Analyst; Lakehouse Operator  
**Requirements**: Identity and integration requirements; Authorization requirements; Verification acceptance criteria

## Feature: StarRocks authorization with Ranger

### US-10 — Enforce StarRocks query permissions from directory-backed roles

**As an analyst or developer,** I want StarRocks query access to follow my assigned role, **so that** StarRocks does not grant broader access than the approved environment matrix.

**Acceptance criteria**

- Ranger/StarRocks authorization allows developer reads across the approved environments and denies developer writes outside development.
- Ranger/StarRocks authorization allows analyst reads only against production and denies all analyst writes.
- The `write-service-account` StarRocks execution identity has only its approved workload scope, and end-user query authorization remains role-aware.
- Ranger policies govern StarRocks requests only; direct Spark-to-RustFS access is verified at RustFS and the applicable metastore controls.
- Policies cover intended newly created databases/tables or fail closed until the policy is updated.

**Persona**: Developer; Analyst; Lakehouse Operator  
**Requirements**: Authorization requirements; Verification acceptance criteria

## Feature: Safe identity cutover

### US-11 — Replace test users without losing data or administrative access

**As a platform identity administrator,** I want to retire `user_a` and `user_b` only after replacement identities pass verification, **so that** the cutover preserves data and does not lock out administrators or ETL workloads.

**Acceptance criteria**

- New identities pass the required login, Kerberos, RustFS, Hive/Spark, and StarRocks authorization checks before old identities are disabled.
- After cutover, `user_a` and `user_b` cannot authenticate or access data.
- Existing persistent workspaces and production bucket objects are preserved.
- `admin` and `write-service-account` remain functional with their existing credentials.
- Rollback instructions restore access without deleting user data or broadening policies.

**Persona**: Platform Identity Administrator; Lakehouse Operator  
**Requirements**: Migration and safety constraints; Verification acceptance criteria

## Story-to-Requirement Coverage

| Requirement area | Stories |
|---|---|
| Identity source and role assignments | US-01, US-02, US-08 |
| Bucket layout and database locations | US-03, US-04 |
| Direct Spark/RustFS authorization | US-05, US-06, US-07, US-09 |
| JupyterHub authentication | US-08, US-09 |
| StarRocks/Ranger authorization | US-10 |
| Safe migration and credential preservation | US-02, US-07, US-11 |
