# U2 Tech Stack Decisions — Identity and Catalog Authorization

## Decision record

| Area | Decision/constraint | Rationale and boundary |
|---|---|---|
| Human identity provider | Keycloak 26.8.1 is the OIDC provider for human users and product group membership. | Approved platform architecture; users are provisioned separately from the initial product resources. Exact realm/client JSON and mapper configuration belong to NFR Design/Infrastructure Design. |
| Canonical local issuer | `http://keycloak.localhost:8080/realms/lakehouse` is the one issuer string for browser, host-side clients, and Polaris. Keycloak advertises this fixed frontend URL; Polaris disables metadata discovery, validates the exact issuer, and retrieves JWKS through `http://keycloak:8080/realms/lakehouse/protocol/openid-connect/certs` over private Compose DNS. | Approved U2 NFR Q1 and Build and Test routing refinement. Host discovery and Polaris JWKS use separate network routes while preserving the exact issuer and JWT `iss`. |
| Human OAuth flow | Authorization Code with PKCE; no Resource Owner Password Credentials flow. | Keeps interactive login appropriate for human identities and follows approved U2 Functional Design. Client-specific redirect URIs and mapper configuration are later design decisions. |
| Writer identity | Dedicated Keycloak client/service account uses OAuth client credentials and belongs to `role-default-writer`. | Non-interactive workload identity; the secret is protected and rotated at least every 90 days and after suspected exposure. Exact client name and secret file path belong to U2 Code Generation planning. |
| Token lifetime | Human Polaris access tokens have a maximum five-minute lifetime; expired tokens are rejected. | Approved recommended answers to U2 NFR Q3/Q4 establish a five-minute maximum revocation exposure window after successful entitlement reconciliation. Writer token duration is a separate implementation/security setting to verify. |
| Entitlement synchronization | Keycloak group membership remains the source of truth; a distinct explicit reconciliation step synchronizes membership to Polaris principals/roles after each change. | Approved recommended answer to U2 NFR Q2. No polling service or event listener is added in this requirements stage. Reconciliation must be idempotent and failures visible. |
| Polaris authorization | Apache Polaris 1.8.0 built-in authorizer remains the catalog authorization layer, using Keycloak OIDC identity and explicit Polaris metastore principals/roles/grants. | Preserves approved design and FR-08/FR-10. Do not substitute RustFS policies or claims alone for Polaris RBAC. Whether mixed/internal bootstrap auth is needed is an implementation integration check. |
| Failure behavior | Product-user authorization fails closed during Keycloak outage, token validation failure, unknown principal, missing role mapping, or insufficient Polaris grant. | Approved recommended answer to U2 NFR Q6 and global NFR-05; no stale entitlement/default-role fallback. Protected provisioning credentials are separate from normal product-user access. |
| Diagnostics | Record safe operation/provider/principal/role/catalog/failure identifiers; exclude credentials, bearer tokens, token payloads, and authorization headers. | Approved recommended answer to U2 NFR Q7; detailed log format and retention remain later design choices. |
| Authorization storage/data | Keycloak state remains in its dedicated Keycloak PostgreSQL store; Polaris state remains in its separate Polaris PostgreSQL store. | Inherits approved U1 infrastructure design. U2 adds groups, principals, roles, and grants without sharing or reusing the retired Hive metadata store. |

## Decisions deliberately deferred

- Exact Keycloak realm export, client identifiers, protocol mappers, audience settings, and writer service-account username.
- Host/browser discovery and private Compose JWKS routing for `keycloak.localhost`/`keycloak` must be verified on the supported local platform.
- Exact Polaris OIDC mode/configuration, principal and role claim paths, bootstrap-auth mechanism, and whether/when a Polaris restart is required.
- Exact Polaris grant API calls and minimum catalog/table privilege set required by the selected Spark/Iceberg client.
- Writer-token lifetime and secret-overlap mechanism supported by Keycloak; if a single client cannot overlap secrets, perform a controlled replacement-client cutover.
- Reconciliation command/API, protected administrative principal, retry/timeout values, and operational user workflow.
- Keycloak and Polaris implementation versions remain pinned to the U1 design baseline and are verified together during U2/U4 Build and Test.

These items are not silently assumed to work. NFR Design/Infrastructure Design must choose concrete configuration, and Build and Test must verify the local issuer, claim mapping, revocation, writer rotation, privilege inheritance, and failure behavior before the U2/U4 journey is accepted.
