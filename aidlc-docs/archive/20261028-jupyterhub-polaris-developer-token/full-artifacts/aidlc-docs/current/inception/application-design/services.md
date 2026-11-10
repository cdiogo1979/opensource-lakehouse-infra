# Services and Orchestration — JupyterHub User Access

## Logical services

| Service | Runs in | Responsibility |
|---|---|---|
| Browser OIDC service | Keycloak and Hub | Authenticates the user and establishes an individual Hub session using Authorization Code flow. |
| Hub token-broker route | JupyterHub process | Authenticates the requesting single-user server's Hub API token, refreshes that user's encrypted OAuth state if required, and returns only the user's current access JWT. |
| User notebook/Spark service | One isolated single-user container per user | Runs Jupyter and starts local Spark sessions with the user's current JWT. |
| Iceberg catalog/auth service | Polaris | Verifies JWT identity and claims, applies existing grants, and vends temporary RustFS credentials. |
| Object storage service | RustFS | Stores and serves the objects addressed by Iceberg metadata using the scoped vended credentials. |

## Login and spawn flow

1. The browser requests JupyterHub and is redirected to the Keycloak `lakehouse` realm through OIDC Authorization Code flow.
2. Keycloak authenticates the user and returns the browser to the registered Hub callback. The Hub validates the OIDC response and resolves the group membership.
3. The Hub admits only `role-default-developer` or `role-default-analyst`, then retains that user's OAuth token state encrypted in Hub storage. Non-members cannot spawn.
4. The Hub spawns the user's single-user Jupyter/Spark container through the Hub-side container engine integration. The container receives its own Hub API token and isolated named home volume. It does not receive the Docker socket or Keycloak refresh token.
5. A Spark launcher asks the Hub broker for an access JWT. The broker validates the caller's Hub server token and derives the user/server binding from Hub state; it does not trust a username from the request body.
6. The broker refreshes that user's Keycloak session when needed and returns only that user's current access JWT and expiry. The launcher supplies the exact JWT to Spark for that session.

## Spark, Polaris, and storage flow

1. Spark local mode sends Iceberg REST requests to Polaris with the user's JWT as a Bearer token.
2. Polaris verifies the token against the canonical issuer `http://keycloak.localhost:8080/realms/lakehouse`, its signature/JWKS, expiry, explicit `polaris` audience, username claim, and allow-listed role claim.
3. Polaris resolves the identity to the pre-provisioned principal and applies the existing internal grants. Developer access is read-all/write-dev; analyst access is read-production/no-write.
4. For authorized object access, Polaris returns temporary RustFS credentials scoped to the permitted location. Spark accesses RustFS directly with those credentials; RustFS root/bootstrap credentials never enter the user container.
5. Logs record identity and result metadata only. The bearer JWT, refresh token, client secret, and temporary storage secret are redacted and not persisted.

## Token/session behavior

- The configured human access-token lifetime is 300 seconds. The broker obtains a current token before each new Spark session; refresh tokens remain encrypted in Hub state.
- Existing Spark sessions retain the identity token used to create that session. If it expires and a later request needs authentication, that request fails safely. The user starts a new Spark session to obtain a current JWT.
- Keycloak unavailability, revoked user session, or failed refresh prevents a new Spark session from starting. No service account or bootstrap-credential fallback changes the user identity.
- Stopping a user's server does not delete that user's named home volume. Hub token state and credentials are not stored in that volume.

## Reachability and issuer behavior

Keep the browser/token issuer URL canonical as `keycloak.localhost`. Container-to-container Hub and Polaris calls use Docker service DNS as needed, including JWKS retrieval, without changing the issuer value expected in the JWT. User containers need reachable Hub broker, Polaris, and RustFS service endpoints only; Docker Engine and provider administration endpoints remain outside the user runtime boundary.
