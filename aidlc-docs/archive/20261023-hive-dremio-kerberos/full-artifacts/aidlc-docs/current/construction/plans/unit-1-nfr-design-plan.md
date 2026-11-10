# NFR Design Plan — Unit 1 Foundation

## Scope

Translate the approved Unit 1 NFRs into logical design patterns for Docker Compose orchestration, local service exposure, runtime credentials, readiness/retry behavior, and persistence. Concrete images, healthcheck commands, mounts, ports, environment files, and Compose syntax remain for Infrastructure Design.

The design must preserve: single-host local operation; no availability or performance SLA; loopback-only host exposure; secrets in restricted ignored runtime storage; safe idempotent retries; state preservation after failure; explicit destructive reset; and no monitoring/scaling infrastructure. It does not resolve the Hive/RustFS authorization feasibility gate.

## NFR Design Checklist

- [x] Select readiness and dependency-gating pattern for Compose services and one-shot initializers.
- [x] Select retry/recovery pattern consistent with safe rerun and fail-closed requirements.
- [x] Select local credential/keytab delivery pattern and host exposure pattern.
- [x] Confirm no additional performance/scaling, monitoring, or HA logical components are needed.
- [x] Generate `aidlc-docs/current/construction/unit-1-foundation/nfr-design/nfr-design-patterns.md`.
- [x] Generate `aidlc-docs/current/construction/unit-1-foundation/nfr-design/logical-components.md`.
- [x] Validate patterns against approved NFR and Functional Design artifacts.

## Design Questions

### Question 1 — Resilience and initialization gating

Which readiness/retry pattern should Unit 1 use?

A) Use Docker Compose health/readiness checks for long-running dependencies, gate dependent services on readiness and one-shot initializers on successful completion, and allow only bounded retries for explicitly idempotent steps; fail dependent startup and preserve volumes on failure (recommended; follows the approved requirements).

B) Add a separate supervisor or recovery service that automatically retries/restarts failed initialization.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 2 — Scalability pattern

How should service instance count and scaling be designed?

A) Use one instance per service in the local Compose deployment; stateful services use their named volumes, with no replicas, load balancer, or scale-out pattern (recommended; no scaling target exists).

B) Design any service for multiple replicas or future scale-out now; specify which one and the expected load.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 3 — Performance pattern

What optimization approach should be used?

A) Keep defaults appropriate for the small TPCH demo and prioritize correctness/startup clarity; do not add caches, queues, or benchmarks without a measured problem (recommended; no performance SLA exists).

B) Add a performance target and a corresponding resource/tuning strategy; specify the target.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 4 — Security and credential delivery

Which local credential handling pattern should the design use?

A) Generate/store credentials in an ignored, access-restricted host runtime directory and mount only required files read-only into the consuming containers; do not put secrets in tracked files, images, or logs (recommended; matches the approved NFRs).

B) Use file-backed Docker Compose secrets for all credentials/keytabs, with local secret source files; document any services that cannot consume secrets as files.

C) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — Logical components and service exposure

Should any supporting infrastructure components be added for Unit 1?

A) Add no monitoring, alerting, HA, cache, queue, or admin service. Bind developer-facing published ports to loopback and use Compose health/status plus actionable logs (recommended; matches the approved scope).

B) Add a specific supporting component or expose a specific service beyond loopback; describe the need and boundary.

X) Other (describe after `[Answer]:`)

[Answer]:A

## Applicability Notes

- Security Baseline and Resiliency Baseline extensions are disabled. Functional security and recovery requirements remain applicable.
- Performance and scalability categories are included for explicit confirmation; their current approved requirements specify no SLA or scaling target.
- No user interface is in Unit 1; operator usability remains shell/Compose based.

## Extension Compliance Summary

- **Security Baseline**: Not enabled. Local credential handling, loopback-only exposure, separation of component credentials, and secret-safe logs remain required by approved NFRs.
- **Property-Based Testing**: Partial extension is not applicable to this design-only stage; no code or tests are introduced here.
- **Resiliency Baseline**: Not enabled. Approved fail-closed startup, safe idempotent retries, and persistent-state recovery rules are represented in the design.

## Current Status

NFR Design artifacts are complete and await explicit user approval. No application configuration has been changed.
