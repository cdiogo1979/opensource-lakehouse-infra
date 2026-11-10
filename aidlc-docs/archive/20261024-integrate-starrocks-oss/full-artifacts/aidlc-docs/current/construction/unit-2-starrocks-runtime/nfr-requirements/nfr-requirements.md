# NFR Requirements — Unit 2 StarRocks Runtime

## Scope

These requirements apply to the local Docker Compose StarRocks OSS runtime: one FE and one BE, their persistent state, the Unit 1 service credential inputs, runtime readiness, and operator diagnostics. The approved requirements do not establish production availability, throughput, or query-latency objectives. Hive catalog setup, SQL users/roles/grants, and catalog query/write validation remain in Unit 3 and integrated Build and Test.

## Availability and Recovery

- **NFR-2.1 — Best-effort local availability:** No uptime or recovery-time objective applies to this PoC. The overall runtime reports ready only when FE and BE are healthy and the FE SQL service is available.
- **NFR-2.2 — Process recovery:** Permit the configured Compose process recovery behavior. If a node remains unhealthy, report the runtime as not ready and require operator action. Do not add a new recovery service or orchestration framework.
- **NFR-2.3 — State preservation:** Normal start, stop, process recovery, and container recreation preserve both FE/BE named volumes and all existing project services and data. Invalid, incompatible, or one-sided empty node state fails safely without automatic deletion or reinitialization.
- **NFR-2.4 — Paired first initialization:** First initialization is permitted only when both FE and BE persistent locations are empty. Startup and health behavior must distinguish that case from one-sided state loss; the implementation mechanism is resolved during NFR/Infrastructure Design.

## Scale and Performance

- **NFR-3.1 — PoC workload:** Support the existing sample databases and occasional interactive SQL use. No concurrency, throughput, or query-latency SLA is required.
- **NFR-3.2 — Startup measurement:** No hard startup-time target applies. Record observed startup duration for the verified local setup and report ready only after FE/BE readiness conditions pass.
- **NFR-3.3 — Resource guidance:** Do not impose a fixed host CPU or memory budget. Document measured minimum and recommended CPU, memory, and storage for the pinned and verified StarRocks/HMS/Iceberg/RustFS combination. State the measurement conditions and distinguish observed values from guarantees.

## Security and Credential Handling

- **NFR-4.1 — Local endpoint exposure:** Publish SQL and FE UI host endpoints on loopback only. Do not add public or LAN bindings.
- **NFR-4.2 — Protected credential inputs:** Consume the Unit 1 StarRocks keytab and RustFS secret as read-only inputs. Keep them outside tracked configuration and do not rotate or modify them in this unit.
- **NFR-4.3 — Redaction:** Never write secret values, keytab contents, ticket contents, or signed authentication material to tracked files, logs, or operator diagnostics.
- **NFR-4.4 — Service identity boundary:** Use the dedicated StarRocks service identity for HMS and object-store access. Do not propagate SQL-client users' Kerberos identities.
- **NFR-4.5 — Ticket refresh:** Retry TGT refresh while the current ticket remains valid, report credential degradation after a failed refresh, and keep the FE/BE runtime available during that valid-ticket interval. If the ticket expires, do not claim secured catalog operations are healthy. Select refresh timing against the configured ticket lifetime and supported runtime mechanisms during later design.

## Compatibility and Technology

- **NFR-5.1 — Supported pinned runtime:** Use a reviewed stable StarRocks OSS release pinned by version and image digest; do not use a floating `latest` tag.
- **NFR-5.2 — Compatibility gate:** Verify the selected release against the existing Hive Metastore 3.1.3, secured Kerberos setup, Iceberg tables/features, and RustFS S3-compatible endpoint before integration is considered complete.
- **NFR-5.3 — Existing platform preservation:** Keep the Compose network and existing services. Do not reset Hive metadata, RustFS objects, Spark/Jupyter state, credentials, or unrelated named volumes.

## Reliability, Diagnostics, and Maintainability

- **NFR-6.1 — Container diagnostics:** Emit actionable, secret-free service diagnostics to container stdout/stderr and make them accessible through Docker Compose logs.
- **NFR-6.2 — No persistent log service:** Do not add a persistent log store, monitoring service, metrics stack, or alerting service for this local PoC.
- **NFR-6.3 — Operator documentation:** Document startup order, endpoints, readiness, observed startup duration, measured minimum/recommended resources, persistent state, ticket-refresh behavior, and safe stop/recreate/recovery operations.
- **NFR-6.4 — Explicit reset boundary:** Routine operations must never delete node volumes. Any future reset procedure must be explicit, StarRocks-only, clearly identify data loss, and preserve shared lakehouse services and data.

## Verification Criteria for Integrated Build and Test

1. The pinned FE/BE services start with loopback-only host bindings and report readiness only after the approved FE/BE conditions pass.
2. Record observed startup duration and measured local minimum/recommended resource use with host and workload conditions; no SLA is inferred from one measurement.
3. Container recreation and configured process recovery preserve both StarRocks volumes and existing shared platform state.
4. A one-sided empty or invalid/incompatible FE/BE state does not trigger silent reinitialization or deletion of the peer's data.
5. Credential files are mounted read-only; inspect tracked files and runtime diagnostics to confirm no keytab, ticket, or RustFS secret values are exposed.
6. Credential-refresh degradation and its behavior before/after ticket expiry are validated without confusing FE/BE process readiness with external catalog health.
7. Compatibility is demonstrated against the existing HMS, Kerberos, Iceberg, and RustFS configuration before declaring the integration complete.

## Traceability

These requirements refine FR-1, FR-5, and FR-7 and intent NFR-1 through NFR-6. They implement the approved Unit 2 Functional Design rules for FE/BE readiness, first initialization, safe persistence, credential refresh degradation, local exposure, and operator recovery. Catalog registration, SQL authorization, and query/write acceptance remain assigned to Unit 3 and integrated verification.

## Extension Applicability

- Security Baseline extension: disabled; explicitly approved local security requirements above remain binding.
- Property-Based Testing extension: partial; these NFRs do not require pure-function or serialization behavior by themselves.
- Resiliency Baseline extension: disabled; best-effort recovery and preservation requirements above are retained because they were explicitly approved for this unit.
