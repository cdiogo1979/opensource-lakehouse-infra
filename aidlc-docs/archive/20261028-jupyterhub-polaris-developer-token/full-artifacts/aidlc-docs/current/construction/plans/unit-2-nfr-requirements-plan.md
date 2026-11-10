# Unit 2 NFR Requirements Plan — Hub Token Broker and Spark Session Identity

## Purpose

Set measurable performance, reliability, security, capacity, and implementation constraints for the Unit 2 Hub broker and Spark token handoff. This plan inherits the approved local Compose profile, single JupyterHub instance, two-user capacity, SQLite Hub state, Keycloak 300-second access tokens, per-user refresh serialization, and fail-closed behavior.

## Unit context

- **Functional design**: `aidlc-docs/current/construction/unit-2/functional-design/`.
- **Stories and requirements**: US-03, Unit 2 part of US-06, FR-3, and the FR-4 Spark-to-Polaris handoff.
- **Trust boundary**: Hub API tokens and user access JWTs cross between isolated user servers and Hub broker; refresh tokens and OAuth client secret remain in Hub-owned encrypted state.
- **Inherited deployment**: Local Compose; one Hub instance; at most two active user servers; broker and Spark run on the approved Hub/user networks. Unit 1 verification gaps were explicitly waived and are not treated as passing.
- **Out of scope**: Polaris policy and RustFS credential vending (Unit 3), cross-service E2E acceptance (Unit 4), public TLS exposure, and multi-Hub high availability. Internal HTTPS for the broker is in scope.

## NFR assessment work plan

- [x] Set broker response latency and Keycloak refresh latency targets.
- [x] Confirm concurrent caller capacity and same-user refresh behavior under the inherited two-server limit.
- [x] Define broker, Keycloak, and refresh-operation timeouts and retry rules, including ambiguous refresh timeout behavior.
- [x] Define confidentiality/integrity protection for bearer-token traffic between user servers and Hub.
- [x] Define minimum token lifetime on return and safe behavior near the 300-second Keycloak expiry.
- [x] Define operational metrics, correlation, and redaction requirements.
- [x] Record supported runtime/dependency constraints without inventing an HA or distributed-locking requirement.
- [x] Generate `nfr-requirements.md` and `tech-stack-decisions.md`; validate against Unit 2 functional design and assigned stories/requirements.

## Clarification questions

### Q1 — Broker latency target

What response targets should the Spark launcher expect from the Hub broker?

A) Return a reusable token within 2 seconds and complete a Keycloak refresh within 5 seconds under normal local conditions (Recommended; preserves reasonable startup time while allowing a back-channel refresh).

B) Use a single 5-second target for both paths.

C) Other targets (please specify).

[Answer]: A — Reuse within 2 seconds; Keycloak refresh within 5 seconds under normal local conditions.

### Q2 — Caller capacity

Unit 1 permits at most two active user servers. How much simultaneous broker activity should Unit 2 support?

A) Support both users concurrently, serialize refresh only per user, and allow same-user callers to wait behind one refresh (Recommended; matches the approved local capacity).

B) Permit one broker request globally at a time.

C) Other capacity target (please specify).

[Answer]: A — Support both users concurrently; serialize refresh only per user.

### Q3 — Timeouts and ambiguous Keycloak refresh outcome

If a refresh request times out, Keycloak may already have consumed/rotated the refresh token. What should the broker do?

A) Use a bounded 5-second Keycloak timeout, do not replay the refresh automatically, re-read Hub auth state once in case a result was persisted, then fail closed and require reauthentication if no valid new state exists (Recommended; avoids refresh-token replay/rotation races).

B) Retry the refresh request once with the same refresh token.

C) Other timeout/recovery policy (please specify).

[Answer]: A — Use a 5-second Keycloak timeout, do not replay automatically, reread auth state once, then fail closed and require reauthentication if no new valid state exists.

### Q4 — Broker transport protection

The broker carries a Hub API bearer token and returns a Keycloak access JWT over the user-server network. Which transport protection should apply in the local Compose profile?

A) Use HTTPS for broker traffic with a Hub certificate trusted by the user image (Recommended; protects bearer tokens from other containers on the shared bridge).

B) Keep HTTP on the private Docker bridge and rely on the current local network isolation.

C) Other protection (please specify).

[Answer]: A — Require HTTPS for broker traffic and trust the Hub certificate in the user image.

### Q5 — Operational measurements

What broker observability should be retained?

A) Record request counts, latency, success/denial class, refresh/reuse decision, and correlation ID without token values or authorization headers (Recommended; supports diagnosis without exposing credentials).

B) Logs only; no metrics.

C) Other requirement (please specify).

[Answer]: A — Record request counts, latency, success/denial class, reuse/refresh decision, and correlation ID without credentials.

## Category analysis

- **Scalability**: Inherit two active user servers and one Hub instance; no distributed broker or multi-instance coordination is in scope.
- **Performance**: Q1 sets the latency budget for the cache/reuse and refresh path; Q3 bounds upstream calls.
- **Availability/reliability**: Keycloak failure prevents new Spark session startup; refresh token rotation must not be retried unsafely.
- **Security**: Q4 resolves protection for bearer-token traffic; token/state isolation, encryption, fail-closed identity binding, and redaction are inherited requirements.
- **Tech stack**: Keep the broker inside the existing Hub process and use Hub-owned state/locks unless an answer requires a justified change. No new database, queue, or shared service is proposed.
- **Maintainability/operations**: Q5 defines safe measurements and diagnostic fields.
- **Usability**: Broker failures must produce actionable non-secret Spark-start errors within the selected latency budget.

## Answer analysis and next gate

The user instructed us to use all five recommendations. They are consistent with the approved two-user single-Hub profile and fail-closed token lifecycle. Internal HTTPS is required only on the user-server-to-broker path; the approved loopback browser HTTP entry point remains a separate ingress decision. The NFR artifacts are generated below and await review. No Unit 2 code or runtime state has been changed.
