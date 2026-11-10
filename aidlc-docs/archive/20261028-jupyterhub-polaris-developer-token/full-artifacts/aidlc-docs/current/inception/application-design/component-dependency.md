# Component Dependencies, Trust Boundaries, and Data Flows

## Dependency matrix

| Caller | Dependency | Protocol / credential | Boundary |
|---|---|---|---|
| Browser | JupyterHub | HTTPS/HTTP browser session | Local host-facing edge. |
| JupyterHub OIDC authenticator | Keycloak | OIDC Authorization Code and confidential-client token exchange | Provider back-channel; client secret stays in Hub runtime. |
| JupyterHub | Local SQLite | Persistent local file on dedicated Hub state volume | Hub-owned state; no PostgreSQL connection from Hub. This reflects the later approved Unit 1 NFR Design decision. |
| JupyterHub | Docker Engine | Spawner API using host-controlled engine credentials | Privileged control plane. Hub only; never mounted into a user container. |
| User Jupyter/Spark container | Hub token broker | Hub API token belonging to its own server | Per-user runtime boundary; broker binds Hub token to the originating server/user. |
| User Spark | Polaris | Iceberg REST with that user's Keycloak access JWT | User data plane. No Polaris bootstrap credential. |
| Polaris | Keycloak | JWKS retrieval over Docker service DNS; canonical issuer still checked from JWT | Trusted identity-provider back-channel. |
| Polaris | RustFS | Credential-vending control access | Provider service boundary; provider credentials remain with Polaris. |
| User Spark | RustFS | S3 API with temporary scoped credentials vended by Polaris | Direct object data plane, limited to authorized catalog/location. |
| Keycloak | PostgreSQL | Private database connection | Existing service network. |

## Trust boundaries

1. **Browser to Hub/Keycloak:** browser redirects and callback are protected by OIDC state and nonce checks. Only the Hub handles the confidential OIDC client secret.
2. **Hub control plane:** encrypted Hub auth state contains OAuth token material. The Hub alone can use the Docker Engine API and manage user servers.
3. **Per-user runtime:** each user gets a separate Jupyter/Spark container and home volume. A container's Hub API token is limited to its own server identity; the container has no Docker socket and no other user's volume.
4. **Catalog authorization:** Spark presents the exact user's access JWT to Polaris. Polaris validates issuer/signature/expiry/audience and maps only approved principal/role claims before evaluating grants.
5. **Object storage:** Spark receives only short-lived, location-scoped credentials from Polaris. RustFS root and bootstrap secrets stay in trusted provider services.

## Sequence diagram

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Hub as JupyterHub + OIDC/Broker
    participant KC as Keycloak lakehouse realm
    participant Spawn as Spawner / Docker Engine
    participant Server as User Jupyter + Spark container
    participant Polaris
    participant RustFS

    User->>Browser: Open JupyterHub
    Browser->>Hub: Request login
    Hub-->>Browser: OIDC authorization redirect
    Browser->>KC: Authorization Code login
    KC-->>Browser: Redirect with code/state
    Browser->>Hub: OIDC callback
    Hub->>KC: Exchange code (confidential client)
    KC-->>Hub: User tokens and claims
    Hub->>Hub: Validate OIDC and approved group; encrypt auth state
    Hub->>Spawn: Start isolated user server + own named home volume
    Spawn-->>Server: Server runtime + own Hub API token
    User->>Server: Start Spark session
    Server->>Hub: Broker request with own Hub API token
    Hub->>Hub: Verify token and derive own user/server binding
    Hub->>KC: Refresh only that user's session when needed
    KC-->>Hub: Current user access JWT
    Hub-->>Server: Current access JWT only
    Server->>Polaris: Iceberg REST + Bearer user JWT
    Polaris->>KC: Retrieve JWKS via service DNS; validate canonical issuer/audience
    Polaris->>Polaris: Resolve principal and evaluate existing grants
    Polaris-->>Server: Authorized catalog response + scoped temporary storage credentials
    Server->>RustFS: Direct S3 object access with temporary scoped credentials
    RustFS-->>Server: Authorized object data
```

## Required fail-closed edges

- No approved Keycloak group → no Hub spawn.
- Invalid/cross-user Hub server token → no access JWT returned.
- Refresh failure or revoked session → no new Spark session token.
- JWT issuer, signature, expiry, audience, principal, or role invalid → Polaris denies.
- Operation outside the role grant → Polaris denies and does not vend usable credentials for that location.
- Expired/revoked temporary storage credential → RustFS denies; no root-key fallback.
