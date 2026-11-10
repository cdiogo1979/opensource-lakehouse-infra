# Unit 4 Infrastructure Design — Dremio Source and Query Identity

## Deployment target

Use the existing single-host Docker Compose deployment and network `iceberg-poc-net` (`iceberg_net` in Compose). Unit 4 is an operator-invoked query validation flow over already running services. Do not add a cloud target, query-runner container, queue, API gateway, monitoring stack, log service, volume, or published port.

## Logical-to-concrete mapping

| Responsibility | Existing infrastructure mapping |
|---|---|
| Query user interaction | Operator uses the Dremio 26.0.5 Community UI and/or existing JDBC/SQL client against Dremio's loopback-bound UI/JDBC ports. Authenticate separately as `user_a` and `user_b`. |
| Local Dremio credentials | Keep one Dremio password per test user under ignored, permission-restricted `.runtime/credentials/` files. The infrastructure design does not create accounts or passwords; account provisioning is a later approved implementation action. Do not add these credentials to Compose services, environment files, command-line arguments, images, or source control. |
| Dremio-to-Hive connection | Existing `dremio` Compose service connects to `hive-metastore:9083` over `iceberg_net`, using the dedicated Dremio Kerberos service keytab mounted read-only and the manually configured Hive source. Keep its existing Hive proxy-user allowlist and RustFS S3A source settings. |
| Hive catalog metadata | Existing `hive-metastore` service connects to `metastore-db` PostgreSQL and the KDC. Preserve the existing metadata volume and generated Hive configuration. Storage-based authorization enablement and enforcement remain an implementation/verification gate. |
| Iceberg data | Existing Hive source reads the RustFS-backed warehouse through `object-store:9000` using the source's existing writer credential. Preserve `object-store-data` and do not rotate or replace the writer key in Unit 4. This shared identity is not per-user RustFS authorization. |
| Kerberos | Existing `kdc` service and runtime keytabs provide service identity support. Dremio local UI/JDBC passwords remain separate from Kerberos principals/keytabs. |
| Evidence | Operator stores minimal redacted scenario results in local workflow/runtime evidence. Use existing Dremio/Hive container logs as needed; no log-forwarding or centralized retention service is added. |

## Network and exposure

- Reuse the existing private Compose network `iceberg-poc-net` for Dremio, Hive, KDC, PostgreSQL, RustFS, and Spark dependencies.
- Reuse existing loopback-only host ports. Unit 4 publishes no new host port and introduces no external endpoint.
- Query traffic to Dremio uses the already configured UI/JDBC endpoint; Dremio's Hive and RustFS traffic remains on the internal Compose network.

## Storage and lifecycle

- Preserve the existing named volumes `dremio-data`, `metastore-db-data`, `object-store-data`, and `kerberos-kdc-data`.
- Do not recreate/reset volumes, delete or rewrite the sample databases/views, or rerun ETL as part of authorization verification.
- Keep generated Dremio passwords in restricted runtime files only; never store them in the query evidence.
- Keep authorization result files local and secret-free. There is no formal retention period.

## Availability, scaling, and observability

- Use manual operator invocation and recovery; there is no HA, failover, restart policy change, or uptime objective in Unit 4.
- Execute the two-user/four-outcome query matrix serially. No scaling, concurrency, caching, or benchmark infrastructure is required.
- Use existing container logs and concise redacted query outcomes. Do not add metrics, alerts, centralized logging, or a new audit store.

## Feasibility gate

The current Compose services are healthy and the user confirmed Dremio can query sample data, but per-user allow/deny behavior is not established. The checked-in Hive Metastore template lacks storage-based authorization listener/provider configuration. Do not claim the matrix passes until Unit 4 verifies Dremio user mapping, effective Hive identity, and the authorization decision. If the pinned Hive/RustFS path cannot enforce the matrix, preserve the stack and state and return the smallest proposed adjustment for review.
