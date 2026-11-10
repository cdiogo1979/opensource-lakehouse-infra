# Unit 3 Spark Runtime and Sample ETL — Deployment Architecture

## Compose Topology

```text
Operator
  |
  +--> workload-profile runner
         |
         +--> tpch-generator (one-shot; no credentials)
         |      writes .runtime/workload/tpch-data
         |
         +--> tpch-loader (one-shot ETL; derived pinned Spark image)
                |-- writer keytab (read-only) --> KDC ticket cache on tmpfs
                |-- writer RustFS key ----------> RustFS object-store:9000
                |-- Hive catalog client --------> Hive Metastore:9083
                +-- redacted manifest ----------> .runtime/workload/results
         |
         +--> tpch-jdbc (one-shot; same image)
                |-- Dremio writer password -----> Dremio:31010
                +-- updates manifest -----------> .runtime/workload/results
```

The existing long-running Spark service remains a separate notebook/master service and receives no writer keytab or writer RustFS secret. `tpch-generator`, `tpch-loader`, and `tpch-jdbc` are profile-gated and do not run during normal Compose startup. Separate one-shot containers enforce the ETL/JDBC credential boundary.

## Dependency and Result Flow

| Stage | Required condition | Result behavior |
|---|---|---|
| Generate | Generator image available; writable runtime input mount | Produce expected eight `.tbl` inputs at scale 1; no platform credentials. |
| Preflight ETL | KDC/Hive/RustFS/bucket ready; writer keytab and RustFS secret files readable; complete input manifest | Fail before table mutation if unmet; bounded retries only for transient readiness. |
| ETL | Spark task process has writer Kerberos ticket and named RustFS key | Create/validate both Hive databases and eight tables each; record schemas/counts. Conflict stops relevant writes without overwrite. |
| JDBC exposure | ETL validation passed; Dremio reachable; writer JDBC password readable in `tpch-jdbc` | Create/validate matching Spaces and views through JDBC. Denial produces JDBC failure and overall partial state; successful data is retained. |
| Finalize | All attempted stages return | Write secret-free manifest, clean cache tmpfs, and return complete/partial/failed status. |

## Mount and Secret Matrix

| Path/artifact | Container | Access | Lifetime |
|---|---|---|---|
| TPCH loader scripts | `tpch-loader` | Read-only | Source-controlled |
| Generated TPCH input directory | generator read-write; loader read-only | Write/read | Runtime input, regenerable |
| Writer keytab | `tpch-loader` | Read-only | Protected local credential |
| Writer RustFS access/secret key files | `tpch-loader` | Read-only secret files | Protected local credential |
| Dremio writer password | `tpch-jdbc` only | Read-only secret file | Protected local credential |
| Kerberos ticket cache | `tpch-loader` tmpfs | Restricted read/write | One invocation; destroyed before JDBC starts |
| Run manifest directory | Both one-shot services | Read/write | `.runtime/workload/results`; no secrets |
| RustFS bucket volume | Object-store service only | Existing service ownership | Persistent Iceberg data |

## Network Exposure

All workload traffic remains on the existing Compose network. The loader reaches KDC/Hive/RustFS/Dremio by service DNS name. No new host-published port is required. Existing Dremio JDBC host binding remains loopback-only for operator clients.

## Deployment Constraints

- The workload is explicitly invoked and sequential; it is not attached to default `docker compose up`.
- The JDBC phase must not be a hard startup dependency for ETL, so Dremio unavailability can be reported separately after successful data loading.
- Runtime input/output paths are distinct from persistent RustFS data and credential storage.
- Existing Spark notebook/master lifecycle is not changed to supply the ETL writer identity.
- Compose profile/container names, exact service commands, tmpfs syntax, and build artifact wiring are finalized during Code Generation and validated in Build and Test.
