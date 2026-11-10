# Application Components — StarRocks OSS Integration

## Scope

This design adds StarRocks as a local analytical SQL service over the existing Hive Metastore, Iceberg tables, and RustFS warehouse. It preserves Spark/Jupyter and shared platform data. Airflow/Jenkins and Ranger remain out of scope. Detailed configuration, SQL grants, retry behavior, image selection, and compatibility handling belong to later Construction design.

## Components

### 1. StarRocks Runtime

**Purpose:** Run the single-FE/single-BE StarRocks OSS deployment and provide the MySQL-compatible SQL endpoint and FE management endpoint.

**Responsibilities:**

- Define pinned FE and BE services, configuration, health/readiness, and named volumes under the project Compose deployment.
- Bind host-facing SQL and UI ports to loopback only.
- Consume mounted StarRocks Kerberos configuration/keytab and dedicated RustFS credentials without exposing their values in tracked configuration or logs.
- Connect to the existing HMS and RustFS services on the Compose network.
- Leave all existing platform services, volumes, and data unchanged.

**Interfaces:** StarRocks SQL protocol for clients and bootstrap; FE/BE service configuration and mounted credentials for dependencies; Compose health/readiness for operations.

### 2. Identity Provisioning

**Purpose:** Extend the existing identity provisioning boundary to create StarRocks-only service credentials while preserving current principals and credentials.

**Responsibilities:**

- Provision a dedicated StarRocks Kerberos service principal/keytab for HMS access through the existing KDC/provisioning mechanisms.
- Provision a distinct RustFS identity/policy with read/write access scoped to the Iceberg warehouse prefix.
- Store local generated secrets only in ignored `.runtime/credentials/` material and avoid printing them.
- Provide StarRocks with mounted keytab/configuration and S3 credential contracts.
- Preserve Hive, Spark, notebook, admin, user, and writer identities; do not rotate them implicitly.

**Interfaces:** Existing identity-provisioning commands/scripts and protected credential files; KDC and RustFS administrative interfaces remain dependencies. Exact script inputs, idempotency, and policy document are deferred to Functional Design.

### 3. StarRocks SQL Bootstrap

**Purpose:** Configure StarRocks SQL-side catalog access and native users/roles/grants after FE readiness.

**Responsibilities:**

- Create or reconcile the external Iceberg catalog that points to the existing HMS and RustFS warehouse.
- Provision native SQL identities and grants for `admin`, `user_a`, `user_b`, and `write_service_account` (mapping from `write-service-account` documented where needed).
- Apply the approved database access matrix: `user_a` reads databaseA only; `user_b` reads both; `write_service_account` reads/writes both but has no StarRocks administrative privilege; `admin` has full StarRocks access.
- Use an explicit, repeatable operator-invoked bootstrap command after dependencies and FE are ready.
- Redact credentials from terminal output and logs.

**Interfaces:** StarRocks SQL over the internal SQL endpoint, input configuration/credential references from the identity provisioning component, and Compose readiness from the runtime. SQL syntax and idempotent reconciliation behavior are deferred to Functional Design.

### 4. Existing Shared Lakehouse Services

**Purpose:** Continue providing catalog, object storage, and existing workload capabilities.

**Responsibilities:** Hive Metastore remains the Iceberg catalog; PostgreSQL remains Hive's metadata database; RustFS remains object storage; KDC remains the Kerberos realm; Spark/Jupyter remain supported workload services.

**Interfaces:** Existing HMS Thrift, Kerberos, RustFS S3-compatible, and Spark catalog/storage interfaces. StarRocks adds a client to these services without changing their ownership or data.

### 5. SQL Clients and Operations

**Purpose:** Allow local users/operators to connect and administer the StarRocks SQL service.

**Responsibilities:** Use native StarRocks SQL identities for authorization. Operators start services, wait for readiness, provision identities, and explicitly run SQL bootstrap. Local documentation explains endpoints, startup order, resources, and safe rollback.

**Interfaces:** MySQL-compatible SQL client on a loopback-bound host port and documented Compose/CLI operations.
