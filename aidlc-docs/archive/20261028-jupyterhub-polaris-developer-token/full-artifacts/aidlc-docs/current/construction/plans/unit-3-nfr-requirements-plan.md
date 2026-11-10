# Unit 3 NFR Requirements Plan — Polaris Authorization and RustFS Credential Vending

## Purpose

Set measurable performance, reliability, security, capacity, and operational requirements for Polaris authorization and short-lived RustFS credentials vended to Spark. This plan inherits Unit 3's approved role matrix, dual-role union behavior, complete developer dev-only mutation scope, role-aligned catalog discovery, and fail-closed credential handling.

## Unit context

- **Functional design:** `aidlc-docs/current/construction/unit-3/functional-design/`.
- **Stories and requirements:** US-04, US-05, Unit 3 responsibilities of US-06, FR-4, FR-5, and FR-6.
- **Trust boundary:** User JWT is presented to Polaris; scoped temporary RustFS credentials are returned to Spark for direct object access. Root/bootstrap storage credentials stay in infrastructure services and never enter user containers.
- **Inherited environment:** One local Compose stack, Polaris 1.8.0, RustFS 1.0.4, Spark 3.5.5 with Iceberg 1.8.1, at most two admitted user servers, three approved catalogs, and existing grants.
- **Out of scope:** Changing role grants/catalogs/buckets, multi-instance high availability, broader Unit 4 end-to-end acceptance, and changing Keycloak's approved 300-second human access-token policy.

## NFR assessment work plan

- [x] Define a measurable Polaris authentication/authorization latency target separate from query and object-store scan time.
- [x] Define RustFS vended credential validity and cache/refresh safety bounds compatible with Polaris, RustFS, and the pinned Iceberg client.
- [x] Define availability, bounded retry, and ambiguous mutation handling without weakening authorization.
- [x] Set concurrent user and request capacity expectations for the approved local profile.
- [x] Define safe authorization audit events, aggregate metrics, and secret-redaction requirements.
- [x] Record dependency/version constraints and identify live verification gaps without claiming compatibility that has not been exercised.
- [x] Generate `nfr-requirements.md` and `tech-stack-decisions.md`; validate against Unit 3 functional design and assigned stories/requirements.

## Clarification questions

### Q1 — Polaris authorization latency

What response target should apply to a Polaris REST authorization/metadata operation, excluding Spark planning, query execution, and RustFS data transfer?

A) Under normal local conditions, p95 at or below 1 second for authorization/metadata requests and p95 at or below 5 seconds for a request that also requires credential vending (Recommended; separates control-plane latency from object scans while fitting a local two-user stack).

B) Use a single p95 target of 5 seconds for all Polaris REST requests.

C) Other targets (please specify).

[Answer]: A — p95 <=1 second for authorization/metadata requests and p95 <=5 seconds for requests that also require credential vending, under normal local conditions. Query execution and RustFS data transfer are excluded.

### Q2 — Vended credential lifetime and renewal

How short should RustFS credentials be, and what should the Iceberg client do as they approach expiry?

A) Set the Polaris vended-credential duration to 900 seconds and keep its credential cache below that duration (for example, 600 seconds); use the Iceberg REST credential-refresh path supported by the pinned client. If refresh fails, fail the operation and never fall back to static keys (Recommended; uses a short bounded lifetime and leaves refresh headroom).

B) Keep Polaris's default vended-credential duration and use the supported refresh path; fail closed if refresh is unavailable.

C) Other lifetime and refresh policy (please specify).

[Answer]: A — Configure 900-second vended credentials and a cache duration below that (target 600 seconds); use the pinned client's supported Iceberg REST credential refresh. Fail closed if refresh fails; no static keys.

### Q3 — Dependency outages and operation retries

What retry behavior should apply when Polaris or RustFS is temporarily unavailable, especially when a write outcome is ambiguous?

A) Fail closed when authorization or credential vending is unavailable. Permit at most one bounded retry for safe reads; do not automatically replay a mutation after an ambiguous timeout. Spark may report the outcome as unknown and require the user to inspect/reconcile before retrying (Recommended; avoids duplicate or partial mutations under a different authorization context).

B) Let Spark retry all operations using its normal retry policy.

C) Other retry policy (please specify).

[Answer]: A — Fail closed on authorization/vending outages; allow at most one bounded retry for safe reads; never automatically replay an ambiguous mutation.

### Q4 — Supported concurrency

What concurrency should Unit 3 support and verify in the local deployment?

A) At least two distinct users operating concurrently, with authorization requests for one user not globally serializing another user's requests; storage-vending contention may be bounded by Polaris/RustFS (Recommended; matches the approved Hub capacity without claiming production-scale throughput).

B) Serialize all authorization and credential-vending requests through one global operation.

C) Other capacity target (please specify).

[Answer]: A — Support at least two distinct users concurrently without a global authorization-request lock; no higher-scale claim.

### Q5 — Authorization audit and metrics

What operational evidence should be retained for allowed and denied operations?

A) Emit a structured decision event with correlation ID, validated principal, approved role names, resource/environment, operation class, decision, and safe failure category; expose aggregate counts/latency with bounded labels. Never log JWTs, RustFS temporary credentials, client secrets, or notebook/query contents (Recommended; supports investigation without collecting bearer credentials).

B) Emit aggregate counters only; no per-decision event.

C) Other audit/metrics policy (please specify).

[Answer]: A — Emit safe structured decision events and aggregate metrics with bounded labels; exclude tokens, temporary storage credentials, secrets, and query contents.

## Category analysis

- **Performance:** Q1 defines p95 targets for control-plane authorization and the additional credential-vending path; data scan time is not included.
- **Reliability:** Q3 defines fail-closed outage behavior, safe read retry, and ambiguous mutation handling.
- **Security:** Q2 bounds credential exposure and renewal; Q5 restricts logs/metrics to safe diagnostic values.
- **Capacity:** Q4 inherits two user servers and requires independent users to make progress concurrently; no multi-Hub or high-throughput guarantee is introduced.
- **Compatibility:** Polaris credential duration/cache, RustFS STS behavior, and Iceberg REST credential refresh must be confirmed against pinned versions during design and implementation. Any client limitation is recorded explicitly rather than bypassed with long-lived keys.
- **Operations:** Q5 supplies bounded, non-secret evidence for allowed/denied decisions and request health.

## Next gate

The user approved all five recommendations. The approved targets and controls are recorded in `aidlc-docs/current/construction/unit-3/nfr-requirements/nfr-requirements.md` and `tech-stack-decisions.md`; they await review. The 900-second credential validity and 600-second cache are requirements pending pinned-version verification, not live test results. No code, provider configuration, catalog grants, buckets, or runtime services have been changed.
