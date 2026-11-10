# Unit 2 NFR Requirements — Hub Token Broker and Spark Session Identity

## Scope and inherited limits

- One local JupyterHub instance with at most two active user servers.
- Up to two users may request broker tokens concurrently. Refreshes are serialized per user; different users must not block one another.
- One request is made before each Spark session. A still-valid access token is reused only when more than 60 seconds remain; otherwise refresh is required.
- Access tokens remain short-lived under the existing Keycloak 300-second human-token policy. No extension to token lifetime is introduced.
- Multi-Hub high availability, distributed broker workers/locks, public exposure, Polaris role enforcement, and RustFS credential vending are outside Unit 2.

## Performance and capacity

1. Under normal local conditions, a token-reuse broker response should complete within 2 seconds.
2. Under normal local conditions, a successful Keycloak refresh and broker response should complete within 5 seconds. The Keycloak refresh request has a hard 5-second timeout; its timeout may produce a fail-closed response within bounded processing time.
3. The Hub must allow requests for both admitted users to proceed concurrently. A refresh for one user must not serialize another user's request.
4. Same-user refreshes must share one in-flight refresh outcome. Waiting requests must re-read state and reuse the refreshed token rather than replaying the old refresh token.
5. The supported ceiling is inherited from Unit 1: two active user servers and one Hub process. No higher-scale claim is made.

## Reliability and failure handling

- If a refresh request times out, do not automatically replay the refresh token. Re-read that user's auth state once to detect an already persisted successful rotation; if no sufficiently valid token exists, deny Spark startup and require user reauthentication.
- A timeout, Keycloak outage, revoked/expired refresh state, Hub state failure, invalid server binding, or malformed response fails closed. Never use a stale token or shared service identity.
- Broker and Spark launcher errors must identify a safe failure class and correlation ID without returning upstream response bodies or credential values.
- A running Spark session does not automatically change identity or renew its JWT; expiry can fail authenticated Polaris operations. A new session repeats broker acquisition.
- Group revocation is observed at Hub/Keycloak revalidation or refresh. Instant revocation is not guaranteed; the Unit 1 operator-stop fallback remains in force.

## Security and privacy

1. Use HTTPS for every single-user-server-to-Hub-broker request. The user image must validate a Hub certificate whose trust chain and service identity match the broker endpoint.
2. The HTTPS listener/certificate delivery must not widen the user container's network access to Keycloak, PostgreSQL, Docker Engine, or Hub administrative services. Implementation detail belongs to Unit 2 Infrastructure Design.
3. Hub API tokens and Keycloak access JWTs are bearer credentials. Send them only in authorization headers; never in URLs, query strings, command-line arguments, logs, notebook outputs, persistent Spark settings, or user-home files.
4. Refresh tokens and the OAuth client secret remain in encrypted Hub auth state and Hub-only protected configuration. They never enter a user container or broker response.
5. Broker authorization is derived exclusively from a valid Hub-issued server API token and Hub state. A user container cannot choose the username, subject, role, or server identity.
6. Continue the existing 60-second minimum remaining lifetime rule before returning a token for new Spark startup.
7. Avoid sensitive or unbounded metric labels. Do not label metrics with user subjects, usernames, token IDs, or correlation IDs.

## Observability

Record aggregate request counts, latency, outcome class, whether a token was reused/refreshed, and a correlation ID in safe structured diagnostics. Include validated user/server identifiers only in appropriately protected Hub logs if needed for audit; never include authorization headers or token values. Metrics should use bounded labels such as outcome and token decision only.

## Operational and maintenance constraints

- Use the existing Hub process, encrypted auth-state store, and Keycloak token endpoint; add no database, queue, or distributed lock service.
- Per-user refresh coordination may be process-local because the approved profile has a single Hub process. If deployment later adds Hub replicas, distributed coordination becomes a design requirement before scaling.
- Internal broker certificate provisioning, trust distribution, and rotation must be documented and validated before the integration is enabled.
- Verify response latency and concurrent behavior through focused tests; the targets are requirements, not test results.
