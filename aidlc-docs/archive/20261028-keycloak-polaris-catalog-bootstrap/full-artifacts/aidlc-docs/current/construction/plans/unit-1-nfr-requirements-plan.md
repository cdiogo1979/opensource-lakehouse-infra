# Unit 1 NFR Requirements Plan — Runtime Composition and Legacy Removal

## Unit context

U1 provides the local runtime foundation for the `default` data-product bootstrap and removes active FreeIPA, Hive Metastore, and MIT Kerberos/KDC dependencies. Its functional design defines service-scoped readiness, fail-closed dependency behavior, preservation of healthy state during partial failures, deferred opt-in services, fresh state, and a separate explicit legacy-volume cleanup action.

This plan clarifies measurable quality expectations for the local Compose runtime. The approved project requirements already require a one-machine Docker Compose deployment, loopback-bound administrative UIs, isolated persistent metadata, protected secrets, fail-closed authorization, pinned compatible images/libraries, and actionable credential-safe diagnostics. U1 NFR Requirements must refine the runtime-facing expectations without changing those approved requirements or selecting implementation details that belong in Infrastructure Design.

## Planning checklist

### Analyze approved design and requirements

- [x] Review the approved U1 Functional Design artifacts and plan.
- [x] Review applicable approved NFRs NFR-01–NFR-08 and requirements FR-13/FR-14.
- [x] Keep destructive cleanup separate from normal startup/bootstrap; preserve RustFS data and unrelated state.
- [x] Separate measurable runtime quality requirements from implementation choices reserved for Infrastructure Design.

### Plan approval gate

- [x] Collect all NFR clarification answers below.
- [x] Resolve ambiguity and check consistency with approved requirements.
- [x] Obtain explicit approval of this plan before generating NFR Requirements artifacts.

### Generate NFR Requirements artifacts after plan approval

- [x] Generate `aidlc-docs/current/construction/unit-1/nfr-requirements/nfr-requirements.md`.
- [x] Generate `tech-stack-decisions.md` documenting constraints and decisions without prematurely selecting image versions.
- [x] Validate alignment with U1 scope and the approved global requirements.
- [x] Present both artifacts for explicit NFR Requirements approval.

## NFR clarification questions

Replace each `[Answer]:` with a selected option or a concrete alternative.

### Question 1 — Capacity and concurrency target

The U1 journey runs on one developer machine. What should the core runtime target?

A) One local operator and one bootstrap/smoke workload at a time; no multi-user concurrency or horizontal scaling target (Recommended for this local Compose journey).

B) Multiple concurrent bootstrap/smoke workloads; provide a target number and host resource limit.

C) Other (specify expected concurrent users/workloads and available CPU/memory).

[Answer]:A

### Question 2 — Startup and readiness bound

How long may default runtime startup take before the operator receives a terminal readiness result?

A) Use a bounded 10-minute startup/readiness window with per-service status; allow configuration of the bound for slower developer machines (Recommended: avoids indefinite waits while accommodating local image/service startup).

B) Require all core services ready within 5 minutes, then fail with actionable provider status.

C) Do not impose a total startup bound; report current provider readiness and let the operator decide when to stop waiting.

X) Other (give a maximum duration and desired timeout behavior).

[Answer]:A

### Question 3 — Failure recovery and restart behavior

After a core provider fails or becomes unavailable, what recovery behavior should the local runtime provide?

A) Restart failed containers according to a bounded container restart policy; never restart healthy dependencies or delete state. Report when operator action is needed (Recommended: local convenience while preserving the Functional Design safety boundary).

B) Do not restart automatically; report the failure and leave all recovery to the operator.

C) Other (specify retry count/backoff and which services may restart automatically).

[Answer]:A

### Question 4 — Persistent state backup and retention

U1 requires identity and catalog metadata to persist across restarts but has no backup target. What is expected for this local environment?

A) Persist state in named stores and document an operator-managed backup/restore procedure; no scheduled backup service is required in this journey (Recommended for the local single-machine scope).

B) Add automated scheduled backups; specify retention period and backup destination.

C) Other (specify retention, recovery point, and recovery time expectations).

[Answer]:A

### Question 5 — Host exposure and transport

The approved NFR requires administrative UIs to bind to loopback. What host/network boundary should apply to the rest of the core runtime?

A) Publish only necessary operator-facing ports on loopback; keep provider-to-provider APIs on an isolated Compose network. Plain HTTP is acceptable only on loopback and that private local network (Recommended for a local developer stack).

B) Publish additional service APIs to the host on loopback; list which ports and clients need them.

C) Require TLS for all service-to-service and host-published traffic, including local development endpoints.

X) Other (specify allowed host interfaces, exposed APIs, and transport requirements).

[Answer]:A

### Question 6 — Operational diagnostics

What minimum operational visibility is required for the default runtime?

A) Per-service readiness, dependency-aware startup status, and actionable redacted startup/runtime errors available through the existing local runtime tools; no separate monitoring stack or log-retention service (Recommended and consistent with NFR-07).

B) Add a metrics/monitoring service; specify required metrics and retention.

C) Other (specify status, alerting, and log retention needs).

[Answer]:A

## Answer analysis

The user selected A for all six questions. The choices define a single local operator and one bootstrap/smoke workload at a time; a configurable, bounded 10-minute startup/readiness window; bounded restarts of failed containers without disturbing healthy providers or persistent state; operator-managed backup/restore documentation without scheduled backups; loopback-only operator-facing host ports with provider APIs on the private Compose network and HTTP restricted to that local boundary; and dependency-aware readiness plus actionable, redacted diagnostics without a separate monitoring stack.

These answers are consistent with U1 Functional Design and approved NFR-01–NFR-08. “Bounded restart” is a behavioral requirement; retry limits and backoff belong in Infrastructure Design. The readiness timeout is configurable, so slower developer machines can adjust it without changing the default. No additional clarification is needed.

## Gate

All six answers are complete, reviewed, and consistent. The plan was approved; both NFR Requirements artifacts are generated and await separate artifact approval. No source, runtime services, volumes, or object data were changed.
