# Application Design — JupyterHub OIDC to Polaris

## Purpose and scope

This design adds browser-authenticated developer and analyst journeys to the existing local Keycloak–Polaris–RustFS lakehouse. It covers Hub authentication, role admission, per-user server lifecycle, a Hub-side token broker, local Spark sessions, Polaris authorization, and RustFS credential vending. It does not implement the services; detailed API and deployment choices belong to Construction.

## Baseline decisions

| Area | Design decision |
|---|---|
| Retain | Keycloak `lakehouse` realm, developer/analyst groups, canonical issuer, `polaris` audience and role claim, Polaris mixed authentication/internal grants and principal reconciliation, RustFS vending, existing catalog grant matrix, and PostgreSQL state. |
| Add | JupyterHub with browser OIDC, encrypted Hub auth state, confidential OIDC client, in-process token-broker extension, per-user isolated Jupyter/Spark server, and individual persistent home volumes. |
| Exclude | FreeIPA, Hive, Ranger, owner/writer JupyterHub journeys, shared Spark cluster, root RustFS access from user containers, and a shared writer identity for human Spark sessions. |

The Hub-side broker is a custom extension/API route in the Hub process. It uses the requesting single-user server's Hub API token to identify the server and user, then refreshes only that user's encrypted Keycloak state. Spark runs in local mode inside that user's isolated container. Each user's home persists in its own named volume. The Hub uses a confidential Keycloak client whose secret is protected runtime configuration. Unit 1 NFR Design selected SQLite on a dedicated persistent Hub volume for Hub state; this supersedes the earlier PostgreSQL dependency mention below. PostgreSQL remains the state store for Keycloak and Polaris.

## Component and service design

Keycloak authenticates users with OIDC Authorization Code flow. The JupyterHub authenticator validates the callback and admits only `role-default-developer` and `role-default-analyst`. The Hub stores token state encrypted at rest and controls the Spawner. Each user receives a separate server container and volume; only the Hub has Docker Engine access.

Before each Spark session, the user launcher calls the Hub token broker with that server's JupyterHub API token. The broker verifies it and derives its user/server binding from Hub state rather than request parameters, refreshes the same user's Keycloak session as needed, and returns only the current access JWT. The refresh token never leaves Hub state. The exact access JWT is passed to Spark at runtime and is not written to logs, images, home volumes, or notebook outputs.

Spark local mode sends the JWT to Polaris as a Bearer token for Iceberg REST. Polaris validates the canonical issuer, signature, expiry, explicit `polaris` audience, username, and allow-listed product roles. It resolves the pre-provisioned principal and applies the existing grants: developers can read production/UAT/dev and write only dev; analysts can read production and cannot write. For authorized object operations, Polaris vends temporary location-scoped RustFS credentials. Spark accesses objects directly with those credentials; user containers have no root/bootstrap storage keys.

The access token lifetime is currently 300 seconds. A Spark session uses the JWT obtained at session start. If an authenticated Polaris request later fails due to token expiry, the session fails safely; a new session obtains a fresh JWT. Keycloak or refresh failures prevent a new Spark session. No shared writer identity or storage-root fallback is allowed.

## Interfaces and dependencies

The key logical contracts are: OIDC `begin_login`/`complete_login`; Authenticator handler registration for the broker; Spawner `prepare_user_server`/`start`; broker `issue_spark_access_token`; Spark `start_session` and `catalog_request`; Polaris token validation, authorization, and credential vending. Full input/output/error contracts are in `component-methods.md`.

Keep `http://keycloak.localhost:8080/realms/lakehouse` as the canonical issuer in user tokens and Polaris validation. Containers use Docker service DNS for back-channel calls and JWKS retrieval without altering the issuer. The Hub depends on Keycloak and the Docker Engine API, and stores its state in local SQLite; user runtimes depend only on their own Hub broker, Polaris REST, and RustFS data endpoints. Detailed trust boundaries and sequence flow are in `component-dependency.md` and `services.md`.

## Compatibility and construction notes

- Register the broker through the custom Authenticator handler extension contract supported by the selected JupyterHub version. Pin that version and verify the precise `get_handlers()` and Hub token/server-model APIs during construction; do not rely on deprecated generic extra-handler configuration.
- Verify that the selected authenticator exposes the required Keycloak group and encrypted token state to the Hub without sending refresh tokens to single-user servers.
- Ensure Polaris receives both the required `polaris` audience and the existing `resource_access/polaris/roles` values, and that its internal principal matches `preferred_username` after reconciliation.
- Configure user-container network access to the broker, Polaris, and RustFS without giving the container Docker Engine access or provider administrative credentials.
- Redact bearer, refresh, client-secret, and temporary storage-secret values in logs and error paths.

## References

- [JupyterHub authenticator and encrypted auth state](https://jupyterhub.readthedocs.io/en/stable/reference/authenticators.html)
- [JupyterHub service authentication and Hub token APIs](https://jupyterhub.readthedocs.io/en/stable/reference/api/services.auth.html)
- [JupyterHub Authenticator API](https://jupyterhub.readthedocs.io/en/stable/reference/api/auth.html)
- [Apache Polaris Keycloak guide](https://polaris.apache.org/guides/keycloak/)
- [Apache Polaris external IdP configuration](https://polaris.apache.org/releases/1.8.0/managing-security/external-idp/)
- [Apache Polaris access control](https://polaris.apache.org/releases/1.8.0/managing-security/access-control/)
- [Apache Polaris vended credentials](https://polaris.apache.org/releases/1.8.0/vended-credentials/)
- [Apache Polaris Spark client](https://polaris.apache.org/releases/1.8.0/polaris-spark-client/)
