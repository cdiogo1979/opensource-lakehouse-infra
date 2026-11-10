# Workflow Plan — JupyterHub Developer and Analyst Access to Polaris

## Intent

Implement the approved user access journey in `aidlc-docs/current/inception/requirements/requirements.md`: Keycloak OIDC login to JupyterHub, isolated per-user Jupyter/Spark containers, Hub-side user token refresh, Polaris authorization, and temporary RustFS credentials.

## Approved decisions carried into the workflow

- Developer and analyst journeys are both in scope. Developer access is read across production/UAT/dev and write to dev only; analyst access is read production only and no writes.
- One Docker container per user hosts that user's Jupyter single-user server and Spark client/driver. User containers will not receive the Docker socket.
- The Hub stores OAuth access/refresh state encrypted. A Hub-side broker authenticates the requesting user's Jupyter server and returns only that user's current access JWT before a Spark session starts. Refresh tokens remain on the Hub.
- Polaris requires the canonical Keycloak issuer, `polaris` audience, user identity, and applicable product role.
- Browser URL/callback: `http://jupyterhub.localhost:8000` and `/hub/oauth_callback`; Hub-to-Keycloak back-channel access must work on the Compose network without changing the canonical issuer.
- Use a dedicated, non-admin `developer-user` test identity. Local integration testing may start/reconfigure services and create temporary developer test identity/data, then clean them up.
- The broader Security Baseline is not an additional blocking set. Security requirements explicitly needed for this token flow remain in scope.

## Workflow and stage outputs

| Stage | Work | Reviewable output / gate |
|---|---|---|
| User Stories | Define admin configuration and developer/analyst login, Spark session, authorization-denial, and token renewal stories. | Story set and traceability to FR/AC. |
| Application Design | Design JupyterHub and custom OIDC authenticator/config, Hub token broker authentication and API, container networking, Spark token handoff, Keycloak audience/role claims, and Polaris integration. | Component/data-flow design, trust boundaries, and API contract. |
| Units Generation | Break design into implementation units and sequence dependencies. | Unit-of-work plan and construction plans. |
| Construction — Unit 1: JupyterHub foundation | Add pinned JupyterHub/Jupyter DockerSpawner service/profile, persistent Hub state with cryptographic key, per-user singleuser image/container, browser/back-channel URL configuration, and Keycloak OIDC client/group admission. | Functional/NFR/infrastructure design and code generation review for this unit. |
| Construction — Unit 2: Hub token broker and Spark client | Implement a Hub-side broker that authenticates the caller as its own JupyterHub server, refreshes only that user's session, returns a fresh access JWT, and fails closed. Add Spark launcher/client configuration to request and use the exact token for the session. | Broker/API and Spark authentication implementation, negative token tests, and secret-handling review. |
| Construction — Unit 3: Polaris and role authorization | Configure Keycloak `polaris` audience and role claims for developer/analyst; configure Polaris issuer/JWKS/claim mapping and role provisioning as needed; connect Spark to Polaris REST and verify scoped RustFS credential vending. | Polaris configuration/bootstrap changes and verified permission mapping. |
| Construction — Unit 4: End-to-end verification and operations | Add local integration checks for login, isolation, developer/analyst read-write matrix, token refresh/failure, and cleanup. Document start/stop, user onboarding, broker troubleshooting, and rollback. | Build/test evidence and deploy handoff. |
| Build and Test | Run static checks, compose validation, unit tests, then authorized local integration tests with temporary developer identity/data. Exercise expiry/revocation and clean up test resources. | Test summary with passed checks, gaps, and any remaining approvals. |
| Deploy Handoff | Document operator configuration, secrets, bootstrap sequence, URLs, user enrollment, limitations, and rollback. Do not publish or deploy without a separate user request. | Handoff review and intent closure. |

## Dependencies and sequencing

1. Confirm supported JupyterHub, DockerSpawner, and singleuser image versions before pinning; the project currently defers JupyterHub and has no active runtime definition.
2. Unit 1 establishes user identity and container isolation before the broker is built.
3. Unit 2 broker API and Spark integration depend on the exact JupyterHub server-token identity/scopes available in the selected version. Application Design must prove this API boundary and prevent one user's server from obtaining another user's token.
4. Unit 3 token claims and Polaris mappings must align with the existing canonical issuer, service-side JWKS resolution, and role grants.
5. Unit 4 verifies both role journeys. The current test authorization explicitly covers creation of a temporary developer test user; if analyst login testing requires creating a new analyst identity, request that approval before creating it.

## Key risks to resolve in design

- **Hub broker authorization**: User containers are untrusted from the Hub's perspective. The broker must bind every request to the calling JupyterHub server identity, reject requests from another user/server, avoid accepting caller-supplied usernames, and never return refresh tokens.
- **Token audience and role claims**: Polaris must see the intended realm issuer and `polaris` audience while the browser and Hub back-channel can both resolve the Keycloak endpoints.
- **Spark token propagation**: Avoid command-line arguments, notebook output, Spark event logs, or persistent configuration containing bearer tokens. Define how the launcher provides the token to the REST client without logging it.
- **Short token lifetime**: Human tokens currently last 300 seconds. A running Spark session does not change identity or replace its token silently; calls after expiration fail safely and a new session obtains a fresh token.
- **Credential vending**: Confirm Polaris's S3 credential vending works with RustFS endpoint/path-style behavior and that Spark uses only the vended scoped credentials.
- **Local TLS**: Current issuer and browser callback use local HTTP. The design must distinguish this local test profile from production TLS requirements.

## Scope boundaries

- No Ranger or FreeIPA changes.
- No Docker socket inside user containers and no per-job container launcher in this intent.
- No change to existing developer/analyst Polaris data permissions beyond the Keycloak claim mapping needed to enforce them.
- No production rollout, external publication, commit, or deletion of existing data as part of Build and Test.
- Temporary test identities/data created under the approved local verification scope must be removed after verification.

## Approval status

Requirements, workflow plan, User Stories, Application Design, and Units Generation were approved by the user on 2026-10-28. Construction Unit 1 is starting with Functional Design.
