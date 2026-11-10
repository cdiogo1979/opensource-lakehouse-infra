# U1 NFR Design Patterns — Runtime Composition and Legacy Removal

## Design scope

This design applies to the supported local Compose runtime for Keycloak, Polaris, its dedicated PostgreSQL metadata store, and RustFS. It applies approved U1 NFRs without choosing exact Compose syntax, service names, ports, volume names, images, or health-check commands; those are resolved in Infrastructure Design.

## Startup and readiness pattern

- Start independent core providers concurrently. Respect provider prerequisites such as Polaris metadata persistence before Polaris readiness.
- A single bounded readiness coordinator observes each provider separately and returns a terminal result within the configurable 10-minute overall window.
- Report provider state and dependency impact as `starting`, `ready`, `unavailable`, or `stopped`. If the bound expires, report exactly which required providers remain unavailable and do not start dependent work.
- Health checks are observations of liveness/readiness, not commands to restart a live unhealthy process. No extra watchdog is introduced.
- The host CLI and one-shot Spark smoke job are on-demand clients, not default long-running providers. They run only after required dependencies are ready.

## Resilience and failure-isolation pattern

- Apply a bounded retry policy to container process exits, with a default maximum of three restart attempts.
- Do not restart healthy dependencies when one provider fails. Do not cascade a provider failure into automatic stack teardown.
- When a process remains alive but fails its health check, mark it unavailable, prevent dependent work, and report the provider for operator action.
- When the retry budget is exhausted or readiness times out, return an actionable failure. Preserve all named state stores and RustFS objects.
- No queue, cache, circuit-breaker service, or cluster failover mechanism is required for the single-host, single-workload target.

## Secret-handling pattern

- Keep local secret source files outside version control in a gitignored runtime-secret directory with owner-only host permissions.
- Deliver secrets as file-backed, read-only mounts. Prefer Compose secrets where a service can read the resulting file path; use a read-only file mount for compatibility when it cannot.
- Configure applications to consume secret file paths where supported. Do not put secret values in Compose interpolation, ordinary environment variables, command-line arguments, logs, or diagnostics.
- Secret generation and exact names are specified in Infrastructure Design; the handling rule applies to all core service credentials.

## Network-exposure pattern

- Use one private core network for provider-to-provider API traffic.
- Publish only operator-required endpoints to host loopback. Do not publish internal service APIs to non-loopback interfaces.
- Plain HTTP is permitted only over loopback or the private local network. External exposure and cross-host operation are out of scope.
- Keep browser-facing and service-to-service identity/catalog flows addressable consistently; U2 and Infrastructure Design define their concrete issuer URLs and port mappings.

## Persistence and recovery pattern

- Give Keycloak identity state, Polaris metadata, and RustFS object state separate persistent ownership boundaries. Keycloak’s supported production-mode database must be logically isolated from Polaris metadata; physical database topology is deferred to Infrastructure Design.
- Preserve all persistent state across ordinary restart/recovery. Do not bind new services to old FreeIPA, Hive, or KDC state.
- Document offline backup and restore commands for each named persistent store. Stop the relevant service before copying state to ensure consistency. Include RustFS object data in the preservation/backup guidance.
- Scheduled backup infrastructure, replication, and a backup/restore service are out of scope.

## Legacy-volume cleanup pattern

Legacy cleanup is a separate operator-invoked transition workflow:

1. Inventory candidate volumes in dry-run mode and display exact names and ownership evidence.
2. Require a second explicit invocation naming the exact reviewed volumes.
3. Reject RustFS volumes, unrelated volumes, and candidates whose ownership is ambiguous.
4. Remove only confirmed FreeIPA, Hive/metastore, or MIT KDC volumes named in the invocation.
5. Report removed and rejected resources without exposing credentials.

The cleanup workflow is not linked from normal Compose startup, service recovery, or product bootstrap. It does not remove RustFS objects or unrelated service state.

## Resource and capacity pattern

- Document the single-operator, one-bootstrap/smoke-workload-at-a-time boundary.
- Do not set fixed CPU/memory limits for the default local setup because host capacity varies. Operators may add resource limits for their local machine.
- There is no horizontal scaling, concurrent-run guarantee, throughput target, latency target, uptime target, or multi-host recovery objective.

## Mapping to U1 NFRs

| Requirement | Design response |
|---|---|
| U1-NFR-01 | Single operator and one workload at a time; no scaling claim. |
| U1-NFR-02 | Concurrent independent startup with one configurable 10-minute readiness coordinator. |
| U1-NFR-03 | Up to three process-exit restarts; health checks observe only; preserve healthy providers and state. |
| U1-NFR-04 | Persistent service-owned state and documented offline backup/restore. |
| U1-NFR-05 | One private provider network; operator endpoints loopback-only; HTTP limited to local boundary. |
| U1-NFR-06 | Per-provider readiness, dependency impact, actionable redacted errors. |
| U1-NFR-07 | Separate logical ownership for Keycloak, Polaris metadata, and RustFS state; no legacy-state import. |
| U1-NFR-08 | Explicit dry-run and exact-name cleanup, with RustFS/unrelated resources rejected. |
| U1-NFR-09 | Version pinning and compatibility matrix are specified in Infrastructure Design. |
| U1-NFR-10 | No active default dependency on FreeIPA, Hive Metastore, MIT Kerberos, or KDC. |
