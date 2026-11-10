# Unit 3 NFR Design Plan — Polaris Authorization and RustFS Credential Vending

## Purpose

Translate approved Unit 3 NFR requirements into concrete control-plane, credential-lifecycle, retry, capacity, and observability patterns for the existing Polaris/RustFS deployment. This stage selects design patterns and logical components; exact Polaris properties, Compose mounts, and implementation changes belong to Infrastructure Design and Code Generation.

## Inputs

- `aidlc-docs/current/construction/unit-3/nfr-requirements/nfr-requirements.md`
- `aidlc-docs/current/construction/unit-3/nfr-requirements/tech-stack-decisions.md`
- `aidlc-docs/current/construction/unit-3/functional-design/`
- `aidlc-docs/current/inception/application-design/`
- Existing pinned Polaris 1.8.0, RustFS 1.0.4, Spark 3.5.5, and Iceberg 1.8.1 contracts.

## NFR design work plan

- [x] Select the authorization/credential-vending request path and how to measure the two p95 targets without including object scans.
- [x] Define the short-lived credential configuration and cache/refresh control pattern; preserve the user/role/location binding.
- [x] Define bounded retries for safe reads and the no-replay handling for ambiguous mutations.
- [x] Define concurrent-user behavior and ensure no global authorization lock is introduced.
- [x] Select the design for safe decision events, aggregate metrics, bounded labels, and secret redaction.
- [x] Define failure containment when Polaris, RustFS STS, or the pinned Iceberg refresh mechanism is unavailable.
- [x] Generate `nfr-design-patterns.md` and `logical-components.md`.
- [x] Validate design traceability to Unit 3 functional rules and NFR targets; call out any pinned-version compatibility uncertainty.

## Clarification questions

### Q1 — Request measurement and metric source

How should the local stack measure authorization and credential-vending latency while keeping the measurement separate from Spark query and RustFS scan time?

A) Use Polaris's existing management metrics/health surface and structured service logs. Record distinct REST authorization and credential-vending durations with bounded labels; keep the management endpoint internal and add no new monitoring service (Recommended; reuses the existing Polaris control plane).

B) Add a Prometheus server and scrape configuration to Compose.

C) Other measurement design (please specify).

[Answer]: A — Reuse Polaris management metrics/health and structured service logs; record separate control-plane request and credential-vending durations with bounded labels. Keep management endpoints internal and add no monitoring service.

### Q2 — Credential lifetime and refresh control

How should the 900-second vended credential target, 600-second cache target, and Iceberg refresh behavior be applied?

A) Configure Polaris for a 900-second credential duration and 600-second-or-shorter cache after verifying pinned-version support; have Iceberg REST refresh credentials before expiry using the same user JWT and original resource scope. If refresh cannot be completed, fail the operation/session without static-key fallback (Recommended; centralizes vending policy in Polaris and keeps client identity unchanged).

B) Leave Polaris defaults and restart Spark sessions before each credential expires.

C) Other credential lifecycle design (please specify).

[Answer]: A — Target 900-second credentials and a 600-second-or-shorter cache after pinned-version verification; Iceberg REST refreshes before expiry with the same user JWT and scope. Fail closed on refresh failure.

### Q3 — Retry and ambiguous mutation pattern

Where should the safe-read-only retry policy be enforced?

A) Keep a single bounded retry at the client/request boundary for idempotent Polaris reads only. Do not retry authorization denials or mutations with ambiguous outcomes; surface an outcome-unknown failure for reconciliation. Verify Spark/Iceberg's own retry settings do not silently violate this boundary (Recommended; makes the policy explicit while preserving safe read recovery).

B) Rely on Spark and Iceberg default retries for all requests.

C) Other retry design (please specify).

[Answer]: A — At most one bounded retry for idempotent Polaris reads; no replay of denials or ambiguous mutations. Verify Spark/Iceberg retries preserve this boundary.

### Q4 — Concurrent authorization and credential vending

How should the existing two-user capacity be handled if RustFS STS or Polaris credential vending is slower than metadata authorization?

A) Keep authorization requests independent per user and avoid a global lock. Use bounded HTTP/connection pools and request timeouts for Polaris-to-RustFS STS; let dependency saturation fail within a deadline rather than queuing unbounded work (Recommended; maintains fairness and resource bounds without a new queue).

B) Serialize credential vending globally to protect RustFS.

C) Other concurrency-control design (please specify).

[Answer]: A — Keep users independent with bounded connection pools/timeouts; avoid a global lock and unbounded queueing.

### Q5 — Audit and metric identity fields

Which user/resource identifiers should appear in logs versus metric labels?

A) Structured decision logs may include validated principal, role, catalog/environment, operation class, outcome, correlation ID, and latency under protected service-log access. Aggregate metric labels remain bounded and exclude usernames, subjects, token IDs, table names, JWTs, credential values, and query contents (Recommended; supports investigations without high-cardinality or secret-bearing metrics).

B) Use the same principal and resource labels on logs and metrics for easier filtering.

C) Other logging/label policy (please specify).

[Answer]: A — Protected structured logs may include validated identity/role/resource/operation/outcome/correlation/latency; metric labels remain bounded and exclude usernames, subjects, table names, tokens, and query contents.

## Category analysis

- **Performance:** Q1 establishes measurements at the Polaris control plane; Q4 prevents unbounded queuing and global serialization.
- **Reliability:** Q2 sets behavior when credential refresh fails; Q3 distinguishes safe reads from ambiguous writes; dependency timeouts fail closed.
- **Security:** Preserve validated user identity and exact location scope across refresh; never use root/bootstrap/static storage credentials in Spark.
- **Observability:** Q1/Q5 use existing Polaris service facilities and safe structured events without adding a new monitoring dependency or exposing high-cardinality identity data.
- **Compatibility:** Exact configuration keys, management metric names, RustFS STS timeout/pool controls, and Spark/Iceberg retry/refresh behavior must be confirmed against the pinned versions before implementation.
- **Logical components:** Spark/Iceberg REST client, Polaris authentication/authorization path, Polaris credential manager/cache, RustFS STS endpoint, and Polaris management metrics/logging. No separate policy or credential service is proposed.

## Next gate

The user approved all five recommendations. The NFR patterns and logical components are recorded in `aidlc-docs/current/construction/unit-3/nfr-design/` and await review. The 900-second duration, 600-second cache, management metric availability, credential refresh support, and retry behavior remain subject to pinned-version verification. No application code, provider configuration, grants, buckets, containers, or runtime data have been changed.
