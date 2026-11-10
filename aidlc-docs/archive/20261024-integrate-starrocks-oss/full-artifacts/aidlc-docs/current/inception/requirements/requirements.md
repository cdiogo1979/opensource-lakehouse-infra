# StarRocks OSS Integration — Requirements

## Intent Analysis

- **User request**: Integrate StarRocks OSS into the existing Hive/RustFS lakehouse after Dremio removal.
- **Request type**: New analytical engine integration.
- **Scope estimate**: Cross-component Compose, catalog/storage, identity, authorization, operations, and verification work in `hive-dremio-rustfs`.
- **Complexity estimate**: Moderate to complex. Query and write compatibility, Kerberos to HMS, S3-compatible storage, authorization, and resource limits require integration validation.

## Goals

Add StarRocks OSS as a local SQL analytics engine for the existing Iceberg tables in Hive Metastore and RustFS. Retain Spark as the existing ETL and notebook engine. StarRocks must support both querying and writing Iceberg tables while enforcing the existing per-user Spark/Jupyter access matrix through StarRocks SQL permissions.

## Out of Scope

- Modifying the sibling `airflow-spark-jenkins` project or migrating its Spark jobs from Nessie in this intent.
- Adding Apache Ranger; use StarRocks native users and SQL roles/grants for this PoC.
- Replacing Hive Metastore, RustFS, Spark, JupyterHub, or the TPCH ETL.
- Propagating end-user Kerberos identity from the StarRocks SQL client through HMS and RustFS. StarRocks uses a service identity for catalog access and object-store access; SQL users are authenticated/authorized separately.
- Production high availability, external identity-provider setup, and production deployment.

## Functional Requirements

### FR-1 — Add StarRocks OSS

Add a single-node StarRocks OSS deployment to the existing Docker Compose project, using one FE and one BE. Use persistent named volumes, bind host-facing SQL/UI ports to loopback, and document local resource requirements. Pin a current stable release after compatibility review; do not use a floating `latest` tag.

### FR-2 — Connect to the existing Iceberg catalog and data

Configure StarRocks to use the existing Hive Metastore Thrift service as its Iceberg catalog and RustFS as its S3-compatible object store. Preserve the existing bucket, warehouse paths, Hive metadata, and Iceberg table contents. Configure the in-network RustFS endpoint, path-style access, region, and TLS mode to match the current service.

### FR-3 — Query and write Iceberg tables

StarRocks must discover and query existing Iceberg databases/tables and support writes to Iceberg tables. Spark remains a supported writer. Validate Iceberg table-version, file-format, and commit compatibility against the tables produced by this project before considering the integration complete.

### FR-4 — Use a dedicated service identity for storage

Provision a dedicated RustFS identity for StarRocks with read/write access limited to the Iceberg warehouse prefix. Keep this credential distinct from user, Hive, admin, and Spark writer credentials. Store generated local credentials only in ignored `.runtime/credentials/` files; do not print or commit secrets.

### FR-5 — Authenticate to secured Hive Metastore

Configure a dedicated StarRocks Kerberos service principal/keytab for access to the Kerberos-protected Hive Metastore, with a renewable/refreshed TGT lifecycle appropriate for the container. Do not reuse end-user keytabs. Preserve existing Hive, Spark, and notebook identities.

### FR-6 — Provide StarRocks SQL users and permissions

Provision StarRocks native SQL users and roles/grants for `admin`, `user_a`, `user_b`, and `write-service-account`. The StarRocks SQL user identifier for `write-service-account` may use `write_service_account` if required by StarRocks naming rules; document the mapping while keeping the Kerberos/RustFS principal unchanged. Generate and persist local passwords using the project's protected runtime credential convention.

Implement the current Spark/Jupyter authorization matrix:

| StarRocks identity | `databaseA` | `databaseB` |
|---|---|---|
| `user_a` | Read | Deny |
| `user_b` | Read | Read |
| `write_service_account` (`write-service-account`) | Read and write | Read and write |
| `admin` | Full StarRocks access | Full StarRocks access |

These SQL grants control access through StarRocks. They do not replace or change direct Spark, Hive, or RustFS authorization.

### FR-7 — Preserve existing services and data

Keep all existing Compose services, named volumes, identities, credentials, Iceberg metadata/data, and notebook workspaces intact. Do not perform destructive cleanup or runtime migration as part of adding StarRocks.

## Non-Functional Requirements

- **NFR-1 Local security**: Expose SQL and UI endpoints on loopback only. Keep passwords and keytabs outside tracked source/configuration and redact them from logs.
- **NFR-2 Repeatability**: Compose configuration and provisioning must be idempotent and must not rotate existing credentials implicitly.
- **NFR-3 Persistence**: FE/BE state uses named volumes and survives container recreation.
- **NFR-4 Compatibility**: Pin a reviewed OSS image version/digest and verify the actual Hive Metastore 3.1.3, Iceberg tables, and RustFS combination.
- **NFR-5 Resource awareness**: Document the local CPU/memory/storage requirement and startup order for the single-node PoC.
- **NFR-6 Maintainability**: Keep StarRocks-specific configuration/bootstrap assets under an appropriately named `infra/starrocks/` directory and update project operation documentation.

## Acceptance Criteria

1. Compose validates and starts the StarRocks FE/BE services with persistent state and only loopback host bindings.
2. StarRocks authenticates to the Hive Metastore using its dedicated service principal and discovers the current Iceberg databases and tables.
3. StarRocks reads existing table data from RustFS using its dedicated identity.
4. A controlled write through StarRocks updates an Iceberg table, and a query confirms the committed result. The test uses an explicitly designated test table or reversible test data and preserves existing sample data.
5. The StarRocks SQL access matrix is demonstrated: `user_a` can read `databaseA` and is denied on `databaseB`; `user_b` can read both; the writer can read/write both; admin has full StarRocks access.
6. Credentials/keytabs do not appear in committed files or test output. Provisioning does not rotate existing secrets.
7. Existing Hive, Spark, JupyterHub, RustFS data, and Airflow/Jenkins sibling project remain unchanged by this intent.

## Decisions Recorded

- Airflow/Jenkins sibling project remains out of scope.
- StarRocks supports both query and write workloads; Spark remains in place.
- Use native StarRocks SQL users/roles; defer Ranger.
- Dedicated StarRocks Kerberos identity for HMS and dedicated read/write RustFS identity for the Iceberg warehouse.
- Local single FE/BE with persistent volumes and loopback ports.
- Security Baseline: disabled. Property-Based Testing: partial for changed pure functions/serialization. Resiliency Baseline: disabled.

## Open Implementation Validation

- Confirm which Iceberg format version, delete files, compression, and table features the current sample tables use.
- Confirm the selected StarRocks OSS release works with the current Iceberg/HMS/RustFS configuration and Kerberos setup.
- Verify StarRocks native grants block unauthorized users even though the StarRocks service identity can read both warehouse prefixes.
- Verify local memory/disk requirements against the host before building/running the stack.
