# NFR Design Patterns — Unit 2 StarRocks Runtime

## Resilience and Recovery

- **Process restart:** Configure FE and BE containers to restart after process exit unless an operator explicitly stopped them. The selected restart policy is a best-effort local mechanism, not an availability guarantee or RTO.
- **Health failure:** Health checks report a failed node and cause the overall runtime to be reported not ready. A process that remains alive but unhealthy is not restarted solely because its health check fails; the operator investigates and recovers it.
- **State safety:** A single startup preflight validates both FE and BE persistent directories before either node starts. Both empty directories are eligible for paired first initialization. One empty side with an initialized peer, or invalid/incompatible state, blocks startup without deleting or rewriting state.
- **Recovery boundary:** Restart and recreate operations retain both named volumes. No HA, failover, automatic volume repair, or retry controller is introduced.

## Scalability

- Keep exactly one FE and one BE. No horizontal scaling or autoscaling is included.
- Keep resource values fixed in Compose. If the measured workload exceeds the documented baseline, an operator changes Compose resource configuration and recreates the StarRocks services deliberately.
- Do not apply fixed CPU/memory limits until the local measured baseline and pinned release are known; document the measured minimum/recommended values and their host/workload conditions.

## Performance

- Begin with the selected compatible StarRocks release defaults. Do not add cache or memory tuning without compatibility evidence or an observed operational need.
- Measure and document FE/BE startup duration and local resource use during integrated verification. These measurements are observations, not service-level guarantees.
- Keep readiness based on the FE/BE health and FE SQL service. Catalog/HMS and RustFS query health is established separately by Unit 3/integrated verification.

## Security and Kerberos Ticket Lifecycle

- Mount the Unit 1 keytab read-only into both FE and BE containers; configure the Java Kerberos configuration path in each node as documented by StarRocks.
- Run periodic `kinit -kt` tasks inside each FE and BE container. Each node refreshes its own TGT so all relevant StarRocks processes have the Kerberos credentials required for HMS access. This follows the [official StarRocks Hive Catalog guidance](https://docs.starrocks.io/docs/data_source/catalog/hive_catalog/).
- Store each TGT cache on a per-container memory-backed temporary filesystem with restrictive directory/file permissions. Do not store ticket caches in FE/BE data volumes or tracked files.
- The refresh task reports a safe success/failure category to container logs. It never logs keytab contents, ticket contents, or secret-bearing command output.
- A refresh failure while the current TGT is valid sets a credential-degraded diagnostic while FE/BE remains available. If the TGT expires, secured HMS operations may fail; runtime health must not imply catalog health.
- Refresh cadence and cache path are selected against the pinned StarRocks version, configured ticket lifetime, and runtime process behavior during Infrastructure Design and compatibility validation.

## Logical Component Patterns

- **Paired-state preflight/init coordinator:** A one-shot Compose component that examines FE and BE data locations as a pair and gates their startup. It initializes only a clean paired first start and fails safely for one-sided or invalid state.
- **FE and BE runtime containers:** The single StarRocks FE and BE retain independent persistent volumes and readiness checks. Each receives read-only service credentials and its own ephemeral TGT cache.
- **Per-node ticket refresh task:** A scheduled task inside each FE/BE container obtains and refreshes that node's TGT using its mounted keytab. No separate helper service is added.
- **Operator diagnostics:** Container stdout/stderr, retrieved through Docker Compose logs. No persistent log collector, metrics service, alerting, or dashboard is introduced.

## Extension Applicability

- **Security Baseline:** Disabled. Explicit project requirements for loopback-only exposure, keytab/secret protection, identity separation, and redaction remain mandatory.
- **Property-Based Testing:** Partial. No property-based design pattern is required by these architecture artifacts; qualifying functions, if any, are addressed during implementation planning.
- **Resiliency Baseline:** Disabled. The explicitly approved best-effort restart and state-preservation behavior is retained; no HA or production resilience is implied.

## Compatibility Notes

- The cited StarRocks documentation requires periodic `kinit -kt` on each FE and BE and Kerberos JVM configuration on each node. Exact commands, scheduler availability, image changes, and configuration locations must be checked against the selected pinned release.
- The StarRocks image/version and digest are not selected in this design. They remain subject to compatibility review against Hive Metastore 3.1.3, the secured KDC, Iceberg, and RustFS.
