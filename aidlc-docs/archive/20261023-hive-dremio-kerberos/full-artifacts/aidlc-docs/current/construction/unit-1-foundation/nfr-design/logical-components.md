# Unit 1 NFR Design — Logical Components

## Component View

This view describes logical responsibilities and readiness relationships. Concrete Compose services, image selection, ports, healthcheck commands, dependency syntax, and mounts are deferred to Infrastructure Design.

| Logical component | Responsibility | Readiness/operation contract |
|---|---|---|
| Compose lifecycle and operator interface | Starts and stops the local foundation, reports status, and exposes the explicit reset action. | Does not report full readiness until required initializers and services succeed; stop preserves volumes; reset is explicit and destructive. |
| Kerberos KDC and realm initializer | Provides the disposable realm and creates required service/user principals and keytabs. | Realm initialization is a successful one-shot prerequisite; keytabs remain local runtime artifacts and are consumed read-only. |
| Metastore PostgreSQL and schema initializer | Persists Hive catalog metadata and prepares the Hive schema. | Database readiness precedes idempotent schema initialization; schema failure blocks Hive Metastore and downstream work. |
| RustFS object service | Stores warehouse and table objects and enforces its native storage credentials/policies. | API readiness precedes bucket setup or storage clients. Its health does not prove Hive/Dremio/Spark authorization behavior. |
| Bucket initializer | Ensures the required bucket exists. | Runs after RustFS readiness; ensure-only behavior preserves existing objects; failure blocks storage-dependent downstream work. |
| Hive Metastore | Serves Hive catalog metadata to Spark and Dremio. | Ready only after PostgreSQL schema and required KDC/storage prerequisites; authorization behavior remains a separate feasibility check. |
| Unit 2 identity/permission provisioner | Coordinates component-owned identities and grants for admin, writer, and query users. | Runs after required services are ready; reports component-specific outcomes; failure blocks the dependent ETL/authorization flow. It is not itself an authorization decision point. |
| Unit 3 Spark ETL and sample-data initializer | Creates `databaseA`, `databaseB`, and sample Iceberg tables as `write-service-account`. | Runs only after required catalog, storage, and writer-authorization prerequisites succeed; safe rerun preserves existing data and does not implicitly drop tables. |
| Query and authorization acceptance clients | Exercise the approved Dremio and Spark paths with the intended effective identities. | Run only after setup succeeds; record effective identity and allow/deny result. An unverified or shared-credential path cannot be reported as per-user authorization proof. |

## Readiness Dependency Graph

```text
Kerberos KDC -> realm/principal initialization --+
                                                  +-> Hive Metastore PostgreSQL schema --+
Metastore PostgreSQL service --------------------+                                     |
Kerberos service principal/keytab -----------------------------------------------------+--> Hive Metastore
RustFS service -> bucket ensure ------------------------------------------------------------> storage-ready

Hive Metastore ready + storage-ready
    -> Unit 2 identity and permission provisioning
    -> Unit 3 ETL as write-service-account
    -> Dremio/Spark query and authorization acceptance clients
```

The graph is logical. Infrastructure Design may refine ordering where independent prerequisites can start concurrently, but consumers must remain gated on successful completion of required one-shot initialization and readiness checks.

## Failure Boundaries

- A failed KDC, schema, bucket, or required permission initializer blocks dependent work and keeps overall readiness false.
- Independent services may remain running for operator diagnosis; their presence does not make the foundation ready.
- Failures preserve catalog and object-store volumes. Do not automatically delete state, recreate a bucket destructively, or reset the environment.
- Authorization acceptance remains blocked if the actual effective-user path cannot be established or the selected storage/metastore mechanism cannot enforce the intended outcome.

## Cross-Cutting Constraints

- Host-published developer interfaces bind to loopback; internal component communication stays on the local Compose network.
- Credential delivery is file based from ignored, restricted local runtime storage, with only required files mounted read-only where supported.
- No monitoring, alerting, HA, scaling, cache, queue, reverse proxy, or custom operator UI component is introduced.
- Initialization and status output is actionable and secret safe.
