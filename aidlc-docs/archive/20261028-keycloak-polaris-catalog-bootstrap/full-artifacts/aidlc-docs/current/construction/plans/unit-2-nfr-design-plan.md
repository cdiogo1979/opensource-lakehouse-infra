# Unit 2 NFR Design Plan — Keycloak Identity and Polaris Authorization

## Unit context

U2 implements the identity and catalog-authorization layer for the `default` data product. Approved Functional Design and NFR Requirements make Keycloak the human and writer identity provider, Polaris the catalog authorization authority, and Keycloak product groups the entitlement source. The approved NFRs require a single local issuer, five-minute human access tokens and revocation bound after successful reconciliation, explicit idempotent group-to-Polaris reconciliation, 90-day writer-secret rotation, fail-closed authorization, and credential-safe diagnostics.

This plan defines the patterns and logical components needed to meet those requirements. It does not select exact Compose syntax, service names, URLs beyond the approved issuer, secret filenames, or implementation commands; those belong to Infrastructure Design and Code Generation. It does not authorize runtime identity or catalog mutations.

## Planning checklist

### Analyze approved U2 requirements and design

- [x] Review approved U2 Functional Design artifacts and access matrix.
- [x] Review approved U2 NFR Requirements and Tech Stack Decisions.
- [x] Evaluate resilience, security, token handling, reconciliation, revocation, and logical component needs.
- [x] Preserve the U1 local-only network, protected-file secret handling, and fail-safe persistence boundaries.
- [x] Keep RustFS IAM/policy enforcement in U3 and CLI/Spark end-to-end behavior in U4.

### Plan approval gate

- [x] Collect answers to all NFR Design questions below; the user approved the recommended choices.
- [x] Resolve ambiguity and verify consistency with approved functional/NFR requirements.
- [x] Obtain explicit approval of this completed plan before generating NFR Design artifacts.

### Generate NFR Design artifacts after plan approval

- [x] Generate `aidlc-docs/current/construction/unit-2/nfr-design/nfr-design-patterns.md`.
- [x] Generate `logical-components.md` describing identity, token, reconciliation, and authorization components.
- [x] Map each pattern to U2 NFR requirements and defer concrete service configuration to Infrastructure Design.
- [x] Present both artifacts for explicit NFR Design approval.

## NFR Design questions

Replace each `[Answer]:A` with a selected option or a concrete alternative.

### Question 1 — Polaris bootstrap authentication boundary

Polaris needs a protected setup path for initial principals, catalog roles, and grants, while product-user requests must fail closed and must not use bootstrap credentials. What design boundary should be used?

A) Keep a distinct, protected operator bootstrap credential for explicitly invoked provisioning/reconciliation operations; use Keycloak OIDC only for product-user requests. Store the bootstrap credential in a protected file and never expose it to normal users or Spark jobs (Recommended: separates setup authority from runtime identity).

B) Use Keycloak OIDC for all Polaris operations, including initial provisioning; document a separate first-user bootstrap procedure that does not persist a fallback credential.

C) Other (specify the bootstrap identity, how it is protected, and how user requests are prevented from using it).

[Answer]:A

### Question 2 — Polaris token validation and issuer reachability

The approved issuer is `http://keycloak.localhost:8080/realms/lakehouse`, and a host-issued token must validate in Polaris. Which design should NFR Design apply to discovery/JWKS access?

A) Configure Polaris to validate against that exact issuer and its discovery/JWKS endpoints; provide a Compose-only DNS alias or routing path so Polaris reaches the same issuer, and fail closed if validation metadata cannot be obtained or trusted (Recommended: preserves one `iss` value across host and container contexts).

B) Use a separate internal issuer URL and rewrite or translate host tokens; this requires a documented, verifiable issuer-equivalence mechanism.

C) Other (specify the exact issuer-validation and host/container reachability model).

[Answer]:A

### Question 3 — Group claims and stable principal mapping

Keycloak groups are the entitlement source, while Polaris stores principals and role assignments. How should the design map OIDC identity to Polaris principals and entitlements?

A) Use the configured stable Keycloak username/service-account username as the Polaris principal name, retain the immutable subject as the identity correlation key, and explicitly reconcile approved product-group memberships into Polaris principal-role assignments. Do not authorize from a display name or an assumed group claim alone (Recommended: aligns with Functional Design’s stable-name mapping and makes reconciliation observable).

B) Put group names in access tokens and have Polaris dynamically derive all catalog grants from token claims; define exact claim paths, trust checks, and removal behavior.

C) Other (specify stable principal key, group representation, and grant-resolution mechanism).

[Answer]:A

### Question 4 — Reconciliation transaction and failure handling

Membership reconciliation may involve reading Keycloak and updating Polaris. How should partial failures be handled?

A) Make reconciliation idempotent and convergent: read current approved group membership, validate the complete input, apply only the required Polaris role changes, then verify effective assignments. Return success only after verification; on partial failure report non-convergence and retry safely without broad replacement/deletion (Recommended: aligns with U2-NFR-03/09/10).

B) Replace the full Polaris assignment set on each run; require a transactional API spanning both providers or stop on any unavailable dependency.

C) Other (specify ordering, verification, rollback/retry, and success criteria).

[Answer]:A

