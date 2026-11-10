# Requirement Verification Questions — Developer JupyterHub to Polaris

The draft requirements capture the requested Keycloak → JupyterHub → Spark → Polaris → RustFS journey and reuse the existing developer role. Please answer the remaining decisions in this file. Recommendations are based on the current single-host Compose architecture and the 300-second Keycloak user access-token lifetime.

## Question 1: Spark execution container boundary

How should the user's isolated Spark container be provisioned?

A) Run the user's Jupyter single-user server and Spark driver/client in the same per-user container; do not expose the Docker socket inside that container. (Recommended for a safe, simple first journey.)

B) Have the Jupyter notebook submit each Spark job into a separate per-job container. This needs a trusted submission service or carefully constrained container-launch API and token handoff.

X) Other (describe after `[Answer]`).

[Answer]:A

## Question 2: Access-token expiry and long-running jobs

Keycloak currently issues human access tokens with a 300-second lifetime. How should JupyterHub handle the token after that?

A) Store access/refresh tokens in encrypted Hub auth state, refresh through Keycloak as needed, and pass the current user's fresh access-token JWT to each newly spawned Spark execution. Require Spark jobs to start with a fresh token; test expiry during a running job and fail safely. (Recommended; keeps Polaris permissions user-scoped without extending token lifetime.)

B) Keep the exact login token for the whole container session and accept that Polaris calls after five minutes fail until the user restarts/re-authenticates.

C) Increase the Keycloak access-token lifetime for JupyterHub. This simplifies jobs but increases the validity window after token theft or group removal.

X) Other (describe after `[Answer]`).

[Answer]:A

## Question 3: Polaris audience and Keycloak claims

How should the Keycloak token be made acceptable to Polaris?

A) Add an explicit `polaris` audience to the JupyterHub access token; expose the authenticated user's applicable existing developer or analyst role in `resource_access/polaris/roles`; configure Polaris to require that audience, the canonical issuer, and the existing `preferred_username` principal mapping. (Recommended.)

B) Accept any valid token from the `lakehouse` realm without an audience restriction.

X) Other (describe after `[Answer]`).

[Answer]:A

## Question 4: JupyterHub browser URL and callback

Which local address should the Keycloak client use for JupyterHub's OAuth redirect URI?

A) Use a stable local URL `http://jupyterhub.localhost:8000` with callback `http://jupyterhub.localhost:8000/hub/oauth_callback`; configure browser-facing Keycloak authorization separately from Hub-to-Keycloak Docker-network back-channel calls while retaining the canonical token issuer. (Recommended.)

B) Use another hostname, scheme, port, and exact callback URI (state them after `[Answer]`).

X) Other (describe after `[Answer]`).

[Answer]:A

## Question 5: Developer test identity

Which user should the end-to-end test use?

A) Create a dedicated non-admin Keycloak `developer-user`, assign it only to `role-default-developer`, reconcile its Polaris principal/role, and generate/store its test password only in protected local runtime files. (Recommended.)

B) Use an existing Keycloak developer. State the username; do not paste its password or token.

X) Other (describe after `[Answer]`).

[Answer]:A

## Question 6: Scope and existing access matrix

Should this intent implement only the developer journey and keep the existing grant matrix (read production/UAT/dev, write dev only)?

A) Yes — developer journey only; do not enable analyst, owner, or writer JupyterHub access in this intent. (Recommended.)

B) Include additional role journeys (name the roles and expected access after `[Answer]`).

X) Other (describe after `[Answer]`).

[Answer]: B , analyst

## Question 7: Security extension

Should the Security Baseline be enforced for this identity/token-forwarding work?

A) Yes — enforce all security rules as blocking requirements, especially token encryption, no token logging, strict issuer/audience/signature/expiry verification, least privilege, and per-user isolation. (Recommended.)

B) No — skip all Security Baseline rules.

X) Other (describe after `[Answer]`).

[Answer]:B

## Question 8: Verification environment

May Build and Test start/reconfigure the local JupyterHub and Keycloak services and create a temporary developer test identity, perform a browser OIDC login, submit Spark reads/writes to the existing smoke tables, and remove temporary containers/rows/identity afterward?

A) Yes — use the local stack and isolated temporary test data/identity; no production/external services. (Recommended.)

B) Prepare tests and configuration only; do not start services or create identities/data.

X) Other (describe after `[Answer]`).

[Answer]:A
