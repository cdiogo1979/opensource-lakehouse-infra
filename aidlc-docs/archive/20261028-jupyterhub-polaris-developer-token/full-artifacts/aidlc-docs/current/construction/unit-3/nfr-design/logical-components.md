# Unit 3 Logical Components — NFR Design

## Logical component inventory

| Component | State / responsibility | Protection and lifecycle |
|---|---|---|
| Spark/Iceberg REST client | Sends the exact user's Keycloak JWT to Polaris for catalog requests; receives temporary credentials and refresh metadata. | Credentials stay in transient client state; pinned Iceberg refresh and retry behavior must be verified. No root/bootstrap storage keys. |
| Polaris request authentication | Validates JWT signature, issuer, expiry, audience, principal, and allow-listed role claims. | Denies malformed or unapproved identities before resource processing; no alternate service identity. |
| Polaris authorization evaluator | Applies role, operation, catalog/environment, and resolved table-location grants. | Preserves developer dev-only mutation and analyst production-read-only boundaries. Denials cannot trigger credential vending. |
| Polaris credential manager/cache | Issues temporary location-scoped RustFS credentials after an allow decision and caches only within approved validity/scope rules. | User-approved 3600-second credential duration and <=600-second cache, conditional on pinned-version verification; cache entries cannot cross principal/resource scopes. |
| Polaris-to-RustFS STS client | Requests scoped temporary credentials for authorized object operations. | Bounded connection pool and request timeouts; no unbounded queue, ambient-root fallback, or expanded policy on failure. |
| Iceberg credential refresh path | Obtains refreshed credentials through the Polaris REST refresh contract before expiration. | Uses the same user JWT and resource context; fails closed if the pinned client/protocol cannot renew safely. |
| Retry boundary | Distinguishes safe idempotent reads from mutations with possible ambiguous outcomes. | At most one bounded retry for safe reads; no automatic mutation replay or identity substitution. |
| Polaris management metrics and logs | Measures authorization and credential-vending durations and records safe decision events. | Internal management surface; bounded aggregate labels; protected logs exclude JWTs, temporary credentials, secrets, query text, and request bodies. |

## Authorization and credential-vending flow

```mermaid
sequenceDiagram
  participant S as Spark / Iceberg client
  participant P as Polaris REST and JWT validation
  participant A as Polaris authorization evaluator
  participant C as Polaris credential manager/cache
  participant R as RustFS STS
  participant O as RustFS object API
  participant M as Polaris management metrics/logs
  S->>P: Catalog request + user's Bearer JWT
  P->>P: Validate signature, issuer, expiry, audience, principal, roles
  P->>A: Evaluate operation and trusted resource/location
  A-->>P: Allow or deny
  P->>M: Record bounded outcome and latency
  alt Denied
    P-->>S: Safe authorization failure; no storage credentials
  else Allowed object operation
    P->>C: Request scoped temporary credentials
    C->>R: Bounded STS request for authorized location
    R-->>C: Temporary scoped credentials and expiry
    C-->>P: Vended credentials and refresh metadata
    P-->>S: Catalog response and temporary credential properties
    S->>O: Direct object request using vended credentials
    O-->>S: Object response or bounded storage failure
    S->>P: Refresh request before expiry with same user JWT/context
    P->>A: Reauthorize same principal/resource
    A-->>P: Allow or deny
    P-->>S: New scoped credentials or fail-closed response
  end
```

## Trust and resource boundaries

- **Identity:** Keycloak issues the user token; Polaris validates the canonical issuer, explicit audience, and approved role claims. The Spark client cannot provide a replacement username or role.
- **Authorization:** Polaris is the sole catalog authorization decision point. The approved catalog grants and resolved table locations determine whether credentials can be issued.
- **Object storage:** Spark connects directly to RustFS only with the temporary credential response for its authorized object operation. Root/bootstrap credentials remain outside user containers.
- **Metrics and logs:** Management telemetry is separated from the data path. Aggregate metrics contain bounded labels; detailed logs contain validated identity only under the existing operator access boundary.
- **Concurrency:** Each user's request has independent bounded processing; there is no global authorization lock. Polaris/RustFS pool saturation ends in bounded failure.

## Failure and observability behavior

1. Invalid identity or denied authorization returns a safe failure before credential vending; record the result without token material.
2. RustFS STS timeout or vending failure fails the request within the configured bound. No broader credential or static-key path is attempted.
3. Credential refresh is reauthorized under the same identity and resource scope. Unsupported or failed refresh fails the affected operation.
4. Safe reads may retry once within a bounded request deadline. An ambiguous mutation is not replayed automatically and is reported for reconciliation.
5. Metrics capture separate control-plane latency and credential-vending latency where supported. If pinned Polaris metrics cannot distinguish them, document the gap before choosing instrumentation in Infrastructure Design.

## Design decisions deferred

Unit 3 Infrastructure Design selects exact Polaris property names, runtime configuration mounts, STS/request timeout values, management endpoint network exposure, and any required metric/log wiring. Code Generation verifies the exact pinned-client refresh and retry interfaces. No deployment or provider state is changed by this logical design.