### Question 5 — Token cache and revocation mechanics

The approved requirements set a five-minute human access-token maximum and a five-minute post-reconciliation revocation bound. Which control combination should the design use?

A) Cap human token lifetime at five minutes, reject expired tokens, avoid entitlement caches beyond the token lifetime, and verify that Polaris does not continue honoring a removed Polaris assignment; do not claim immediate revocation (Recommended: meets the measured bound without adding a revocation service).

B) Add token introspection or a revocation event mechanism on every request so removal takes effect immediately; specify its behavior during Keycloak outage.

C) Other (specify cache lifetime, revocation mechanism, and maximum stale-access interval).

[Answer]:A

### Question 6 — Keycloak outage and stale authorization

What should happen to human access when Keycloak or its validation metadata is unavailable?

A) Fail closed for product authorization whenever Keycloak is unavailable; do not use cached group membership, stale identity data, or a fallback user identity. Restore access only after Keycloak is healthy and tokens/claims can be validated normally (Recommended: directly enforces approved U2-NFR-06 outage behavior).

B) Deny all product requests whenever Keycloak is unreachable, including locally verifiable unexpired JWTs.

C) Other (specify exactly what can be served from trusted cached material, its maximum age, and failure behavior).

[Answer]:A

### Question 7 — Writer secret rotation overlap

The writer client secret must rotate every 90 days and after suspected exposure, without logging either value. How should a no-downtime local cutover be modeled?

A) Prefer a second temporary writer client during rotation if Keycloak cannot overlap client secrets: provision and verify the replacement identity, switch the protected secret file, verify a fresh token and writer operation, then disable the prior client and remove its secret (Recommended: provides controlled overlap without assuming same-client secret support).

B) Rotate the same client secret in place during a maintenance window; tolerate a brief writer interruption and document the expected failure/recovery behavior.

C) Other (specify overlap, cutover ordering, rollback, and old-secret retirement).

[Answer]:A

### Question 8 — Diagnostics and audit correlation

How should identity and authorization operations be correlated across Keycloak, reconciliation, and Polaris without exposing credentials?

A) Use a generated operation/correlation ID and record safe principal subject/username, product role, catalog, provider, outcome, and failure category where known. Exclude tokens, token claims/payloads, secrets, passwords, and authorization headers; bound local diagnostic retention in the later implementation design (Recommended: traceable while preserving U2-NFR-07).

B) Record provider outcomes only; omit all principal, role, catalog, and operation identifiers.

C) Other (specify safe fields, correlation method, and retention expectation).

[Answer]:A

### Question 9 — Catalog role privilege separation

The approved access matrix gives developers, analysts, product owners, and the writer different privileges across three catalogs. How should the design prevent privilege expansion?

A) Define separate Polaris catalog roles per product/environment as needed, grant only the approved namespace/table privileges, keep grant-management authority separate from content-write privileges, and verify effective inherited grants for all roles (Recommended: makes environment boundaries and privilege review explicit).

B) Use one broad role per persona across all catalogs and rely on application selection to prevent cross-environment operations.

C) Other (specify role granularity, grant-management separation, and inheritance checks).

[Answer]:A

### Question 10 — Identity and catalog recovery consistency

If Keycloak or Polaris restarts or a reconciliation is interrupted, how should consistency be restored?

A) Treat Keycloak groups as the source of truth and Polaris assignments as reconcilable derived state; after provider readiness, rerun the idempotent reconciliation and verify effective roles before reporting completion. Never clear all unrelated assignments or grant broader access as a recovery shortcut (Recommended: converges safely after interruptions).

B) Persist a separate entitlement queue and replay it before enabling product access; define queue ownership, replay order, and poison-event handling.

C) Other (specify durable state, recovery order, and authorization behavior during recovery).

[Answer]:A

## Answer analysis

The user approved the recommended answer for every question. Question 3 follows the approved Functional Design: the stable Keycloak username/service-account username is the Polaris principal name, with immutable subject retained as a correlation key. Question 6 is explicitly fail-closed during Keycloak outage, consistent with U2-NFR-06; access resumes after provider recovery and normal token validation. The bootstrap credential is distinct from user access, reconciliation is additive/idempotent and verified before success, revocation is bounded by five-minute tokens without promising immediate invalidation, writer rotation uses controlled replacement-client overlap if needed, diagnostics are correlated but redacted, catalog grants are least-privilege and separate grant administration, and recovery reruns reconciliation without clearing unrelated state.

## Gate

**Plan status: APPROVED.** The user approved the recommended choices for all ten questions. Both U2 NFR Design artifacts were generated and approved. U2 Infrastructure Design planning may proceed. No code, credentials, runtime identity, catalogs, roles, grants, buckets, or tables were changed by this plan approval.

### Build-and-Test routing refinement (approved 2026-10-28)

Runtime verification showed that `.localhost` resolves to loopback inside the Polaris container. The user approved preserving the canonical issuer `http://keycloak.localhost:8080/realms/lakehouse` while Polaris obtains signing keys from `http://keycloak:8080/realms/lakehouse/protocol/openid-connect/certs` over private Docker service DNS. Polaris discovery is disabled and the canonical issuer is validated explicitly. This refines network routing only; it does not change the issuer contract or authorization design.
