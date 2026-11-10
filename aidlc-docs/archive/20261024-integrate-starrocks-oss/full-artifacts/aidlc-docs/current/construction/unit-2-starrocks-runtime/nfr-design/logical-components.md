# Logical Components — Unit 2 StarRocks Runtime

## Component Inventory

| Component | Responsibility | State and inputs | Failure behavior |
|---|---|---|---|
| Startup Preflight/Init Coordinator | Validate FE and BE persistent state together; gate FE/BE startup; allow paired first initialization only when both locations are empty | Read/write access to the FE and BE data locations during validation/initialization; no access to unrelated platform volumes | Return failure and prevent node startup on one-sided empty, invalid, or incompatible state; preserve available data |
| StarRocks FE | Provide SQL frontend and UI; access HMS and coordinate query execution | Persistent FE volume; read-only keytab and Kerberos config; per-container TGT cache; RustFS service secret if required by the selected catalog/runtime; internal network | Health/readiness failure is surfaced; process exit is handled by configured Compose restart policy; volume remains intact |
| StarRocks BE | Execute query work and access data storage as required by the configured catalog | Persistent BE volume; read-only keytab and Kerberos config; per-container TGT cache; RustFS service secret if required by the selected catalog/runtime; internal network | Health/readiness failure makes the overall runtime not ready; process exit is handled by configured Compose restart policy; volume remains intact |
| FE Ticket Refresh Task | Periodically obtain/refresh the FE TGT with `kinit -kt` | Read-only FE keytab; FE-private memory-backed ticket cache; KDC network access | Log a redacted failure category; maintain degraded state while a prior ticket remains valid; retry on schedule |
| BE Ticket Refresh Task | Periodically obtain/refresh the BE TGT with `kinit -kt` | Read-only BE keytab; BE-private memory-backed ticket cache; KDC network access | Log a redacted failure category; maintain degraded state while a prior ticket remains valid; retry on schedule |
| FE/BE Readiness Checks | Determine node readiness and FE SQL service availability | FE/BE health endpoints or supported process checks | Report overall runtime not ready if either required node is unhealthy; do not assert external catalog readiness |
| Operator Interface | Start/stop/recreate services and inspect diagnostics | Docker Compose commands, service status, and container logs | Operator handles persistent health failures; routine commands preserve named volumes |

## Startup Sequence

1. Compose creates or attaches the existing FE/BE named volumes and supplies read-only credential/configuration mounts plus private temporary cache filesystems.
2. Startup Preflight/Init Coordinator validates both persistent data locations as a pair.
3. If both locations are empty on first start, the coordinator permits paired initialization. If only one is empty or either is invalid/incompatible, it fails without modifying the peer's data.
4. FE and BE start with the selected release's required Kerberos configuration.
5. Each node's ticket refresh task obtains a TGT using its keytab and periodically refreshes it.
6. FE/BE readiness checks report the runtime ready only when both nodes and the FE SQL service are healthy.
7. Unit 3 configures the Hive Iceberg catalog and SQL users/grants after the runtime is ready.

## Credential and Network Boundaries

- The FE and BE each receive the keytab read-only and maintain a separate in-memory TGT cache. Neither ticket cache is stored in the node's persistent data volume.
- RustFS secret is mounted read-only into the FE and/or BE components that the pinned release and catalog configuration require; it is never logged.
- FE/BE, KDC, HMS, and RustFS communication uses Compose-internal service networking. Host SQL/UI bindings remain loopback-only.
- SQL clients authenticate as StarRocks SQL users in Unit 3. Their identities are not converted into Kerberos service tickets.

## Operational Boundaries

- No sidecar ticket-renewal service, persistent monitor, log collector, cache tier, queue, or HA coordinator is introduced.
- Compose restart policy handles process exit only. A health check failure for a still-running process is reported for operator action.
- The preflight coordinator may inspect and initialize only StarRocks FE/BE state. It must not modify Hive metadata, RustFS data, Spark/Jupyter state, credentials, or unrelated Compose volumes.
- Detailed process supervision, health-check commands, startup dependency syntax, and refresh interval are deferred to Infrastructure Design and pinned-version compatibility validation.
