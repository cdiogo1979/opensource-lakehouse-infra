# Unit 2 Business Logic Model — StarRocks Runtime

## Purpose

Define the runtime behavior for the local single-FE/single-BE StarRocks deployment. The runtime provides the SQL engine process and its service credentials; Unit 3 configures the Iceberg catalog, SQL identities, grants, and query/write behavior.

## Actors and Responsibilities

- **Platform operator:** Starts and stops the local Compose stack, inspects readiness and diagnostics, and resolves failures that cannot be recovered safely by the runtime.
- **StarRocks runtime:** Coordinates the FE and BE lifecycle, consumes the Unit 1 service credential files, maintains the Kerberos ticket lifecycle, and preserves node state.
- **FE:** Provides the StarRocks frontend and SQL endpoint when the runtime reaches ready state.
- **BE:** Provides the StarRocks backend execution capacity required for the single-node runtime to be ready.
- **External catalog and object store:** Hive Metastore and RustFS are consumed by the Unit 3 catalog configuration. Their catalog registration and query-level behavior are outside this unit's readiness contract.

## Runtime Lifecycle

1. **Uninitialized:** On the first deployment only, if both FE and BE persistent data locations are empty, the runtime initializes the pair using the selected StarRocks release's supported initialization behavior.
2. **Starting:** The runtime starts FE and BE with their own persistent state and the Unit 1 read-only service credentials. Credentials are not copied into tracked configuration or emitted in diagnostics.
3. **Ready:** Both FE and BE are healthy and the FE SQL service is available on the approved internal and loopback-bound endpoints. This state does not claim that the external Iceberg catalog is configured or reachable.
4. **Credential degraded:** A TGT refresh attempt has failed while the current ticket remains valid. The runtime remains available, reports the degraded credential condition, and retries refresh at the designed interval.
5. **Not ready:** FE or BE is unhealthy. The overall StarRocks runtime is reported not ready; configured Compose recovery may run while both node volumes remain intact.
6. **Startup blocked:** A one-sided empty state, invalid or incompatible persisted state, or a missing/invalid required credential prevents safe startup. The runtime reports an actionable diagnostic and preserves all available persistent data for operator inspection.

## Ticket Refresh Failure Flow

- Use the StarRocks service principal and Unit 1 keytab; do not use end-user Kerberos credentials.
- On a transient refresh failure, retain runtime availability while the current TGT remains valid, expose a degraded credential status, and retry according to the interval defined during NFR/Infrastructure Design.
- If the TGT expires before refresh succeeds, operations requiring the secured HMS catalog may fail. The runtime must not report catalog functionality as healthy based only on FE/BE health.
- Credential contents and raw key material never appear in state messages or logs.

## Persistent State Initialization and Recovery

- First startup may initialize FE and BE only as a pair when both persistent locations are empty.
- After the first successful initialization, an empty or missing one-sided node state is an error. Do not silently initialize that node alongside existing peer state.
- Invalid or incompatible persisted state blocks startup. Preserve the volume and require operator diagnosis; no automatic deletion or destructive reinitialization is allowed.
- Infrastructure Design must define how startup distinguishes a clean paired initialization from a one-sided missing/empty state using the supported StarRocks runtime behavior. It must not infer permission to reset a populated node.
- Compose restart/recreate operations must retain both node volumes. A coordinated reset, if ever needed, is an explicit operator action outside routine startup.

## Scope and Traceability

- **FR-1:** Single FE and BE runtime, persistent state, local endpoints, and operator resource/startup guidance.
- **FR-5:** Dedicated service principal/keytab and renewable/refreshed ticket lifecycle.
- **FR-7 / NFR-3:** Preserve existing services and data; keep FE/BE state across container recreation.
- **NFR-1:** Loopback-only host exposure and credential redaction.
- **NFR-4 / NFR-5 / NFR-6:** Pin compatible runtime, document local requirements, and document safe operations; exact mechanisms are decided in later design stages.
- **Unit 3 boundary:** Hive Iceberg catalog registration, SQL users/roles/grants, and catalog query/write integration.

## Known Design Dependency

The startup check must identify the paired-empty first-start case and reject a one-sided empty state without modifying the populated peer. The detection mechanism and failure diagnostics are deferred to Unit 2 NFR and Infrastructure Design. No runtime implementation is created by this functional design.
