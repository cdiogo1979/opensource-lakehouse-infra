# Unit 2 NFR Design Plan — Hub Token Broker and Spark Session Identity

## Purpose

Translate approved Unit 2 NFR requirements into concrete resilience, capacity, performance, security, and observability patterns for the local single-Hub profile. This plan resolves the remaining TLS endpoint, certificate lifecycle, and metrics implementation choices before generating NFR design artifacts.

## Inputs

- `aidlc-docs/current/construction/unit-2/nfr-requirements/nfr-requirements.md`
- `aidlc-docs/current/construction/unit-2/nfr-requirements/tech-stack-decisions.md`
- `aidlc-docs/current/construction/unit-2/functional-design/`
- `aidlc-docs/current/construction/unit-1/infrastructure-design/`
- `aidlc-docs/current/inception/application-design/`

## NFR design work plan

- [x] Select a topology for serving the broker over internal HTTPS without changing browser ingress.
- [x] Define certificate creation, trust distribution, storage, and rotation patterns.
- [x] Define per-user refresh coordination lifecycle, bounded concurrency, and timeout recovery.
- [x] Select an observability pattern for counts, latency, outcome, token decision, and correlation without exposing bearer data.
- [x] Validate the designs against the two-user capacity, five-second Keycloak timeout, fail-closed rules, and current network boundaries.
- [x] Generate `nfr-design-patterns.md` and `logical-components.md` after clarification answers are resolved.

## Clarification questions

### Q1 — Internal HTTPS broker endpoint

The broker must remain an in-process JupyterHub extension and use HTTPS for user-server requests. How should the Hub expose that endpoint?

A) Add a dedicated internal TLS listener in the Hub process for the broker, bound only to the Docker user-server network; keep browser ingress and the existing Hub API listener unchanged (Recommended; preserves the in-process broker design without another service).

B) Add a small TLS reverse-proxy sidecar in front of the broker route (adds a separately managed component).

C) Other topology (please specify).

[Answer]: A — Dedicated in-process TLS listener on the user-server network; leave browser ingress and the Hub API listener unchanged.

### Q2 — Internal certificate lifecycle

How should the broker certificate be issued and trusted by the isolated user servers?

A) Generate a local internal CA and a Hub server certificate during protected runtime preparation. Keep the CA private key outside containers after issuance, mount the Hub certificate/key read-only to the Hub, and distribute only the CA certificate read-only to user servers. Include the internal broker DNS name in the server certificate SAN; rotate with an explicit preparation command and restart affected containers (Recommended; local-only trust, no public CA dependency).

B) Use a self-signed server certificate and disable client certificate verification (not recommended; does not authenticate the endpoint).

C) Other certificate lifecycle (please specify).

[Answer]: A — Generate an internal CA and Hub server certificate during protected runtime preparation; keep the CA key on the protected host, mount the server key/certificate read-only into Hub, distribute only the CA certificate to user servers, require broker DNS SAN validation, and rotate explicitly with container restarts.

### Q3 — Broker observability implementation

Which implementation should retain the required aggregate request counts, latency, outcome class, reuse/refresh decision, and correlation ID?

A) Emit token-safe structured Hub logs and process-local aggregate counters; do not add a public or user-server-reachable metrics endpoint. Counters reset on Hub restart, while logs remain the operational record (Recommended; meets the local diagnostic need without another exposed interface).

B) Add a Prometheus-compatible endpoint protected by Hub administration authentication (adds a scrape interface and access-control surface).

C) Other observability pattern (please specify).

[Answer]: A — Token-safe structured Hub logs and process-local aggregate counters; no user-server-reachable metrics endpoint.

## Category analysis

- **Resilience:** Inherit a single Hub process and no HA/SLA. A Keycloak timeout is bounded to five seconds, is not automatically replayed, triggers one auth-state reread, and then fails closed if no valid token exists. No circuit breaker or distributed retry service is proposed for the two-user local profile.
- **Scalability:** Support two active user servers. Use one independent asynchronous refresh lock per Hub user; requests for different users proceed concurrently. Re-read Hub auth state after lock acquisition. Keep lock state process-local and clean idle entries without introducing a distributed coordinator.
- **Performance:** Reuse responses target two seconds; successful refresh responses target five seconds under normal local conditions. Bound upstream requests and avoid serialization except for concurrent refreshes by the same user.
- **Security:** Preserve the Hub/user/data-access network separation, server-token-derived identity, Hub-only refresh state and OAuth secret, exact access-token handoff, HTTPS certificate validation, and token-free logs/labels. Do not alter browser-facing loopback ingress.
- **Logical components:** Hub broker handler and internal HTTPS listener, Hub auth-state/refresh coordinator, Keycloak token endpoint, Spark launcher/client, runtime certificate preparation, user-server trust material, and safe Hub diagnostics. No new database, queue, or service is presumed.
- **Operational boundary:** This stage selects patterns. Internal ports, Compose wiring, mounted paths, and executable certificate commands belong to Unit 2 Infrastructure Design.

## Next gate

The user's three A selections are specific and consistent with the approved single-Hub design. The design preserves the existing user-server/data-access network split, protects bearer traffic with verified TLS, keeps refresh coordination process-local and per user, and limits diagnostics to safe logs and counters. Artifacts are generated for review. No code or runtime state was changed.
