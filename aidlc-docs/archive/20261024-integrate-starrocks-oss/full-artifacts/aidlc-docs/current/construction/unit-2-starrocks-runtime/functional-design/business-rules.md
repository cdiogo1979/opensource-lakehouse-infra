# Unit 2 Business Rules — StarRocks Runtime

## Startup and Readiness

1. **Single-node topology:** The runtime consists of exactly one FE and one BE for this local PoC. (FR-1)
2. **Joint readiness:** The overall runtime is ready only when FE and BE are healthy and the FE SQL service is available. If either node is unhealthy, report the overall runtime as not ready. (FR-1, US-05)
3. **Catalog boundary:** FE/BE readiness does not imply that the Hive Iceberg catalog, RustFS reads, SQL grants, or query/write paths are ready; those are configured and verified by Unit 3. (FR-2, FR-3, FR-6)
4. **Partial failure recovery:** Configured Compose recovery may restart the unhealthy service. Recovery must preserve both FE and BE persistent volumes. (Q3 A, NFR-3)

## Initialization and Persistence

5. **First initialization:** Automatic initialization is allowed only on first startup when both FE and BE persistent locations are empty. (Clarification 1 A)
6. **One-sided empty state:** If the runtime has previously initialized and one node's persistent state is missing or empty while its peer retains state, fail startup and preserve the remaining data. Never silently initialize the empty side. (Q2 A, Clarification 1 A, FR-7)
7. **Invalid existing state:** Invalid or incompatible node state causes startup to fail with an actionable, secret-free diagnostic. Do not delete, rewrite, or reinitialize the affected state automatically. (Q2 A, NFR-3)
8. **Paired-state validation:** Before starting either node, validate the pair: both empty is eligible for initial setup; one empty and one initialized is an error; invalid/incompatible state is an error. Resolve the detection mechanism in Infrastructure Design. (Clarification 1 A)
9. **Persistent lifecycle:** Normal stop, start, recreate, and recovery operations retain the FE and BE named volumes and all existing project services/data. (FR-7, NFR-3)

## Credentials and Security

10. **Service identity only:** HMS and RustFS access use the dedicated StarRocks service identities provisioned in Unit 1. End-user Kerberos impersonation is outside this runtime. (FR-4, FR-5)
11. **Read-only runtime inputs:** The runtime consumes the Unit 1 keytab and RustFS secret through read-only mounts. It does not modify or rotate either credential. (FR-4, FR-5, NFR-1, NFR-2)
12. **No secret disclosure:** Passwords, keytabs, ticket contents, and RustFS secret values are not written to tracked files, command output, or logs. (NFR-1)
13. **Kerberos refresh degradation:** If TGT refresh fails while the current ticket remains valid, keep the runtime available, report credential degradation, and retry at the interval determined in later design. (Q1 A, FR-5)
14. **Expired TGT:** If the TGT expires before refresh succeeds, secured catalog operations may fail. FE/BE process health must not be presented as proof that HMS operations are functioning. (Q1 A, FR-5)

## Endpoint and Unit Boundaries

15. **Local exposure:** Host-published SQL and FE UI endpoints bind to loopback only. Exact port and Compose declarations are specified in Infrastructure Design. (FR-1, NFR-1)
16. **No catalog/bootstrap in Unit 2:** This unit does not create the Iceberg catalog, SQL users/roles, grants, sample data, or write tests. Those belong to Unit 3. (FR-2, FR-3, FR-6)
17. **No destructive shared changes:** Adding or operating StarRocks must not remove or reset existing services, Hive metadata, RustFS data, identities, or notebook workspaces. (FR-7)

## Extension Applicability

- Security Baseline extension: disabled; applicable project requirements above still govern the design.
- Property-Based Testing extension: partial; no pure functions or serialization logic are defined in these design artifacts, so PBT is not applicable here.
- Resiliency Baseline extension: disabled; the user-approved FE/BE failure and persistence behavior remains binding.
