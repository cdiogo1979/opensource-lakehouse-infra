# Unit 2 Functional Design Plan — Hub Token Broker and Spark Session Identity

## Purpose

Define the user-identity lifecycle from a JupyterHub single-user server's broker request through token renewal and Spark session startup. This design covers business behavior and failure rules; technology-specific route, authenticator, and Spark API choices remain for later design stages.

## Unit context

- **Unit**: Unit 2 — Hub token broker and Spark session identity, from `aidlc-docs/current/inception/application-design/unit-of-work.md`.
- **Stories**: US-03 and the Unit 2 responsibilities of US-06 in `unit-of-work-story-map.md`.
- **Requirements**: FR-3 and FR-4 client handoff in `requirements/requirements.md`; token lifecycle, identity isolation, confidentiality, and fail-closed NFRs.
- **Component baseline**: `aidlc-docs/current/inception/application-design/application-design.md` and `component-methods.md`.
- **Unit 1 contract**: JupyterHub stores each user's OIDC token set in encrypted Hub auth state. Each isolated single-user server has its own Hub API token and is bound to one Hub user/server. Only the Hub owns the OAuth client secret and refresh token.
- **Outcome**: Before each Spark session, the user's runtime authenticates to the Hub broker with its Hub API token. The broker derives the caller's user/server binding from Hub state, refreshes only that user's Keycloak state as needed, and returns only that user's current access JWT. Spark uses that exact JWT as the Polaris Bearer token.
- **Boundary**: No refresh token or client secret leaves the Hub. No caller-supplied username, subject, role, or server identity is trusted. Polaris authorization and RustFS credential vending are Unit 3; end-to-end journeys are Unit 4.

## Functional design work plan

- [x] Model broker request authentication and derive the bound user/server identity from Hub-owned state.
- [x] Model access-token freshness, refresh-token use, expiry, concurrent Spark starts, and per-user refresh serialization.
- [x] Define the token response and Spark-session initialization lifecycle, including exact-token handoff and non-persistence.
- [x] Define denial, Keycloak outage, revoked/expired refresh state, malformed caller, and broker retry behavior.
- [x] Define audit/correlation behavior while excluding access tokens, refresh tokens, and client secrets.
- [x] Generate business logic, rules, and domain entity artifacts for Unit 2.
- [x] Validate traceability to US-03, US-06, FR-3, FR-4 client handoff, and approved application design.

## Clarification questions

### Q1 — Access-token freshness at Spark session start

The broker is called before each Spark session, but a still-valid access token may already be in the user's encrypted Hub auth state. Should it reuse that token or force a Keycloak refresh for every new session?

A) Reuse the current token when it has more than 60 seconds remaining; refresh when it is expired or within 60 seconds of expiry (Recommended; avoids unnecessary refreshes while ensuring usable lifetime).

B) Force a Keycloak refresh for every Spark session.

C) Other policy (please specify).

[Answer]: A — Reuse when more than 60 seconds remain; otherwise refresh.

### Q2 — Concurrent session starts for one user

Two Spark sessions from the same user's server could ask the broker for a token at the same time. How should the Hub handle a refresh-token race?

A) Serialize refresh per Hub user and share the resulting current access token with concurrent callers (Recommended; avoids parallel use of a rotating refresh token).

B) Allow independent concurrent refresh calls and return each successful result.

C) Other policy (please specify).

[Answer]: A — Serialize refresh per Hub user and share the resulting current access token with concurrent callers.

## Category analysis

- **Business workflow**: Spark start → authenticated broker call → Hub-derived server/user binding → token validity/refresh → access-token response → in-memory Spark setup.
- **Entities**: Hub user, single-user server, Hub API token, encrypted OIDC token state, access token, refresh attempt, and Spark session.
- **Business rules**: One server token can access only its owning user's current auth state; user identity and roles are never accepted from request fields; broker returns no refresh token; failure denies new session creation.
- **Data flow**: Hub API token flows from the user's server to the broker in an authorization header; the access JWT flows back only to that server and into the Spark runtime; secrets are excluded from logs, command arguments, persistent files, and notebook output.
- **Integration points**: Hub authenticator state and API token validation, Keycloak token refresh, single-user server launcher, Spark REST catalog client.
- **Failure handling**: Invalid/revoked Hub token, cross-server mismatch, unavailable Keycloak, failed refresh, expired resulting JWT, and malformed broker response all fail closed. No stale-token or shared-service-identity fallback is permitted.
- **Concurrency and edge cases**: Q1/Q2 resolve refresh freshness and same-user races. A running Spark session retains its session-start identity; it does not silently change identity after expiry.
- **Frontend**: No custom UI; report a safe, actionable Spark-start failure without token details.

## Answer analysis and next gate

Both answers are specific and consistent with the approved token lifecycle. On a refresh path, the Hub serializes by user and re-reads auth state after acquiring the per-user lock so waiting requests can use the token produced by the first successful refresh. The functional design artifacts are generated below and await review. No Unit 2 code or runtime state has been changed.
