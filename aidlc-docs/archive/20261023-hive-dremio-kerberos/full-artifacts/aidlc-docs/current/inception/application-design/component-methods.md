# Component Methods and Operations

These are high-level contracts, not implementation signatures. Detailed validation, authorization rules, retries, and error behavior are deferred to per-unit Functional Design.

| Component | Operation | Inputs | Outputs | Purpose |
|---|---|---|---|---|
| Kerberos KDC | `createPrincipal(principalName, principalType)` | Principal name and category (service, user, admin, writer) | Principal reference or setup result | Creates identities in the disposable realm. |
| Kerberos KDC | `createKeytab(principalName, outputPath)` | Existing principal and local output location | Local keytab reference | Produces runtime credentials without tracking them in source. |
| Identity/permission provisioner | `provisionIdentities(identityManifest)` | Desired in-scope identities and component mapping | Per-component provisioning results | Coordinates KDC and native user creation. |
| Identity/permission provisioner | `applyHiveGrants(grantManifest)` | Database and principal grant intents | Grant operation results | Requests Hive-owned authorization setup for users and service identities. |
| Identity/permission provisioner | `applyStoragePolicies(policyManifest)` | Bucket/path scopes and identity-to-policy mapping | Policy operation results | Requests RustFS-owned credentials/policies without becoming the policy authority. |
| Identity/permission provisioner | `provisionDremioUsers(userManifest)` | Dremio local account names and credential inputs | Account creation results | Creates the required local Dremio identities through supported administration interfaces. |
| Metastore PostgreSQL | `initializeSchema(schemaVersion)` | Selected Hive schema version and admin connection | Initialization status | Initializes/persists Hive Metastore schema. |
| Hive Metastore | `createDatabase(databaseName, owner)` | Database name and effective identity | Database metadata reference | Creates Hive database metadata for the writer's ETL. |
| Hive Metastore | `registerIcebergTable(database, tableDefinition)` | Database and table metadata/location | Table metadata reference | Registers an Iceberg table. |
| Hive Metastore | `resolveTable(database, tableName, effectiveUser)` | Database, table, effective user | Metadata or authorization result | Supports Dremio and Spark catalog lookups under effective identity. |
| RustFS | `ensureBucket(bucketName)` | Bucket name and initializer credentials | Bucket status | Creates the sample data bucket idempotently. |
| RustFS | `writeObject(path, content, identity)` | Object path, data, credential context | Write result | Stores Iceberg data and metadata under a scoped identity. |
| RustFS | `setPolicy(identity, resourceScope, actions)` | Identity, bucket/path scope, allowed actions | Policy result | Applies component-owned access controls. |
| Spark runtime | `openSession(identity, catalogConfig)` | Kerberos keytab/principal and catalog/storage configuration | Spark session | Creates a Spark session with the requested identity context. |
| TPCH generator | `generate(sourceDirectory, scale)` | Output directory and scale | Source files | Produces input files for the ETL. |
| TPCH loader | `loadSampleData(sourceDirectory, databases, identity)` | TPCH data, `databaseA`/`databaseB`, writer credentials | Created table list and load summary | Creates and populates Hive Iceberg tables as `write-service-account`. |
| TPCH loader | `createDremioSpacesAndViews(databaseTables, jdbcIdentity)` | Database-to-table mapping and writer JDBC credentials | Space/view creation summary | Creates matching Spaces and a corresponding view for each Hive table. Subject to Dremio Community capability verification. |
| Dremio | `connectHiveSource(sourceConfig, serviceIdentity)` | Metastore endpoint, SASL/Kerberos settings, service identity | Source status | Connects Dremio to Hive Metastore. |
| Dremio | `mapQueryIdentity(dremioUser, hiveUser)` | Local user and effective Hive user mapping | Mapping result | Makes Hive authorization evaluate the intended query identity. |
| Dremio | `createSpace(spaceName, jdbcIdentity)` | Space name and authenticated JDBC identity | Space reference or capability error | Provides one Space for each target Hive database, if supported by the chosen Community version and writer permissions. |
| Dremio | `createView(spaceName, viewName, sourceTable, jdbcIdentity)` | Space, view name, Hive source table, JDBC identity | View reference or capability error | Exposes each underlying Hive table as a view in the corresponding Space. |
| JupyterHub | `spawnNotebook(username, identityBundle)` | Demo username and scoped Kerberos/RustFS mounts | Single-user notebook session | Starts an isolated Spark-enabled session. |
| SQL workloads | `runAuthorizationScenario(engine, user, query)` | Engine, test user, query | Query result or expected denial | Demonstrates access behavior through Dremio and Jupyter Spark. |
| Lifecycle scripts | `start(platformProfile)` | Local environment/profile | Startup status | Starts infrastructure and ordered initialization. |
| Lifecycle scripts | `clean(cleanupScope)` | Selected volume/data cleanup scope | Cleanup status | Removes local resources according to documented persistence behavior. |

## Interface Notes

- Exact client libraries, CLI commands, network ports, readiness checks, credential files, and error contracts are infrastructure/functional design decisions.
- Dremio JDBC setup must use a supported interface for the selected version. If a Space or view operation requires administrator rights unavailable to the writer, record the observed limitation and return for a scope decision; do not silently substitute `admin`.
- Permission manifests describe requested changes only. Each destination component validates and applies its own authorization model.
- No Airflow or Jenkins method is defined in this intent.
