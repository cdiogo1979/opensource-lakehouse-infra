# User Stories — JupyterHub Developer and Analyst Access

Stories use the approved user-journey hybrid: shared identity/session outcomes, followed by role-specific access. Acceptance criteria are numbered business rules, as selected in the story-planning answers.

## US-01 — Sign in with an approved Keycloak role

**Story:** As a developer or analyst, I want to sign in to JupyterHub through Keycloak so that my lakehouse access is tied to my individual identity and approved role.

**Acceptance criteria**

1. JupyterHub uses browser-based OIDC Authorization Code flow with the configured Keycloak `lakehouse` realm and registered callback.
2. A user in `role-default-developer` or `role-default-analyst` can complete sign-in and is associated with the correct role.
3. A user in neither approved group is denied access and cannot spawn a user environment.
4. JupyterHub does not collect the user's Keycloak password or use the Resource Owner Password grant.

**Traceability:** FR-1, FR-2; Requirements AC 1–2.

## US-02 — Work in an isolated personal environment

**Story:** As an admitted user, I want my Jupyter and Spark environment isolated from other users so that I can work without accessing another user's runtime or credentials.

**Acceptance criteria**

1. Each admitted user receives a separate Jupyter single-user server and Spark client/driver environment.
2. The user container does not have access to the Docker socket.
3. A user cannot read another user's token or runtime state through the supported container and volume configuration.
4. Hub-side OAuth token state is encrypted at rest; bearer and refresh tokens do not appear in logs, image layers, notebook outputs, or persistent shared files.

**Traceability:** FR-7; Requirements AC 3, 8.

## US-03 — Start Spark with my current identity

**Story:** As an admitted user, I want each Spark session to authenticate to Polaris as me so that Polaris applies my current role grants.

**Acceptance criteria**

1. Before a Spark session starts, its launcher authenticates to the Hub token broker as the requesting user's own JupyterHub server.
2. The broker refreshes only the matching user's Keycloak session and returns only that user's current access-token JWT.
3. The user's refresh token remains in encrypted Hub auth state and is never returned to the container.
4. Spark sends the exact returned JWT as a Bearer token to Polaris; it is not replaced with the shared writer or bootstrap identity.
5. The broker rejects missing, invalid, expired, or cross-user server credentials and fails closed if the user session cannot be refreshed.
6. If the JWT expires during a Spark session, an authenticated Polaris request fails safely; a later Spark session must obtain a fresh token without changing the user identity.

**Traceability:** FR-3, FR-4; NFR Token lifecycle and Availability; Requirements AC 3–4, 7.

## US-04 — Develop across environments with dev-only writes

**Story:** As a developer, I want to read approved data across production, UAT, and development while writing only to development so that I can build and validate data products without changing protected environments.

**Acceptance criteria**

1. Polaris recognizes the Keycloak principal and `role-default-developer` role from a token with the approved issuer and `polaris` audience.
2. Spark can read the approved production, UAT, and development catalogs and paths.
3. Spark can write to approved development paths.
4. Attempts to write production or UAT paths are denied by Polaris/storage authorization.
5. Successful object-store access uses temporary credentials vended by Polaris and scoped to the authorized location.

**Traceability:** FR-4, FR-5, FR-6; Requirements AC 4–6.

## US-05 — Analyze production data without write access

**Story:** As an analyst, I want to query approved production data without write access so that analysis cannot alter protected data or read non-production environments.

**Acceptance criteria**

1. Polaris recognizes the Keycloak principal and `role-default-analyst` role from a token with the approved issuer and `polaris` audience.
2. Spark can read approved production catalogs and paths.
3. Attempts to read UAT or development data are denied.
4. Attempts to write any environment are denied.
5. Successful object-store reads use temporary credentials vended by Polaris and scoped to the authorized production location.

**Traceability:** FR-2, FR-4, FR-5, FR-6; Requirements AC 4–6.

## US-06 — Operate access without exposing credentials

**Story:** As a platform operator, I want to configure role admission and diagnose access issues without seeing bearer tokens so that the service remains supportable while user credentials stay private.

**Acceptance criteria**

1. The operator can configure the Keycloak client, JupyterHub callback, approved group admission, and supported user environment.
2. The token broker binds each request to the authenticated JupyterHub server identity and does not trust a username supplied by the user container.
3. If Keycloak is unavailable or a session is revoked, new logins and token refreshes fail closed.
4. Logs can identify the user, service, and authorization outcome without recording access-token or refresh-token values.
5. The operator can distinguish authentication failure, token refresh failure, Polaris denial, and object-store access failure without retrieving a user's token.

**Traceability:** FR-1, FR-2, FR-3, FR-7; NFR Security, Availability, Auditability; Requirements AC 2–3, 7–8.

## Story coverage

| Persona | Stories |
|---|---|
| Platform Operator | US-01, US-02, US-03, US-06 |
| Developer | US-01, US-02, US-03, US-04 |
| Analyst | US-01, US-02, US-03, US-05 |

The story set contains six independently reviewable outcomes. Each has a clear user value and observable acceptance criteria; the stories can be estimated and tested separately while preserving the shared authentication journey.
