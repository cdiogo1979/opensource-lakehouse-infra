# Application Design — Hive, Dremio, RustFS, and Kerberos PoC

## Purpose and Scope

This design replaces Nessie with a standalone Hive 3.x Metastore backed by PostgreSQL, adds a disposable Kerberos KDC and a one-shot identity/permission provisioner, and defines the cross-engine sample data and authorization paths. Iceberg data remains in RustFS. It is an active-intent review artifact; durable project knowledge will be curated at approved intent closure.

In scope are component responsibilities and high-level interfaces, identity setup boundaries, startup/ETL/query orchestration, and dependencies. Detailed authorization implementation, exact version compatibility, service configuration, and operational commands remain for later design stages.

## Architecture Summary

- Hive Metastore is the catalog for Spark-created Iceberg tables; HiveServer2 is not in the baseline.
- PostgreSQL persists Hive metadata; RustFS stores Iceberg data.
- A disposable local KDC issues distinct principals/keytabs for `user_a`, `user_b`, `admin`, `write-service-account`, and required service identities.
- A one-shot identity/permission provisioner coordinates KDC, Hive, RustFS, and Dremio setup through their own administrative interfaces. It is not a runtime policy or authorization authority.
- `tpch-loader` runs sample ETL as `write-service-account`, creates/populates `databaseA` and `databaseB`, then connects to Dremio over JDBC to create corresponding Spaces and one view per Hive table.
- Dremio authenticates to Hive with a Kerberos service identity and maps local query users to Hive effective users. JupyterHub provides isolated Spark sessions with user-specific Kerberos and RustFS credentials.
- Airflow/Jenkins integration and direct RustFS authorization demonstrations are deferred/out of scope.

## Main Interactions

1. **Bootstrap:** Compose starts PostgreSQL, KDC, RustFS, and their initializers. KDC creates runtime principals/keytabs. The provisioner creates component-native users/permissions. Hive Metastore starts after schema and service identity readiness.
2. **ETL:** `tpch-loader` runs Spark as `write-service-account`, writes Hive catalog metadata and RustFS table data, and records created tables.
3. **Dremio mirror:** The same service account uses JDBC to create Spaces named `databaseA` and `databaseB` and views corresponding to every table. This operation is subject to the Dremio Community feasibility check.
4. **Dremio query:** Dremio authenticates to Hive using SASL/Kerberos, maps the local account to its Hive effective user, and accesses data from RustFS using the selected integration.
5. **Jupyter query:** JupyterHub starts isolated user containers; each Spark session uses its own Kerberos keytab and RustFS credentials. The required access outcomes are `user_a`: databaseA only; `user_b`: both databases.

## Component and Interface Details

See [components.md](components.md) for component responsibilities and identity boundaries, and [component-methods.md](component-methods.md) for the high-level operation contracts.

## Orchestration Details

See [services.md](services.md) for bootstrap, ETL, Dremio, Jupyter, and cleanup flows. Startup sequencing is owned by Compose/lifecycle scripts. Component-native authorization remains owned by each service.

## Dependencies and Communication

See [component-dependency.md](component-dependency.md) for the dependency matrix, communication mechanisms, and data/identity flow. Service-to-service dependencies are local Compose network interactions; user credentials and component administrator credentials remain separate.

## Feasibility Gates and Open Design Constraints

1. **Dremio Community permissions:** Verify that `write-service-account` can create the two Spaces and their views over JDBC without administrator privileges. Do not use admin privileges to mask unavailable Community capabilities. If unsupported, return the smallest alternative for review.
2. **Hive authorization path:** Verify that the selected standalone Metastore authorization mechanism can produce the required database allow/deny behavior for both Dremio and Spark against RustFS-backed tables. HiveServer2 is excluded unless this path proves infeasible; any architecture change requires review.
3. **Version compatibility:** Select a compatible Hive 3.x, Spark/Iceberg, and Dremio version combination and verify metastore schema and catalog behavior.
4. **Dremio storage access:** Confirm how the selected Hive source reads RustFS objects and whether user identity is preserved at the authorization boundary.
5. **Local authentication:** DummyAuthenticator is only a development test-label mechanism and does not verify user identity.

## Security and Identity Boundaries

- `admin` maps to component-specific administrative roles/accounts; native credentials are distinct where Kerberos is not used.
- `write-service-account` is a non-admin workload identity with scoped Hive and RustFS write rights and a Dremio local account for JDBC.
- `user_a` and `user_b` remain separate identities with individual keytabs and storage credentials.
- Dremio's Kerberos service principal authenticates the source connection; the mapped user's effective identity must be used for authorization.
- Generated secrets/keytabs are local runtime artifacts and must not be committed, logged, or baked into images.

## Deferred Decisions

Functional Design will define the concrete Hive authorization mechanism, order of database and grant creation, exact identity mappings, error behavior, and ETL idempotency. Infrastructure Design will define images, versions, ports, health/readiness, volumes, networks, mounts, and secret generation. Build and Test remains instruction preparation only under the approved execution plan; no tests are added or run by this design stage.
