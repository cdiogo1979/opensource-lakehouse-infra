# Unit 1 NFR Design Plan — Runtime Composition and Legacy Removal

## Unit context

U1 provides the default local runtime for Keycloak, Polaris with dedicated PostgreSQL metadata, and RustFS. The approved NFR requirements target one operator and one bootstrap/smoke workload at a time, a configurable 10-minute readiness bound, bounded recovery, separate persistent state with operator-managed backup guidance, loopback-only host access, private provider networking, and actionable redacted diagnostics. Exact Compose profiles, services, health checks, volumes, ports, versions, and retry values remain to be designed.

This NFR Design defines patterns and logical infrastructure components. It does not implement Compose changes or choose exact image tags/digests; those are recorded in Infrastructure Design.

## Planning checklist

### Analyze approved U1 requirements and design

- [x] Review approved Functional Design artifacts.
- [x] Review U1 NFR Requirements and tech-stack decisions.
- [x] Evaluate resilience, scalability, performance, security, and logical infrastructure component needs.
- [x] Preserve the explicit legacy cleanup boundary and no-delete-on-startup requirement.

### Plan approval gate

- [x] Collect all design answers below.
- [x] Resolve ambiguity and confirm alignment with approved requirements.
- [x] Obtain explicit approval of this plan before generating NFR Design artifacts.

### Generate NFR Design artifacts after plan approval

- [x] Generate `aidlc-docs/current/construction/unit-1/nfr-design/nfr-design-patterns.md`.
- [x] Generate `logical-components.md` describing the runtime building blocks and interactions.
- [x] Validate every pattern against U1 NFR requirements and defer Compose-specific details to Infrastructure Design.
- [x] Present both artifacts for explicit NFR Design approval.

## NFR Design questions

Replace each `[Answer]:` with a selected option or a concrete alternative.

### Question 1 — Resilience and unhealthy-provider recovery

The approved requirements call for bounded restarts and service-scoped readiness. A process can exit, or it can remain running while failing its health check. How should recovery handle these cases?

A) Use a bounded container restart policy for process exits (default maximum three retries); use health checks for readiness/status, but do not add a watchdog that restarts a live unhealthy container. Dependent work waits up to the configured readiness bound, then reports the failed provider for operator action (Recommended: keeps recovery bounded and avoids hidden restart loops).

B) Add a lightweight watchdog that also restarts live unhealthy containers, with a bounded retry count and backoff.

C) Use health/readiness reporting only; do not restart any container automatically.

X) Other (specify process-exit and health-failure behavior, retry limit, and backoff).

[Answer]:A

### Question 2 — Scalability and local resource controls

The runtime is single-machine and has no horizontal scaling target. How should CPU/memory pressure be handled?

A) Do not impose fixed CPU/memory caps because developer host capacity varies; document that simultaneous bootstrap/smoke runs are unsupported and allow operators to set Compose resource limits when needed (Recommended for the local development scope).

B) Define fixed per-service CPU and memory caps; provide the host capacity and desired limits.

C) Provide an optional constrained-resource Compose profile with documented defaults; normal local startup remains uncapped.

X) Other (specify host capacity and limits).

[Answer]:A

### Question 3 — Performance and startup pattern

The accepted startup/readiness bound is 10 minutes and there is no throughput or latency target. Which startup pattern should the design use?

A) Start independent core providers concurrently, honor declared prerequisites, and use a single bounded readiness coordinator that reports each provider; add no cache or queue for this journey (Recommended: improves startup time without extra services).

B) Start every provider serially in a fixed order, with a separate 10-minute bound per provider.

C) Use a strict 10-minute total bound but do not coordinate readiness; leave waiting to the operator.

X) Other (specify parallelism and timeout allocation).

[Answer]:A

### Question 4 — Secret delivery pattern

Approved NFR-04 permits protected files or Compose secrets. Which pattern should U1 standardize for service credentials?

A) Store local secret source files in a gitignored runtime directory with owner-only permissions; mount them read-only as Compose secrets or read-only files, and have services consume file paths rather than environment values where supported (Recommended: reduces accidental disclosure and supports local operations).

B) Use environment variables populated from a protected local `.env` file; never commit the file and redact logs.

C) Use an external secret manager even for the local Compose journey.

X) Other (specify storage, delivery, and file permissions).

[Answer]:A

### Question 5 — Logical network segmentation

The requirements keep provider APIs on a private Compose network and host publications on loopback. How many logical networks should the core use?

A) One private core network for Keycloak, Polaris/PostgreSQL, and RustFS, with only required operator endpoints published to loopback (Recommended: simplest topology for a single-host journey).

B) Separate identity/catalog and catalog/storage networks, connecting providers only to the networks they require.

C) Other (describe network boundaries and which services share them).

[Answer]:A

### Question 6 — Legacy-volume cleanup safeguards

Functional Design requires cleanup to be separate and limited to exact, reviewed retired-service volumes. What operator safeguard should the cleanup design include?

A) Provide a dry-run inventory first, require an explicit second invocation with the exact reviewed volume names, reject RustFS/unrelated/ambiguous names, and never call cleanup from startup or bootstrap (Recommended: makes the destructive boundary visible and auditable).

B) Require a typed confirmation phrase after showing exact eligible volumes, in addition to explicit invocation and an allowlist.

C) Do not provide a cleanup helper; document manual removal only after ownership is verified.

X) Other (specify safeguard and invocation contract).

[Answer]:A

### Question 7 — Manual backup/restore implementation

The approved NFR requires operator-managed backup/restore documentation without scheduled backup infrastructure. What should that documentation provide?

A) Document concrete offline backup/restore commands for each named persistent store, including a stopped-service consistency requirement and an explicit warning to preserve RustFS object data (Recommended: actionable, without adding a backup service).

B) Document only general principles; leave exact commands to the operator.

C) Provide a small on-demand backup/restore helper script, with explicit service stop/start and destination validation.

X) Other (specify desired operation and consistency expectations).

[Answer]:A

## Category applicability

| Category | U1 applicability and planned treatment |
|---|---|
| Resilience | Applicable: bounded retries, readiness checks, dependency-aware waiting, preserve healthy services and persistent state. Question 1 clarifies health-failure recovery. |
| Scalability | Limited by approved local single-operator/single-workload target. No horizontal scaling; Question 2 clarifies host resource limits. |
| Performance | Applicable to bounded startup only; there are no throughput or request-latency targets and no need for cache/queue components. Question 3 clarifies startup coordination. |
| Security | Applicable: secret files, loopback publications, private APIs, safe cleanup. Questions 4–6 clarify logical patterns and safeguards. |
| Logical components | Applicable: readiness coordinator, health observations, persistent stores, core network, explicit cleanup workflow, and documented backup/restore. Questions 1, 3, 5–7 clarify component boundaries. |

## Gate

The user selected A for all seven questions. The design direction is: up to three container restarts for process exits, health checks report readiness without a watchdog restarting live unhealthy providers, no fixed CPU/memory caps, concurrent startup of independent providers under one 10-minute coordinator, file-backed secrets with read-only mounts (using Compose secrets where supported), one private core network, explicit dry-run plus exact-name cleanup invocation, and concrete offline backup/restore commands requiring stopped services.

These answers are consistent with approved U1 Functional Design and NFR Requirements. The distinction between process exit and an unhealthy-but-running service is explicit. For credential delivery, read-only file-backed mounts are the common requirement; Compose secrets are preferred when the service can consume the resulting file path, with read-only file mounts as the compatibility path. The plan was approved; the NFR Design artifacts have been generated and await separate artifact approval. No source files, running services, volumes, or object data were changed.
