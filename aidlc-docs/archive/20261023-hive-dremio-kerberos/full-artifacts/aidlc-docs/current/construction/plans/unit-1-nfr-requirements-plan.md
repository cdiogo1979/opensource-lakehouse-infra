# NFR Requirements Plan — Unit 1 Foundation

## Scope

Assess non-functional requirements for the local Compose, Hive catalog, Kerberos foundation, metastore PostgreSQL, RustFS, and bucket initializer. The plan is limited to the development PoC. Security Baseline and Resiliency Baseline extensions are disabled; approved functional security and failure-handling requirements remain in scope.

The Unit 1 Functional Design defines safe reruns, fail-closed dependent startup, preserved state on failure, separate stop/full-reset actions, and an unverified Hive/RustFS authorization path. This NFR stage will not claim the authorization feasibility gate has passed.

## NFR Assessment Checklist

- [x] Confirm capacity and scalability expectations for the local demonstration.
- [x] Confirm performance expectations and any measurement target.
- [x] Confirm availability, recovery, and persistence expectations.
- [x] Confirm local security, credential handling, and network exposure expectations.
- [x] Confirm technology version selection and compatibility change policy.
- [x] Confirm reliability, health reporting, and retry expectations.
- [x] Confirm maintainability and operational support expectations.
- [x] Confirm operator interaction and usability expectations.
- [x] Generate `aidlc-docs/current/construction/unit-1-foundation/nfr-requirements/nfr-requirements.md`.
- [x] Generate `aidlc-docs/current/construction/unit-1-foundation/nfr-requirements/tech-stack-decisions.md`.
- [x] Validate NFRs against the approved requirements, functional design, and local-only boundary.

## Extension Compliance Summary

- **Security Baseline**: N/A — disabled by user choice; requirements preserve approved local secret handling and identity boundaries.
- **Property-Based Testing (Partial)**: N/A for NFR planning; no code was added. Reassess during code generation if applicable.
- **Resiliency Baseline**: N/A — disabled by user choice; the Unit 1 functional fail-fast and recovery requirements remain active.

## Questions

### Question 1 — Capacity and scalability

What load should the foundation support for this PoC?

A) One local Compose host, two test query identities, one writer, and the existing small TPCH demonstration scale; no horizontal scaling target (recommended; matches current scope).

B) Specify additional concurrent users, data volume, or scaling expectations.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 2 — Performance expectations

What performance target should be recorded?

A) Prioritize correct repeatable startup and query access; no latency/throughput SLA or performance benchmark is required for this local PoC (recommended; no such target was specified).

B) Define numeric startup, query latency, or throughput targets that must be met.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 3 — Availability and recovery

What availability posture should Unit 1 target?

A) Single-host best effort with no HA/failover or disaster-recovery objective; persistent volumes preserve local state across container stop/start, and operators can recover manually (recommended; matches the Compose PoC).

B) Specify uptime, recovery-time, or recovery-point objectives.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 4 — Local security and exposure

Which security boundary should the local foundation use?

A) Keep services local to the development host, keep generated credentials/keytabs in ignored local runtime storage with restricted access, avoid logging secret values, and make no production-security claim (recommended; follows approved NFRs and scope).

B) Expose selected services to a trusted LAN or additional host; specify which services and the required access controls.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — Version compatibility and upgrades

How should version compatibility be handled?

A) Preserve the existing pinned Spark and Dremio versions where possible, select a compatible Hive 3.x/PostgreSQL/RustFS combination, and return any required existing-component upgrade for review before changing the approved baseline (recommended; minimizes scope change).

B) Allow changing the existing Spark or Dremio versions within this intent if needed to reach compatibility, subject to documented impact.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 6 — Reliability and automatic recovery

How should service health and retries work?

A) Report component readiness and fail dependent setup promptly; retry only safe/idempotent initialization steps, preserve state, and leave recovery to the operator (recommended; aligns with Functional Design).

B) Add automatic restart/recovery behavior for failed services; specify the expected retry or recovery policy.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 7 — Maintainability and operation

What maintainability level should Unit 1 target?

A) Keep service configuration grouped by component, document prerequisites and state transitions, and provide clear startup/stop/full-reset instructions; no monitoring stack or additional ops service (recommended; fits the local PoC).

B) Add a monitoring/administration service or other ongoing operational capability; specify the need.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 8 — Operator usability

How should operators interact with the foundation?

A) Use the existing shell lifecycle scripts and documented Compose commands, with clear status/errors and service URLs; no custom UI (recommended; matches the current project).

B) Add an operator UI or other interaction surface; specify the required workflow.

X) Other (describe after `[Answer]:`)

[Answer]:A

## Current Status

NFR answers are complete and consistent. Two NFR artifacts have been generated. They preserve the local-only boundary, pinned Spark/Dremio versions where compatible, single-host best-effort operation, and explicit Hive/RustFS authorization and version feasibility checks. Awaiting review and approval. No application configuration has been changed.
