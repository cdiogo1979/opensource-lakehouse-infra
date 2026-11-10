# Deployment Architecture — Retained Local Stack

## Retained Services

The project remains a local Docker Compose lakehouse PoC:

- **Identity:** MIT Kerberos KDC and retained Hive/workload/user principals.
- **Catalog metadata:** Hive Metastore 3.x backed by PostgreSQL.
- **Object storage:** RustFS with the existing bucket and credentials.
- **Compute:** Spark, TPCH generator/loader, and JupyterHub-managed Spark notebooks.
- **Network:** Existing internal Compose network; retained host endpoints stay as configured.

Dremio and its JDBC helper are removed. No new service or external dependency is introduced.

## Runtime State Lifecycle

| State | Action | Safety condition |
|---|---|---|
| Dremio container | Remove | Match the Dremio service/container only. |
| Dremio Compose volume | Remove | Verify Compose project and volume labels, unique match, and no retained container attachment. |
| Dremio Kerberos principal | Remove | Delete only `dremio@<realm>` from the existing KDC. |
| Dremio passwords/keytab | Remove | Delete exact Dremio-named files only. |
| Hive/PostgreSQL/RustFS/KDC/Jupyter volumes | Retain | Never use broad Compose volume deletion. |
| Other principals, shared credentials, TPCH data/results, notebook workspaces | Retain | No wildcard cleanup or reset operation. |

## Order of Operations

1. Apply and statically validate source/configuration changes.
2. Identify the active Compose project, Dremio container, and Dremio volume from labels and references.
3. Remove the Dremio container and only its uniquely verified volume.
4. Remove the Dremio principal from the still-running KDC and remove Dremio-only local credential files.
5. Restart or recreate retained services only if their configuration changed; preserve their named volumes.
6. Verify retained services and persisted data, then document outcomes and any checks not performed.

No destructive runtime operation is performed as part of this design stage.
