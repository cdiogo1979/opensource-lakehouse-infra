# Application Design Plan — JupyterHub Developer and Analyst Access

## Purpose

Define component responsibilities, interfaces, service orchestration, and dependency/data-flow boundaries for the approved Keycloak → JupyterHub → Spark → Polaris → RustFS user journeys. This is high-level application design; detailed business rules and implementation specifics remain in later construction stages.

## Context and baseline

- Requirements are approved in `aidlc-docs/current/inception/requirements/requirements.md`.
- Approved stories and personas are in `aidlc-docs/current/inception/user-stories/`.
- The current canonical baseline is `aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md`. Retain Keycloak, Polaris, RustFS, Postgres, and current catalog/role responsibilities. JupyterHub is currently deferred; this intent introduces its application and runtime boundary.
- At intent closure, update the canonical application design with durable approved JupyterHub/token-broker decisions. This plan and detailed intent artifacts remain the active review record until then.

## Design scope

Identify responsibilities and contracts for:

1. Keycloak realm/client and audience/role claims.
2. JupyterHub OIDC login, encrypted auth state, admission, and user server lifecycle.
3. The Hub-side token broker and its per-user server authentication boundary.
4. Per-user Jupyter/Spark environment and the Spark session launcher/token handoff.
5. Polaris OIDC validation, principal/role mapping, authorization, and RustFS credential vending.
6. RustFS object access using only Polaris-vended scoped credentials.

## Design plan checklist

### Analysis and decisions

- [x] Read approved requirements, stories, personas, and workflow plan.
- [x] Read the current canonical application-design baseline and identify retain/update decisions.
- [x] Collect answers to the design questions below.
- [x] Analyze answers for ambiguity or contradiction; none found.
- [x] Confirm component boundaries, token broker caller authentication, Spark runtime topology, home persistence, and Keycloak client type.

### Design artifact generation after plan approval

- [x] Generate `aidlc-docs/current/inception/application-design/components.md` with component purpose, responsibility, and interfaces.
- [x] Generate `aidlc-docs/current/inception/application-design/component-methods.md` with high-level method signatures, inputs, outputs, and purposes.
- [x] Generate `aidlc-docs/current/inception/application-design/services.md` with service responsibilities, orchestration, and interaction patterns.
- [x] Generate `aidlc-docs/current/inception/application-design/component-dependency.md` with dependency matrix, communication patterns, trust boundaries, and data flows.
- [x] Generate `aidlc-docs/current/inception/application-design/application-design.md` consolidating the approved design artifacts.
- [x] Validate that components, method contracts, services, and dependencies agree with requirements and stories.
- [x] Record the design approval prompt in the audit before presenting the completed design for review.

## Context-specific design questions

These decisions affect the component boundary and service contracts. Please answer through the response controls.

### Question 1 — Token broker boundary

Where should the Hub-side token broker live?

A) Implement it as a custom JupyterHub extension/API route in the Hub process, using the caller's JupyterHub server API token to identify that user's server and encrypted auth state (Recommended; avoids a separate service and keeps refresh tokens at the Hub).

B) Implement a separate internal broker service that authenticates each user server and calls a restricted Hub integration.

X) Other (please describe).

[Answer]: A — Custom JupyterHub extension/API route in the Hub process.

### Question 2 — Spark execution topology

Where should the Spark driver and executors run for the first journey?

A) Run Spark in local mode inside the user's isolated Jupyter container (Recommended; matches the approved same-container boundary and avoids shared executor credential propagation).

B) Run the driver in the user's container and connect to a separately operated shared Spark cluster; the design must define per-user executor identity and token handling.

X) Other (please describe).

[Answer]: A — Spark local mode inside the user's isolated Jupyter container.

### Question 3 — User home persistence

What should happen to notebooks and user files when a Jupyter server stops?

A) Persist each user's home directory in a separate named volume with access limited to that user's server (Recommended; preserves work while maintaining per-user isolation).

B) Use an ephemeral home that is removed when the user's server stops.

X) Other (please describe).

[Answer]: A — Persist each user's home in a separate named volume.

### Question 4 — Keycloak OIDC client type

How should JupyterHub authenticate as an OIDC client during the server-side token exchange?

A) Use a confidential Keycloak client; store its client secret in protected local runtime credentials and keep it out of images and source (Recommended for the server-side Hub).

B) Use a public client with PKCE and no client secret.

X) Other (please describe).

[Answer]: A — Confidential Keycloak client; secret in protected runtime credentials.

## Approval gate

## Confirmed design-planning decisions

- **Broker boundary:** Custom JupyterHub extension/API route in the Hub process; use the requesting server's JupyterHub API token to identify the server and user, and retrieve only that user's encrypted auth state.
- **Spark topology:** Spark local mode inside the user's isolated Jupyter container.
- **Home persistence:** Separate named home volume for each user. OAuth secrets and access JWTs must not be written to home volumes.
- **Keycloak client:** Confidential server-side OIDC client with its secret in protected runtime credentials, not in source or container image layers.

Answers are incorporated and unambiguous. The user approved this plan with “approve and continue” on 2026-10-28. The design artifacts below are now generated and await review.

**Approval prompt recorded 2026-10-28T18:30:38Z:** “Please review `aidlc-docs/current/inception/plans/application-design-plan.md`. It defines the design artifact checklist and records your decisions: Hub extension token broker, local Spark mode inside each per-user container, per-user persistent home volumes, and a confidential Keycloak OIDC client. Approve the plan to begin generating the application design artifacts, or request changes.”

**Plan approval received 2026-10-28:** “approve and continue.” Classified as approval and continuation.

## Design artifact generation notes

- Keep the canonical Keycloak issuer (`http://keycloak.localhost:8080/realms/lakehouse`) in browser tokens and Polaris validation. Use Docker service DNS only for Hub/Polaris back-channel reachability and JWKS retrieval.
- Keep Polaris in its current mixed authentication model with internal metastore authorization, pre-provisioned principals, and the existing Keycloak role claim mappings. Do not switch to external authorization or introduce OPA as part of this design.
- The broker is an in-process Hub extension using an Authenticator handler registration contract supported by the pinned JupyterHub version. The exact handler registration and server-token introspection API must be verified against that pinned version during construction; deprecated generic extra-handler configuration is not the design contract.
- A broker call is bound to the requesting server's Hub token and server/user model. It returns only the access JWT for that authenticated user. Refresh tokens remain Hub-side in encrypted auth state.
- Spark runs in local mode inside the user's isolated server container. The access JWT is runtime-only; Polaris vended temporary RustFS credentials are used for direct storage access.
- Each user home uses an individual named volume. Neither Hub OAuth state nor JWTs are persisted in these home volumes.

**Design approval prompt recorded 2026-10-28T18:34:34Z:** “Please review the five generated artifacts under `aidlc-docs/current/inception/application-design/`: `components.md`, `component-methods.md`, `services.md`, `component-dependency.md`, and `application-design.md`. They preserve the current Keycloak/Polaris/RustFS authorization model and add per-user Hub OIDC, brokered access-token renewal, local Spark, isolated persistent homes, and Polaris-vended RustFS access. Approve the application design to continue to Units Generation, or request changes.”
