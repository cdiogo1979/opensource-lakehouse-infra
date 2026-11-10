# Services — StarRocks OSS Integration

## Service Definitions

### StarRocks FE/BE Service

The FE coordinates SQL sessions and query planning; the BE executes scans and writes. The PoC runs one FE and one BE with persistent named volumes. Host SQL and FE UI endpoints bind to loopback only. FE/BE internal communication remains on the Compose network.

### Identity Provisioning Service

The existing identity provisioner is extended with StarRocks-specific operations. It provisions a dedicated Kerberos service principal/keytab for HMS and a separate RustFS key/policy scoped to the Iceberg warehouse. It reports redacted status and does not implicitly rotate existing credentials.

### SQL Bootstrap Service

An explicit, repeatable operator command connects to a ready FE using a StarRocks administrator bootstrap identity. It configures/reconciles the Iceberg catalog and native SQL accounts/roles/grants. It uses mounted configuration and protected credential references; it does not introduce a separate control-plane API or long-running bootstrap service.

### Shared Catalog and Storage Services

Hive Metastore, PostgreSQL, RustFS, and Kerberos remain existing shared services. StarRocks consumes HMS metadata under its own Kerberos service identity and reads/writes Iceberg objects with its separate RustFS service identity. Spark/Jupyter continue using their existing paths and identities.

### SQL Client Service

Users connect to the loopback-bound MySQL-compatible endpoint with native StarRocks SQL credentials. StarRocks SQL permissions enforce the per-user access matrix; the service credential used by StarRocks to reach HMS/RustFS is not propagated as a user identity.

## Startup and Bootstrap Orchestration

1. Start or verify the existing KDC, HMS, PostgreSQL, and RustFS dependencies.
2. Run the identity provisioning operation and confirm protected StarRocks credential references exist.
3. Start StarRocks FE/BE and wait for Compose health/readiness checks.
4. Explicitly invoke the repeatable SQL bootstrap command to configure the Iceberg catalog and SQL accounts/grants.
5. Connect through the loopback SQL endpoint and perform read, controlled-write, and authorization checks during the later verification stage.

Compose health/dependency ordering reports readiness; it does not silently provision identities or automatically apply SQL grants. Detailed command contracts and failure/retry behavior will be designed during Construction.

## Security and Ownership Boundaries

- Kerberos service credentials authenticate the StarRocks service to HMS; they are separate from StarRocks SQL user passwords.
- RustFS service credentials authorize StarRocks object access and are separate from Kerberos and SQL credentials.
- StarRocks SQL users/roles authorize client operations inside StarRocks; direct Spark, Hive, and RustFS access remains governed by their existing controls.
- Secrets stay in ignored runtime credential files or mounted secret material and are redacted from logs/output.
- No identity or grant configuration is added to the sibling Airflow/Jenkins project.
