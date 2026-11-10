# Unit 1 Infrastructure Design Plan — Dremio Removal

## Design Steps

- [x] Map retained logical components to the existing local Docker Compose services.
- [x] Identify Dremio-only Compose services, ports, secrets, volumes, environment variables, and mounts.
- [x] Map Dremio-only Kerberos and Hive proxy configuration that must be removed.
- [x] Define a fail-closed cleanup order for Dremio runtime state.
- [x] Define preservation checks for retained Compose volumes, principals, credentials, and data.
- [x] Evaluate deployment environment, compute, storage, messaging, networking, monitoring, and shared infrastructure categories.
- [x] Check for infrastructure-design clarifications; none remain because the user approved local Compose and the exact retained/deletion boundaries in Requirements Analysis.

## Scope and Question Category Assessment

| Category | Applicability and decision |
|---|---|
| Deployment environment | Applicable. Remains the existing single-host local Docker Compose setup; no cloud target is in scope. |
| Compute infrastructure | Applicable. Remove only the Dremio and `tpch-jdbc` containers/images; keep Hive, PostgreSQL, KDC, RustFS, Spark, JupyterHub, and TPCH Spark ETL. |
| Storage infrastructure | Applicable. Remove only the Dremio named volume. Preserve PostgreSQL metastore, KDC, RustFS, JupyterHub/user volumes, and bind-mounted TPCH/workspace data. |
| Messaging infrastructure | Not applicable. The retained stack has no messaging/queue service or event-driven path affected by Dremio removal. |
| Networking infrastructure | Applicable. Remove Dremio ports and Dremio-only container connectivity. Keep the shared Compose network and retained service endpoints. |
| Monitoring infrastructure | Not applicable. No monitoring or alerting infrastructure is present in the active Compose definition or changed by this scope. |
| Shared infrastructure | Applicable. Preserve shared Hive, PostgreSQL, KDC, RustFS, Spark, JupyterHub and existing named volumes; remove Dremio-only proxy configuration. |

No infrastructure preferences remain unresolved, so no clarification question is needed.

## Artifacts

- `construction/unit-1/infrastructure-design/infrastructure-design.md`
- `construction/unit-1/infrastructure-design/deployment-architecture.md`
