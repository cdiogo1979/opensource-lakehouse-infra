# Requirements — JupyterHub Developer and Analyst Access to Polaris

## Intent Analysis

- **Intent ID**: `20261028-jupyterhub-polaris-developer-token`
- **User request**: Implement developer and analyst JupyterHub journeys using Keycloak OIDC. Forward each user's exact Keycloak access-token JWT to that user's isolated Spark environment. Spark authenticates to Polaris with the JWT; Polaris enforces role grants and vends short-lived RustFS credentials.
- **Request type**: New identity and data-access integration for the existing Keycloak–Polaris–RustFS lakehouse.
- **Scope**: JupyterHub OIDC authentication, user/container spawning, Keycloak token claims, Polaris principal/role mapping, Spark Iceberg REST authentication, RustFS credential vending, and end-to-end verification.
- **Current project status**: Keycloak, Polaris, RustFS, and bootstrap Spark are supported in Compose. JupyterHub is deferred in `docker-compose.deferred.yml`; prior FreeIPA-based Jupyter files exist only in the completed intent archive.

## Functional Requirements

These reflect the answered verification questions, including a Hub-side token broker to refresh user JWTs for Spark sessions launched after the user's container starts.

### FR-1: Keycloak sign-in

JupyterHub shall authenticate users through the existing Keycloak `lakehouse` realm using browser-based OpenID Connect Authorization Code flow. Password collection or the OAuth Resource Owner Password grant shall not be used.

### FR-2: Role-based admission

Only users assigned to Keycloak group `role-default-developer` or `role-default-analyst` shall be admitted to the corresponding JupyterHub journey and allowed to spawn a user environment. Polaris shall resolve the same user identity to the corresponding principal and role. Owner and writer JupyterHub journeys are out of scope.

### FR-3: User token inheritance

JupyterHub shall retain each authenticated user's Keycloak access and refresh tokens in protected, encrypted authentication state. Before each Spark session starts, the user's Spark launcher shall request a fresh access JWT from a Hub-side token-broker endpoint. The broker shall authenticate the requesting user's JupyterHub server, retrieve and refresh only that user's Keycloak session, and return only that user's current access-token JWT. The launcher shall pass that exact JWT to Spark through a proposed `POLARIS_ACCESS_TOKEN` setting. The user's refresh token shall remain in Hub auth state and shall not be delivered to the user container. The Hub shall not substitute the shared `write-service-account` identity or Polaris bootstrap credentials.

### FR-4: Spark-to-Polaris authentication

Spark's Iceberg REST client shall send the session's user JWT as a Bearer token to Polaris. Polaris shall validate the token signature, canonical issuer, expiry, and explicit `polaris` audience, then resolve the user principal and approved developer or analyst role before authorizing catalog operations. A running Spark session shall not switch user identities; if its JWT expires and Polaris requires another authenticated request, the request shall fail safely and a new Spark session shall obtain a fresh token.

### FR-5: Scoped storage credential vending

After an authorized Spark operation, Polaris shall vend temporary RustFS credentials scoped to the permitted catalog, bucket, and object prefix. Spark shall use those credentials for direct object-store access and shall not receive RustFS root or bootstrap credentials.

### FR-6: Developer and analyst permissions

The developer journey shall allow reads across approved production, UAT, and dev data, and writes only to approved dev catalog/bucket paths. The analyst journey shall allow reads of approved production data and no writes in any environment. Both journeys shall use the existing role grant matrices.

### FR-7: Per-user isolation and token handling

Each user shall receive an isolated Jupyter/Spark environment. Access tokens shall not be written to logs, image layers, persistent shared files, notebook outputs, or another user's container. Hub-side token state shall be encrypted at rest; container environment exposure shall be limited to the owning user's environment and trusted host administrators.

## Non-Functional Requirements

- **Security**: The user declined adding the broader Security Baseline as a separate blocking control set. Security properties required by the requested token-forwarding design remain in scope: OIDC state and nonce protections, strict issuer/audience/signature/expiry validation, least-privilege role admission, no shared writer identity, no long-lived storage keys, encrypted Hub auth state, and per-user isolation. Use TLS where applicable to the selected local deployment profile.
- **Token lifecycle**: Keycloak human access tokens currently live 300 seconds. The Hub-side broker shall use encrypted Hub auth state to refresh the user's session before each new Spark session. It shall fail closed if the user session is expired, revoked, or cannot be refreshed. A Spark session shall not assume its JWT remains valid for the whole Jupyter session.
- **Availability**: If Keycloak is unavailable, new logins and token renewals fail closed. Existing JWTs remain usable only until expiry, subject to Polaris policy.
- **Auditability**: Authentication identity, Polaris authorization outcomes, and container lifecycle may be logged without logging access-token values.

## Existing Technical Context

- Keycloak realm: `lakehouse`; groups in scope: `role-default-developer` and `role-default-analyst`.
- Existing catalogs: `lakehouse`, `lakehouse_uat`, `lakehouse_dev`; databases: `default_lh`, `default_lhuat`, `default_lhdev`.
- Existing developer permissions: read all environments, write dev only. Existing analyst permissions: read production only, no writes.
- Polaris maps OIDC principal using `preferred_username` and extracts `resource_access/polaris/roles`, filtering the four explicitly provisioned product roles.
- Polaris's configured issuer is `http://keycloak.localhost:8080/realms/lakehouse`; the service obtains OIDC metadata/JWKS through Docker service DNS. Browser-facing Keycloak authorization and Hub back-channel calls must remain reachable while preserving this canonical issuer.
- Keycloak human access-token lifetime is 300 seconds.
- JupyterHub is currently deferred and not part of the running stack.

## Acceptance Criteria (Draft)

1. Developer and analyst users each complete browser OIDC login through Keycloak without entering credentials into JupyterHub.
2. A user outside the two approved groups is denied and cannot spawn a container.
3. The token delivered to each approved user environment is byte-for-byte that user's access-token JWT; token values do not appear in logs or persistent files.
4. Spark uses that token for Polaris REST calls. Polaris rejects invalid signature, issuer, audience, expiry, or missing role.
5. Developer reads production/UAT/dev and writes dev only; analyst reads production only and cannot write anywhere.
6. Spark receives scoped temporary RustFS credentials from Polaris and has no long-lived RustFS root key.
7. Token broker renewal, invalid/revoked Hub sessions, expiry during Spark work, and user-container restart behavior are tested without exposing refresh tokens or changing the authenticated principal.
8. Tests prove user-container isolation and clean up temporary identities, test rows, tokens, and containers.

## Sources and Compatibility References

- [Apache Polaris 1.8.0 Keycloak guide](https://polaris.apache.org/guides/keycloak/)
- [Apache Polaris 1.8.0 external identity provider configuration](https://polaris.apache.org/releases/1.8.0/managing-security/external-idp/)
- [JupyterHub authenticator and auth state documentation](https://jupyterhub.readthedocs.io/en/stable/reference/authenticators.html)
- [DockerSpawner API](https://jupyterhub-dockerspawner.readthedocs.io/en/latest/api/index.html)
- [Lakekeeper Spark access-control example supplied in the request](https://github.com/lakekeeper/lakekeeper/blob/main/examples/access-control-simple/notebooks/03-01-Spark.ipynb) — illustrative only, not the Polaris implementation contract.
