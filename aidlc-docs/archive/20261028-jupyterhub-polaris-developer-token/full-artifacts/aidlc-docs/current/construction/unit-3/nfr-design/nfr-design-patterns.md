# Unit 3 NFR Design Patterns — Polaris Authorization and RustFS Credential Vending

## Scope and approved targets

This design covers the Polaris control plane for one local Compose deployment with at most two admitted users. It preserves the approved roles and grants: developers read all environments and mutate dev only; analysts read production only and do not mutate. Unit 4 owns full login-to-RustFS journey verification.

Approved requirements are p95 <= 1 second for Polaris authorization/metadata requests and p95 <= 5 seconds for requests requiring credential vending, excluding query execution and RustFS object transfer; vended credentials target 3600 seconds with a cache target of 600 seconds; at least two users can make progress concurrently; safe reads may receive one bounded retry, while ambiguous mutations are not replayed.

## Authorization request and measurement pattern

- Spark presents the Unit 2 user's exact JWT to Polaris REST. Polaris validates signature, canonical issuer, expiry, explicit `polaris` audience, principal mapping, and allow-listed role claims before authorizing the requested catalog action.
- Polaris evaluates the approved operation matrix and trusted catalog/table location before it returns metadata or issues storage credentials. A denial terminates the request before credential vending.
- Use the existing Polaris management metrics/health surface and structured service logs. Observe control-plane request duration and credential-vending duration separately so S3 data transfer and query execution do not distort the p95 values.
- Keep management endpoints internal to the approved service network. Do not add a Prometheus server or expose an additional host/user-facing metrics endpoint in this unit.
- Validate that the pinned Polaris image exposes metrics with enough distinction for the two targets. If it does not, record the gap and choose a reviewed instrumentation approach during Infrastructure Design rather than claiming the target is measurable.

## Vended credential lifetime, cache, and refresh

- Configure the pinned Polaris deployment for a 3600-second vended-credential duration and a 600-second-or-shorter credential cache only after verifying the exact configuration keys and runtime behavior for Polaris 1.8.0 and RustFS 1.0.4.
- Polaris remains the only credential issuer. It scopes each response to the authorized catalog/table location and operation. Cache reuse must not widen the scope or cross principals.
- Spark/Iceberg uses the REST credential-refresh protocol before expiry when the pinned Iceberg 1.8.1 client supports the response and refresh contract. Refresh uses the same user's JWT and re-evaluates the current Polaris authorization for the same resource.
- If refresh is unavailable, rejected, late, or cannot preserve principal/resource scope, fail the affected operation and require a new Spark session when needed. No static, root, bootstrap, or shared-writer key fallback is permitted.
- Keep credentials in the requesting Spark process's transient client state only. Redact access key, secret key, session token, JWT, and refresh response content from all diagnostics.

## Retry and ambiguous outcome pattern

- Allow at most one bounded retry at the client/request boundary for an idempotent Polaris read after a transient transport failure.
- Do not retry an authentication or authorization denial as a different user, role, catalog, or location.
- Do not automatically replay a mutation if a timeout leaves its outcome ambiguous. Return a safe outcome-unknown error and require inspection/reconciliation before manual retry.
- Inspect Spark/Iceberg REST and task retry behavior during implementation. Configure or wrap it only as required to preserve the safe-read-only retry boundary; do not assume defaults comply.
- RustFS failures do not broaden location scope or cause use of ambient/root storage credentials.

## Concurrency and bounded work

- Authorization and credential-vending requests from two distinct users remain independent; do not introduce a global lock.
- Use bounded connection pools, request/connection timeouts, and bounded in-flight work for Polaris-to-RustFS STS interactions. Avoid an unbounded application queue.
- Dependency saturation fails within a bounded deadline using a safe error category. It does not result in authorization bypass or broader credentials.
- The design makes no claim beyond the approved two-user local profile. Multi-instance coordination or higher capacity requires a separate design before scaling.

## Observability and privacy

- Emit protected structured decision logs with correlation ID, validated principal, approved role names, catalog/environment, operation class, decision, latency, and safe failure category.
- Emit aggregate request counts and latency through existing Polaris management metrics where supported. Labels are bounded to outcome, operation class, and environment; exclude username, subject, token ID, correlation ID, table name, JWT, storage credential, and query content.
- Distinguish token/claim rejection, authorization denial, credential-vending failure, refresh failure, timeout, and RustFS rejection without recording sensitive request/response bodies.
- Keep management metrics private to the service network and restrict logs under the existing operator access boundary. Do not add a new metrics backend in this unit.

## Failure containment

| Failure | Response |
|---|---|
| Invalid/expired JWT, wrong issuer/audience, unresolved principal, or missing role | Reject the Polaris request; do not vend credentials. |
| Operation or location is outside role grants | Deny before credential vending; do not reveal unauthorized catalog/namespace information. |
| Polaris or RustFS STS dependency is unavailable | Fail closed within configured timeouts; no shared identity or static-key fallback. |
| Credential refresh fails or expires | Fail the affected operation; require a new Spark session if a fresh authorization token is needed. |
| Ambiguous mutation timeout | Do not replay automatically; return an outcome-unknown error for reconciliation. |
| Metrics endpoint unavailable | Continue authorization without exposing a data-plane endpoint; use safe service logs and report the observability gap. |

## Compatibility gates

Before implementation claims these patterns are supported, verify the exact Polaris duration/cache properties, RustFS STS duration/scope behavior, Iceberg REST credential refresh in Iceberg 1.8.1, Spark retry behavior, and Polaris metric names/labels against the pinned images. Incompatibility is a design finding; it must not be hidden by weakening least privilege or adding long-lived storage credentials.
