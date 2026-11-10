# NFR Requirements — Spark Writer Runtime

## Scope and Quality Profile

These requirements apply to the writer credential lifecycle in the existing local Spark service. The target is a local Docker Compose PoC, not a production availability or performance service. The existing writer identity remains shared across Spark workloads; the existing KDC, Hive Metastore, RustFS, Spark deployment, and persistent data are retained.

No throughput, latency, workload-scale, production uptime, RTO/RPO, failover, or disaster-recovery target has been specified. Use current Spark resource limits and do not claim a capacity guarantee. External monitoring/alerting is out of scope; local Docker health status and sanitized logs provide operator visibility.

## Requirements

### SWR-NFR-01 — Fail-Closed Readiness

- The Spark worker MUST NOT be considered ready for new ETL work until a currently valid TGT for `write-service-account@LAKEHOUSE.LOCAL` has been acquired and validated.
- Initial acquisition or validation failure MUST leave the worker unavailable for new ETL tasks and emit a sanitized diagnostic.
- Docker container health MUST reflect credential readiness as well as the underlying Spark service condition; a running process alone is not sufficient for a healthy state.

### SWR-NFR-02 — Spark-Service Admission Gate

- When the writer credential lifecycle declares the worker unavailable, the Spark service MUST prevent new ETL tasks from being assigned to that worker.
- The admission boundary is the Spark service/worker, as selected in the clarification. Docker health status is an operator signal and is not, by itself, the enforcement mechanism.
- The implementation MUST NOT deliberately terminate already-running workloads solely because the credential lifecycle became unavailable. In-flight operations may succeed or fail according to the authentication result returned by Hive Metastore or RustFS.
- NFR Design and Infrastructure Design MUST select and verify a Spark mechanism that enforces this gate while preserving active tasks. If the existing Spark topology cannot meet both constraints, record the limitation and return for a design decision before claiming the requirement passes.

### SWR-NFR-03 — Renewal Timing and Recovery

- The service MUST begin renewal or fresh-ticket acquisition attempts at least 15 minutes before the current TGT expiry.
- While the current TGT remains valid, renewal/reacquisition MUST be retried no less frequently than once per minute until a valid ticket is restored or the current ticket expires.
- If renewal fails, the service MUST attempt to acquire a fresh TGT from the existing keytab.
- If no valid TGT can be restored, the worker MUST become unavailable for new ETL work before treating the expired credential as unusable; it MUST never report an expired TGT as ready.
- After becoming unavailable, the service MUST automatically attempt fresh TGT acquisition at least once per minute. It MAY restore readiness only after validating a fresh TGT for the configured principal.
- NFR Design MAY select a shorter attempt cadence when needed to satisfy the 15-minute margin, but not a longer one. It must define timing edge cases and retry execution without conflicting retry loops.

### SWR-NFR-04 — Credential and Cache Protection

- Writer keytab and RustFS credential files MUST be mounted read-only into the Spark service.
- Protected host credential files MUST use restrictive owner-only permissions, target mode `0600`.
- The ticket-cache directory MUST be runtime-scoped and private to the service, target mode `0700`; cache files MUST be owner-only, target mode `0600`.
- The Spark service cache MUST be separate from per-run driver and notebook caches and MUST NOT be stored in the Git Bundle, image layer, or persistent lakehouse data volume.
- If the deployment platform cannot preserve requested file modes or ownership, Build and Test MUST fail the credential protection check rather than silently weaken it.

### SWR-NFR-05 — Sanitized Observability

- The service MUST expose credential readiness through Docker health status and sanitized logs.
- Logs/health diagnostics MAY identify the configured principal, lifecycle state, ticket validity status, and sanitized error category.
- Logs/health diagnostics MUST NOT include keytab contents, RustFS secret values, Kerberos ticket contents, or credential-bearing command output.
- Health status MUST change to unhealthy/unready when the worker cannot accept new ETL work, and return to healthy only after valid ticket recovery and Spark worker readiness.

### SWR-NFR-06 — Technology and Resource Constraints

- Implement the lifecycle with the existing Bash entrypoint and Kerberos client utilities already available in the Spark image; do not add a separate helper service or runtime package without an approved design change.
- Build and Test MUST verify the required Bash/Kerberos commands exist in the exact Spark image and that their output can be handled without leaking credentials. If a required command is absent, surface it as a concrete implementation constraint before adding packages.
- **Approved design exception (2026-10-26)**: the pinned Spark base image lacks `kinit` and `klist`; the user approved deriving a local image from the same pinned base digest and installing Debian `krb5-user`. No other runtime package or helper service is in scope.
- Keep current Spark resource sizing and single-service topology; no new performance or scaling target is introduced by this unit.

## Verification Targets for Later Build and Test

- Startup with valid writer credentials becomes healthy only after TGT validation and Spark worker readiness.
- Missing/invalid keytab or failed initial ticket acquisition does not produce a healthy/ETL-ready worker.
- Renewal begins within the specified margin; failed renewal triggers keytab reacquisition and at-most-one-minute retry cadence while recovery is pending.
- An unrecoverable/expired ticket produces unhealthy status and prevents new task assignment while allowing already-running workloads to continue.
- Recovery obtains and validates a fresh TGT before the worker returns to healthy and accepts new ETL tasks.
- Credential modes, read-only mounts, private cache ownership, and sanitized diagnostics meet the stated targets.

## Applicability Notes

- **Scalability/performance**: No numeric target supplied; preserve the existing local Spark capacity.
- **Availability**: No uptime/SLA or DR target supplied; enforce local readiness and automated ticket recovery only.
- **Security**: Explicit credential-protection requirements remain in force even though Security Baseline is disabled.
- **Property-based testing**: Apply only if a pure function or serialization round-trip is introduced; service lifecycle behavior is verified with focused integration checks.
- **Usability**: No UI is in scope; Docker health and sanitized logs are the local operator interface.
