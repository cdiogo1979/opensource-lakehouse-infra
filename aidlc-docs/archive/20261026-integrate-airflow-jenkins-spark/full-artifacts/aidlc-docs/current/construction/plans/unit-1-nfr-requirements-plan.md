# Unit 1 NFR Requirements Plan — Spark Writer Runtime

## Unit and Approved Functional Baseline

This stage sets measurable quality requirements for Unit 1, the existing Spark service's shared writer credential lifecycle. The approved Functional Design requires a valid writer TGT before the worker accepts new ETL work; renewal failure triggers fresh acquisition from the existing keytab; if the TGT cannot be restored, new work is blocked; active work is not deliberately terminated. RustFS uses separate file-backed writer credentials.

The approved project scope is a local Docker Compose PoC. No production SLA, disaster recovery objective, workload throughput target, or additional capacity requirement was supplied. Keep the existing Spark service and dependencies; do not introduce a new credential platform or rotate identities.

## NFR Assessment Checklist

- [x] Read the Unit 1 Functional Design, approved requirements, and existing Spark/Kerberos/RustFS boundaries.
- [x] Assess scalability/performance and availability against the approved local PoC scope; no numerical service-level or capacity target is currently specified.
- [x] Resolve the targeted NFR questions below and check answers for ambiguity or contradictions. Answers A/A/A/A/A are clear; the admission-gating clarification selects the Spark service boundary.
- [x] Define measurable credential renewal/recovery and readiness behavior.
- [x] Define runtime credential/cache protection and sanitized observability requirements.
- [x] Confirm the minimal technology stack and any dependency constraints.
- [x] Generate `aidlc-docs/current/construction/unit-1/nfr-requirements/nfr-requirements.md`.
- [x] Generate `aidlc-docs/current/construction/unit-1/nfr-requirements/tech-stack-decisions.md`.
- [x] Validate against Functional Design A/A/A, US-03, FR-4/FR-5, NFR-1/NFR-3, and the approved Units sequence.
- [x] Present NFR Requirements for explicit review and approval.

## Assessment Boundaries

- **Scalability/performance**: This is one existing local Spark service with no throughput/latency target. Do not add capacity or performance requirements without an approved change.
- **Availability/recovery**: Production uptime, failover, disaster recovery, and external alerting are outside the approved local PoC scope. Service readiness for new work and ticket recovery remain in scope.
- **Security**: Credential files must remain protected and read-only to consuming containers; ticket caches must be private and runtime-scoped; diagnostics must not expose credential values. The Security Baseline extension is disabled, but these explicit requirements remain mandatory.
- **Reliability**: Startup fail-closed behavior, renewal/reacquisition, blocking new work when no valid TGT exists, and behavior of already-running workloads are fixed by Functional Design. Timing, retry cadence, recovery automation, and observable readiness need measurable targets.
- **Maintainability**: Prefer existing Spark image tools and runtime boundaries; any new dependency must have a specific need and justification.
- **Usability**: No new user interface is in scope. Operator-facing readiness/failure should be visible through local service status and sanitized diagnostics.
- **Property-based testing**: The extension is partial. Apply only if this unit introduces applicable pure functions or serialization round-trips; do not force PBT onto process lifecycle behavior.

## NFR Questions

Please fill each `[Answer]:` tag below. If no option fits, select X and describe the target.

### Question 1 — Ticket renewal timing

What renewal margin and retry cadence should the Spark service meet?

A) Begin renewal/reacquisition attempts at least 15 minutes before TGT expiry; retry at least once per minute while the ticket remains valid. Never treat an expired TGT as ready.

B) Begin attempts at least 5 minutes before expiry; retry at least every 30 seconds while the ticket remains valid. Never treat an expired TGT as ready.

X) Other (provide the desired renewal margin and retry cadence after `[Answer]:`).

[Answer]:A

### Question 2 — Automatic recovery after becoming unavailable

If the TGT expires or cannot be restored and the service is unavailable for new ETL work, how should recovery proceed?

A) Automatically retry fresh TGT acquisition from the existing keytab at least once per minute; restore readiness only after validating a fresh TGT.

B) Stop automatic retries after the initial recovery attempt; require an operator to restart the Spark service after correcting the credential problem.

X) Other (describe the retry/restart behavior after `[Answer]:`).

[Answer]:A

### Question 3 — Credential file and cache protections

Which minimum runtime filesystem protections should be required?

A) Keytab and RustFS credential files are read-only inside the service and have restrictive host permissions (target mode `0600`); ticket-cache directory is service-private (`0700`) and cache files are owner-only (`0600`).

B) Require read-only mounts and private runtime cache ownership, but defer exact host file modes to the existing credential provisioning configuration.

X) Other (describe required modes/ownership after `[Answer]:`).

[Answer]:A

### Question 4 — Readiness and failure visibility

How should operators see that the worker can or cannot accept new ETL work?

A) Expose credential readiness through the Spark container's health status and sanitized logs; never include secret/ticket contents.

B) Use sanitized startup/renewal logs only; do not add or change a container health check in this unit.

X) Other (describe the observable status/diagnostics after `[Answer]:`).

[Answer]:A

### Question 5 — Credential lifecycle implementation dependencies

Which implementation constraint should the NFR design use for the renewal helper?

A) Use the existing Bash entrypoint and Kerberos utilities already present in the Spark image; avoid adding a new runtime dependency unless implementation proves it necessary.

B) Add a small dedicated helper runtime/package for ticket renewal and readiness, with the extra image/dependency maintenance documented.

X) Other (describe the preferred stack constraint after `[Answer]:`).

[Answer]:A

## Approval Gate

After answers are reviewed and any ambiguity is resolved, create the NFR requirements and tech-stack decision artifacts, then request explicit approval before proceeding to Unit 1 NFR Design.

**Status**: Answers A/A/A/A/A and the Spark-service admission-gating clarification are resolved. NFR Requirements artifacts are generated and awaiting explicit review and approval.
