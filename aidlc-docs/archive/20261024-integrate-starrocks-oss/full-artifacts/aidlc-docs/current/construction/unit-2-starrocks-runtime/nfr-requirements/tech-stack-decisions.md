# Tech Stack Decisions — Unit 2 StarRocks Runtime

## Decision Summary

| Area | Decision | Rationale |
|---|---|---|
| Deployment platform | Existing Docker Compose project | Matches the local PoC and preserves the current lakehouse network and service lifecycle. |
| Analytical engine | StarRocks OSS | Approved engine for SQL analytics over the existing Iceberg lakehouse. |
| Runtime topology | One FE and one BE | Fixed single-node PoC scope; production HA and horizontal scaling are excluded. |
| Image version | Select a reviewed stable OSS release and pin both version and digest after compatibility review | Avoids floating tags and gates adoption on HMS 3.1.3, Kerberos, Iceberg, and RustFS compatibility. The exact version/digest remains for the later compatibility review. |
| Persistent state | Separate named volumes for FE and BE | Preserves each node's state across container recreation and allows safe recovery without resetting shared services. |
| Network exposure | Existing internal Compose network; SQL and FE UI host ports on loopback only | Keeps service-to-service access internal while limiting host access to the local machine. |
| Credential delivery | Unit 1 keytab and RustFS secret mounted read-only | Reuses the approved service identity contract and avoids embedding secrets in images or tracked config. |
| Kerberos lifecycle | Runtime TGT refresh from the dedicated service credential; retry before ticket expiry and expose a degraded state while a valid TGT remains | Satisfies the approved renewal behavior without propagating end-user identities. Exact scheduling depends on supported runtime mechanisms and ticket lifetime. |
| Health and recovery | FE/BE readiness with configured Compose process recovery | Provides best-effort local availability, preserves volumes, and avoids additional orchestration components. |
| Logs and monitoring | Container stdout/stderr accessed with Docker Compose logs; no persistent collector or monitoring service | Fits the manual PoC operating model and existing diagnostic style. |
| Capacity guidance | Measure and document minimum and recommended local resources for the selected compatible release | User selected no fixed host budget or workload SLA; observed resources will be documented with their conditions. |

## Constraints and Contracts

- Preserve existing Compose services, networks, named volumes, credentials, Hive metadata, RustFS objects, and notebook state.
- The runtime uses the dedicated StarRocks service identity for HMS/RustFS. SQL-user identities are not forwarded as Kerberos principals.
- No credential material or Kerberos ticket contents may appear in tracked files or logs.
- FE/BE readiness is distinct from external Iceberg catalog health and query/write readiness.
- First initialization may occur only when both FE/BE persistent locations are empty; one-sided empty or invalid state must fail without destructive recovery.
- No fixed startup-time, uptime, recovery-time, concurrency, throughput, or query-latency objective is established.
- No Apache Ranger, production HA, external identity provider, cloud platform, monitoring service, or new orchestration framework is introduced.

## Deferred Decisions

- Exact StarRocks OSS version and digest: select after current compatibility research and validation.
- FE/BE health-check implementation, startup order, resource limits, mounts, and Compose restart policy: Unit 2 NFR Design and Infrastructure Design.
- Supported method for maintaining/refreshing the Kerberos ticket and safely identifying paired first initialization: resolve against the pinned StarRocks runtime during NFR/Infrastructure Design.
- Hive Iceberg catalog, RustFS catalog properties, SQL users/grants, and bootstrap mechanism: Unit 3.
