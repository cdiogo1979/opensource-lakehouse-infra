# Units of Work — JupyterHub Developer and Analyst Access

## Decomposition approach

This is a brownfield implementation with four sequenced units. Existing platform boundaries are retained: Keycloak remains the identity provider, Polaris the catalog authorization and credential-vending service, and RustFS the object store. JupyterHub and its per-user runtime are introduced by updating the existing deferred Jupyter integration under `infra/jupyter/` and Compose configuration. The current LDAP/FreeIPA authenticator is legacy material to replace for this journey, not an additional authentication path.

The units are logical construction increments, not separate deployable services. Unit 4 owns cross-component acceptance and operational documentation; each implementation unit is still responsible for its focused tests and review.

## Unit definitions

### Unit 1 — JupyterHub foundation and OIDC admission

**Outcome:** A Keycloak-authorized developer or analyst can start an isolated Jupyter server with encrypted Hub auth state and an individual persistent home volume.

**Responsibilities**

- Pin compatible JupyterHub, Authenticator, DockerSpawner, and single-user image versions after validating the required APIs.
- Replace FreeIPA/LDAP login and authorization in the deferred Hub configuration with browser OIDC Authorization Code flow and allow only the developer and analyst groups.
- Configure the confidential Keycloak OIDC client, callback, canonical issuer/back-channel endpoints, encrypted Hub auth state, and protected Hub secret mounts.
- Add/enable the Hub service in the approved local Compose profile, integrate DockerSpawner, and ensure only Hub has Docker Engine access.
- Provide one isolated Jupyter/Spark container and persistent named home volume per user; do not put refresh tokens or client secrets in those volumes.
- Add focused configuration and authentication/admission checks.

**Primary code/document ownership:** `infra/jupyter/hub/`, `infra/jupyter/singleuser/`, the JupyterHub service definition in Compose, and associated protected runtime credential provisioning/documentation.

**Stories / requirements:** US-01, US-02, US-06; FR-1, FR-2, FR-7.

### Unit 2 — Hub token broker and Spark session identity

**Outcome:** A user's Spark session receives that same user's current access JWT through a verified server-to-Hub path, without exposing refresh tokens or changing identity.

**Responsibilities**

- Add the Hub-side broker route through the selected version's supported Authenticator extension contract.
- Authenticate the broker caller with its JupyterHub API token and derive its user/server binding from Hub state; reject cross-user and caller-supplied identity claims.
- Refresh only the matching user's encrypted Keycloak auth state and return the current access JWT and expiry, never the refresh token.
- Update the per-user Spark launcher and Iceberg REST configuration to obtain a token before each Spark session and use the exact JWT as the Polaris Bearer token.
- Keep token values out of arguments, logs, persistent config, home files, and notebook output; fail closed if renewal fails.
- Add focused broker positive/negative, refresh, and Spark token-handoff checks.

**Primary code/document ownership:** Hub broker module/route under `infra/jupyter/hub/`; Spark session launcher and client configuration under `infra/jupyter/singleuser/`.

**Stories / requirements:** US-03, US-06; FR-3, FR-4 and token lifecycle/availability/auditability NFRs.

### Unit 3 — Polaris role authorization and RustFS credential vending

**Outcome:** Polaris recognizes the same Keycloak user and role presented by Spark, applies the existing developer/analyst grants, and gives Spark only scoped temporary RustFS credentials.

**Responsibilities**

- Align the Keycloak confidential/public client claims as required so the user JWT carries the explicit `polaris` audience and approved role claims.
- Preserve the canonical issuer and service-network JWKS lookup; keep Polaris in its existing mixed authentication and internal authorization model with reconciled principals.
- Preserve existing access grants: developer reads all three environments and writes dev only; analyst reads production only and cannot write.
- Ensure Spark uses Polaris's REST credential vending for direct RustFS operations; no user container receives root/bootstrap storage keys.
- Add focused role-claim, allowed/denied operation, and scoped-credential checks without changing unrelated catalog permissions.

**Primary code/document ownership:** `infra/keycloak/` claim/client contract, `infra/polaris/` OIDC and principal-role mapping, relevant identity reconciliation/grant scripts, and `infra/jupyter/singleuser/` catalog/storage client settings.

**Stories / requirements:** US-04, US-05; FR-4, FR-5, FR-6.

### Unit 4 — End-to-end verification and operations

**Outcome:** The complete developer and analyst journeys and their security boundaries are verified locally and documented for operators.

**Responsibilities**

- Verify browser OIDC sign-in and denial for users outside approved groups.
- Verify per-user container/home isolation and no Docker socket exposure.
- Exercise broker user/server binding, token refresh, failure/revocation, token expiry, and no identity substitution.
- Verify developer and analyst read/write matrices through Spark, Polaris, and RustFS credential vending.
- Verify logs and persistent locations do not contain bearer, refresh, client, or temporary storage secrets.
- Clean up only test resources created for the approved verification and document start/stop, onboarding, troubleshooting, limitations, and rollback.

**Primary code/document ownership:** cross-unit integration checks and operational documentation in project test/docs locations selected during functional design. Unit 4 does not absorb or delay focused tests from Units 1–3.

**Stories / requirements:** US-01–US-06; FR-1–FR-7 and all applicable NFRs.

## Brownfield code organization

- Update the existing `infra/jupyter/hub/` and `infra/jupyter/singleuser/` implementation areas; replace the legacy FreeIPA/LDAP auth flow rather than retaining two login mechanisms.
- Keep Keycloak client/claim and Polaris OIDC/RBAC changes in their existing `infra/keycloak/` and `infra/polaris/` ownership areas.
- Add JupyterHub to the intended default local Compose stack only after its image, network, secrets, and health dependencies are defined. The current `docker-compose.deferred.yml` is inventory-only.
- Keep user homes as per-user named volumes. Keep Hub database/auth state and protected secrets separate from those volumes.
- Leave the existing canonical knowledge file unchanged during construction; after successful intent closure, update it with durable approved JupyterHub and broker decisions.

## Completion conditions

All four units have reviewed functional, NFR, infrastructure, code-generation, and verification plans; every story and requirement has an owner; dependencies are satisfied in sequence; and Unit 4 reports the role matrix and token/isolation results with any gaps explicit.
