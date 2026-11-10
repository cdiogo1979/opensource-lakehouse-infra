# Unit of Work Definitions

## Decomposition Principles

- One maintainer owns the integrated local Docker Compose PoC.
- Units follow the approved technical component boundaries and existing project structure.
- Units may be developed independently after shared contracts are agreed; integrate them in dependency order into one Compose deployment.
- A unit is a reviewable work grouping, not an independently deployed service by default.
- Component-specific SQL examples, lifecycle changes, and operator documentation stay with the component that owns the behavior. No standalone documentation unit is created.
- No additional runtime or authorization authority is introduced. The identity/permission provisioner remains a one-shot coordinator of component-owned interfaces.

## Units

### Unit 1 — Compose, catalog, identity foundation, and storage

**Scope and owners:** Compose orchestration and lifecycle, PostgreSQL for Hive metadata, Kerberos KDC, Hive Metastore, RustFS, and bucket initialization.

**Responsibilities:**

- Define Compose services, networks, volumes, readiness, and lifecycle ordering for the foundation services.
- Replace the Nessie catalog/persistence boundaries with Hive Metastore and its PostgreSQL backend.
- Provide catalog, storage, and KDC interfaces consumed by workload and query units.
- Define the Hive-owned authorization integration needed for database-level outcomes; select and validate the concrete mechanism in Functional Design.
- Document local startup/cleanup, volume behavior, and foundational prerequisites.

**Primary stories:** US-CAT-01, US-AUTH-01, US-DOC-01.

**Canonical design paths:** `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/compose-orchestration.md`, `lifecycle-scripts.md`, `metastore-postgresql.md`, `kerberos-kdc.md`, `hive-metastore.md`, `rustfs.md`, and `bucket-initializer.md`.

**Integration outputs:** Compose network/service contracts; Hive Metastore endpoint and schema readiness; KDC realm/principal conventions; RustFS bucket and warehouse conventions; Hive authorization capability findings.

### Unit 2 — Identity and permission provisioning

**Scope and owner:** The approved one-shot identity/permission provisioner, using setup interfaces owned by KDC, Hive, RustFS, Dremio, PostgreSQL, Spark, and JupyterHub.

**Responsibilities:**

- Create or coordinate creation of `user_a`, `user_b`, `admin`, `write-service-account`, and required service identities.
- Coordinate component-native accounts and credentials without reusing Kerberos credentials as web or S3 credentials.
- Request least-privilege Hive and RustFS permissions from the owning systems; prepare effective-user mappings for Dremio.
- Support setup ordering where some database-specific read grants may only be applied after ETL creates the databases. `write-service-account` must receive the minimal setup permissions needed before ETL.
- Keep generated secrets/keytabs local and out of tracked files, logs, and image layers.

The unit coordinates setup only. Query-time authorization remains with the owning components; this unit does not implement a central policy engine.

**Primary stories:** US-ID-01, US-ID-02.

**Related stories:** US-AUTH-01 (grant provisioning coordination), US-CAT-02, US-JH-01, US-ID-03, US-JDBC-01.

**Canonical design path:** `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/identity-provisioner.md`.

**Integration outputs:** Principal/account manifest, component setup interfaces, credential delivery conventions, permission provisioning results, and sequencing contract with ETL.

### Unit 3 — Spark runtime and sample ETL

**Scope and owners:** Spark runtime, TPCH generator, TPCH loader, and the loader's requested JDBC Space/view setup operation.

**Responsibilities:**

- Configure Spark to use Hive Metastore and RustFS in place of Nessie.
- Run sample ETL as `write-service-account`; create and populate `databaseA` and `databaseB` with Iceberg tables in RustFS.
- Create two matching Dremio Spaces and a view for every Hive table over JDBC using `write-service-account`, subject to the Dremio Community feasibility gate.
- Report effective identity and created databases/tables/views so the operator can inspect outcomes.
- Keep generator and loader responsibilities within their existing workload boundaries.

**Primary stories:** US-CAT-02, US-JDBC-01.

**Related stories:** US-CAT-01, US-ID-01, US-AUTH-02, US-DOC-01.

**Canonical design paths:** `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/spark-runtime.md`, `tpch-generator.md`, and `tpch-loader.md`.

**Integration outputs:** Hive catalog properties, ETL identity/credential contract, database/table manifest, and JDBC view-creation result. Do not elevate the writer if Community blocks the requested operations.

### Unit 4 — Dremio source and query identity

**Scope and owner:** Existing Dremio service and its source/user/JDBC configuration.

**Responsibilities:**

- Configure a Hive source using Kerberos/SASL and a Dremio service identity.
- Map Dremio local query usernames to Hive effective users and keep proxy-user rules narrow.
- Provision/configure Dremio's required local users through supported interfaces, coordinating with Unit 2.
- Query the cataloged Iceberg tables and demonstrate the Dremio allow/deny matrix.
- Validate whether the selected Dremio Community version supports the writer's non-admin Space/view operations over JDBC; return a limitation for review rather than granting admin privileges.
- Keep Dremio-owned query examples and documentation with this unit.

**Primary stories:** US-ID-03, US-AUTH-02.

**Related stories:** US-CAT-01, US-CAT-02, US-ID-02, US-JDBC-01, US-DOC-01.

**Canonical design path:** `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/dremio.md`.

**Integration outputs:** Hive source connection contract, username mapping, JDBC behavior and feasibility result, and observable allow/deny outcomes.

### Unit 5 — JupyterHub and per-user Spark access

**Scope and owners:** JupyterHub based on `jupyter-platform/` and user-isolated Spark session configuration.

**Responsibilities:**

- Configure Hub, DockerSpawner, and Spark single-user images for the local PoC.
- Retain DummyAuthenticator as a development-only label mechanism and document its limitation.
- Mount each user's own keytab read-only and provide distinct RustFS credentials to their Spark session.
- Demonstrate Spark access to both databases according to the user's profile.
- Keep notebook query examples and user-session instructions with this unit.

**Primary stories:** US-JH-01, US-AUTH-03.

**Related stories:** US-CAT-01, US-ID-01, US-ID-02, US-AUTH-01, US-DOC-01.

**Canonical design paths:** `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/jupyterhub.md` and `spark-runtime.md`.

**Integration outputs:** User-to-credential mapping, isolated notebook mounts/environment contract, and Spark authorization outcomes.

## Shared Feasibility Gates

These are cross-unit acceptance gates, not new units:

1. Verify Hive 3.x, Spark/Iceberg, Dremio Community, and metastore schema compatibility.
2. Verify Hive authorization over standalone Metastore and RustFS enforces the required database outcomes in both query paths.
3. Verify Dremio's Hive source reads RustFS-backed Iceberg data with the expected effective identity behavior.
4. Verify `write-service-account` can create the matching Spaces/views over JDBC without platform administrator privileges.

If a gate fails, document evidence and the smallest proposed adjustment for user review before changing the approved scope.
