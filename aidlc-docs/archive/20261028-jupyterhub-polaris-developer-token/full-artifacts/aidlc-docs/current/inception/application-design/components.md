# Application Components — JupyterHub User Access

## Component inventory

| Component | Responsibility | Interfaces |
|---|---|---|
| Keycloak `lakehouse` realm | Browser OIDC provider; authenticates users and issues user-specific access/refresh tokens and `polaris` audience/role claims. | OIDC authorization, token, user-info, and JWKS endpoints. Existing developer and analyst groups remain the admission and authorization source. |
| JupyterHub OIDC authenticator | Starts Authorization Code flow, validates callback/state/nonce, establishes Hub identity, checks approved group membership, and retains OAuth state encrypted at rest. | JupyterHub Authenticator contract; Keycloak OIDC endpoints; Hub authentication state. |
| JupyterHub Hub and token-broker extension | Owns user/server lifecycle, stores confidential client configuration, serves a token-broker route, authenticates each caller's Hub server token, and refreshes only that user's auth state. | Hub internal user/server/token APIs; broker HTTPS/HTTP endpoint reachable by that user's server; Keycloak token endpoint. |
| Spawner and container engine | Creates and stops one isolated single-user container per admitted user, attaches only that user's home volume, and injects the session access token at launch. | JupyterHub Spawner contract; Docker Engine API available to Hub only. |
| Per-user Jupyter/Spark runtime | Hosts notebooks and launches Spark in local mode. Obtains a fresh access JWT before each Spark session; never receives the refresh token or Docker socket. | Hub broker; Polaris Iceberg REST; RustFS S3 endpoint using temporary credentials returned by Polaris. |
| Polaris | Validates Keycloak JWT issuer, signature, expiry and audience; maps username and approved roles to pre-provisioned principals; authorizes operations; vends scoped temporary storage credentials. | Iceberg REST and management APIs; Keycloak JWKS back-channel; RustFS credential vending. |
| RustFS | Stores Iceberg objects and accepts only temporary scoped credentials for user data access. | S3-compatible API. Long-lived root/bootstrap credentials remain in platform services and are not delivered to user runtimes. |
| PostgreSQL | Persists Keycloak and Polaris service state in their existing separate databases. | Private service-network database connections. |

## Responsibilities and constraints

- User identity is the authenticated Keycloak principal, correlated to Polaris through the existing `preferred_username` mapping. The broker must not accept a username asserted by the user container.
- Keycloak group admission is restricted to `role-default-developer` and `role-default-analyst`. Owner and writer roles do not grant JupyterHub admission in this journey.
- The existing Polaris mixed authentication, internal authorization, principal reconciliation, role claim filtering, and catalog grants remain in place. Developers read production/UAT/dev and write dev only; analysts read production only and cannot write.
- Hub OAuth state is encrypted using the Hub crypt key. The confidential Keycloak client secret and refresh tokens remain Hub-side. The access JWT is short-lived and present only in the requesting user's runtime for its Spark session.
- Polaris-vended temporary RustFS credentials are scoped by the authorized catalog/location. User runtimes never receive RustFS root or bootstrap credentials.
- The Hub may access the Docker Engine API to spawn containers. User containers must not mount or otherwise reach that API.
- Per-user named home volumes persist notebooks and files. Token state, client secrets, and Spark credential material must not be written to those volumes or notebook outputs.

## Components retained or introduced

Retain Keycloak, Polaris, RustFS, PostgreSQL, existing product groups and Polaris role mappings, and Spark bootstrap behavior. Introduce JupyterHub, its OIDC authenticator/broker extension, the user server image and spawner configuration, and per-user named home volumes. This design does not reintroduce FreeIPA, Hive, Ranger, or a shared Spark cluster.
