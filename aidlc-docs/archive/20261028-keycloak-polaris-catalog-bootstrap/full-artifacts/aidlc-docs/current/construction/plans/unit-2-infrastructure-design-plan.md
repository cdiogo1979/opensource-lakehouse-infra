# Unit 2 Infrastructure Design Plan — Keycloak and Polaris Authorization

## Unit context

U2 implements Keycloak identities/groups, Polaris OIDC authentication and catalog authorization, and explicit reconciliation from Keycloak membership to Polaris principals and principal-role assignments. U1's core Compose runtime and protected secret-file boundary are approved and running. U2 Functional Design, NFR Requirements, and NFR Design artifacts are approved.

The approved design uses one canonical issuer (`http://keycloak.localhost:8080/realms/lakehouse`), human Authorization Code with PKCE, a client-credentials writer, a separate protected operator bootstrap credential, fail-closed behavior during Keycloak outages, five-minute human tokens/revocation bound, and least-privilege catalog roles across `lakehouse`, `lakehouse-dev`, and `lakehouse-uat`. RustFS policies and credential vending belong to U3; CLI/Spark end-to-end orchestration belongs to U4.

This plan selects concrete infrastructure/configuration contracts for Keycloak and Polaris. It does not create or mutate runtime users, groups, principals, roles, grants, catalogs, buckets, or tables. Secret files are never read for this planning work.

## Planning checklist

### Analyze approved U2 design

- [x] Review U2 Functional Design and its role/environment access matrix.
- [x] Review approved U2 NFR Requirements and NFR Design patterns/components.
- [x] Preserve the U1 Compose network, canonical issuer, persistence, and protected-file secret-delivery decisions.
- [x] Keep U3 RustFS policy/credential configuration and U4 CLI/Spark flow out of scope.

### Plan approval gate

- [x] Answer the infrastructure questions below and resolve implementation boundaries; the user approved the recommended choices.
- [x] Check compatibility with the pinned Keycloak/Polaris/PostgreSQL versions and the approved NFRs using their official documentation.
- [x] Obtain explicit approval of this completed plan before generating Infrastructure Design artifacts.

### Generate Infrastructure Design artifacts after plan approval

- [x] Generate `aidlc-docs/current/construction/unit-2/infrastructure-design/infrastructure-design.md`.
- [x] Generate `deployment-architecture.md` for the Keycloak realm, clients/groups, Polaris auth, bootstrap and reconciliation paths, and secret mounts.
- [x] Validate exact settings against the pinned version documentation and U1 Compose design.
- [x] Present both artifacts for explicit Infrastructure Design approval.

## Infrastructure Design questions

Replace each `[Answer]:A` with a selected option or a concrete alternative.

### Question 1 — Keycloak realm provisioning

How should U2 create the product realm and its base configuration?

A) Provision a dedicated `lakehouse` realm from a version-controlled, secret-free realm template; inject only generated secret values from protected files at startup/bootstrap, and fail on conflicting existing configuration rather than importing or replacing the whole realm (Recommended: reproducible and additive).

B) Create the realm and all settings through interactive Keycloak Admin Console steps; document each step and avoid automated realm files.

C) Other (specify realm ownership, provisioning mechanism, and conflict behavior).

[Answer]:A

### Question 2 — Human and writer client separation

How should OAuth clients be split between browser users and the noninteractive writer?

A) Use separate clients: a public human client with Authorization Code + PKCE and exact local redirect URIs, and a confidential service client with service accounts/client credentials for the writer. Disable unused flows and scopes (Recommended: isolates human and workload credentials).

B) Use one confidential client for human and writer flows, with separate scopes and redirect URIs.

C) Other (specify client types, allowed grants, and redirect policy).

[Answer]:A

### Question 3 — Product groups and role claims

How should the four product groups become identity claims while preserving the approved stable-name principal mapping?

A) Create the exact groups `role-default-developer`, `role-default-analyst`, `role-default-owner`, and `role-default-writer`; map only those memberships to explicit Polaris product-role claims through narrowly scoped protocol mappers. Emit the stable username claim expected by Polaris and retain `sub` for correlation; do not emit unrelated realm/group data (Recommended: explicit and least-privilege).

B) Emit all realm groups in a generic `groups` claim and have Polaris filter them.

C) Other (specify group names, claim names, mapper scopes, and principal-name claim).

[Answer]:A

### Question 4 — Polaris authentication mode and bootstrap

Which Polaris authentication configuration should the deployment use to support protected provisioning and normal Keycloak OIDC users?

A) Configure the pinned Polaris release for the documented mode that supports both external Keycloak OIDC product access and its protected operator bootstrap mechanism. Keep bootstrap credentials file-backed and operator-only; select the exact supported mode and endpoints from the pinned-version documentation before implementation (Recommended: supports first-time setup without making a fallback credential available to users).

B) Use external OIDC only and provision all principals/roles through a separate supported API that requires no Polaris bootstrap credential.

C) Other (specify the supported Polaris mode, first-admin path, and user/bootstrap separation).

[Answer]:A

### Question 5 — Polaris principal identity and claim mapping

Which token claim should Polaris use to find the corresponding pre-created principal?

A) Configure Polaris to resolve the exact stable Keycloak username/service-account username claim used by the reconciler. Keep immutable `sub` as a correlation value, and fail closed if the configured name is missing, duplicated, or conflicts with an existing mapping (Recommended: consistent with approved Functional Design).

B) Use the immutable subject as the Polaris principal name and migrate the approved stable-name contract.

C) Other (specify exact claim, name normalization, uniqueness rule, and conflict behavior).

[Answer]:A

### Question 6 — Reconciliation implementation boundary

Where should the explicit idempotent group-to-Polaris reconciliation run?

A) Provide a separately invoked, short-lived operator command/container with read access to Keycloak membership and only the Polaris administrative APIs needed to ensure principals and product-role assignments. Keep it outside normal user and Spark execution paths (Recommended: isolated least-privilege operation; U4 may invoke it later).

B) Run reconciliation inside Keycloak as an event listener on each membership mutation.

C) Other (specify execution location, trigger, credentials, and retry behavior).

[Answer]:A

### Question 7 — Five-minute human-token configuration

How should the approved five-minute maximum human access-token lifetime be configured?

A) Set a realm/client-specific maximum of five minutes for Polaris-facing human access tokens, keep refresh/SSO session lifetime separate, and verify issued `iat`/`exp` claims. Do not shorten unrelated service/system tokens without a requirement (Recommended: precise enforcement of U2-NFR-02).

B) Set a five-minute realm-wide access-token lifetime for all clients, including the writer.

C) Other (specify token lifetime per client and validation evidence).

[Answer]:A

### Question 8 — Keycloak outage enforcement boundary

What must happen when Keycloak is unreachable during normal Polaris user access?

A) Configure normal product authorization to fail closed on Keycloak dependency/validation failure, with no cached group entitlement or alternate user credential. Health/readiness and operational bootstrap may report separately but cannot authorize product-user requests (Recommended: implements U2-NFR-06 directly).

B) Continue accepting locally verifiable unexpired JWTs from cached JWKS for up to five minutes.

C) Other (specify cached material, maximum age, and user-request behavior).

[Answer]:A

### Question 9 — Protected bootstrap and writer credential files

How should U2 deliver the Polaris bootstrap credential and Keycloak writer client secret?

A) Use separate generated files under the approved `.runtime/credentials/` boundary, owner-only on the host and read-only to only the process that needs each value. Never pass secret values through Compose interpolation, command-line arguments, ordinary environment variables, or logs; rotate writer credentials through the approved replacement-client flow if necessary (Recommended: consistent with U1 and U2 NFRs).

B) Use Docker secrets for both credentials and do not create host-side files beyond the Compose secret sources.

C) Other (specify file path, permissions, mounting, and operator access).

[Answer]:A

### Question 10 — Polaris role/grant bootstrap ownership

How should catalog roles and grants be provisioned and reconciled?

A) Use the protected operator/bootstrap workflow to additively ensure the four Polaris principal roles and per-catalog roles/grants for the approved matrix across all three catalogs. Verify effective grants; fail on conflicting definitions; preserve unrelated Polaris state. Keep product-owner grant management scoped to the product catalogs (Recommended: aligned with U2 design and safe reruns).

B) Let each user create or self-assign Polaris catalog roles after Keycloak login.

C) Other (specify principal/catalog role split, grant owner, scope, and conflict handling).

[Answer]:A

### Question 11 — Keycloak and Polaris dependency/readiness contract

How should startup and operator commands handle provider dependency readiness?

A) Preserve U1's bounded readiness coordinator; require Keycloak and Polaris health before U2 provisioning/reconciliation, then verify private JWKS reachability and Polaris auth readiness before dependent actions. A timeout reports the unavailable provider and does not mutate roles/grants (Recommended: respects the U1 readiness boundary).

B) Start dependent U2 actions immediately and rely on internal retries without a single readiness deadline.

C) Other (specify dependency order, readiness probes, timeout, and mutation behavior on failure).

[Answer]:A

## Answer analysis

The user approved the recommended answer for all eleven questions. The selected Keycloak setup uses a secret-free, additive realm template; distinct public human and confidential writer clients; exact product groups with narrowly scoped role claims; and a five-minute lifetime for human Polaris tokens. Polaris uses the pinned 1.8.0 mixed authentication mode with internal credential mode and metastore-backed principals so the protected internal token path remains available for bootstrap, while product users authenticate through Keycloak and receive no internal fallback credentials. Principals resolve by the configured stable username claim; the reconciler separately records immutable subject correlation. Reconciliation is a short-lived operator command that uses protected credentials, applies/verifies only the required assignments, and is gated on readiness.

The outage behavior is strict fail-closed for product-user authorization, matching U2-NFR-06. Bootstrap credentials and writer secrets use separate protected files with least-privilege mounts. The grants follow the approved environment matrix, use Polaris principal-role → catalog-role grants, and preserve unrelated state. Exact Polaris property names, startup ordering, Keycloak mapper configuration, grant API calls, and first-time bootstrap commands must still be implemented and tested against the pinned versions.

Official compatibility references reviewed: [Polaris 1.8.0 Identity Providers](https://polaris.apache.org/releases/1.8.0/managing-security/external-idp/), [Polaris 1.8.0 Keycloak integration guide](https://polaris.apache.org/releases/1.8.0/getting-started/using-polaris/keycloak-idp/), [Polaris 1.8.0 access control](https://polaris.apache.org/releases/1.8.0/managing-security/access-control/), and [Keycloak 26.8.1 Server Administration Guide](https://www.keycloak.org/docs/26.8.1/server_admin/). Polaris 1.8.0 documents `mixed` authentication as supporting both internal and OIDC authentication; its Keycloak example uses metastore-backed principals matched by name and a protected internal setup token. Polaris RBAC separates principal roles, catalog roles, and privileges. Keycloak 26.8.1 documents client service accounts/client-credentials, configurable access-token lifespans, groups, and client scopes/protocol mappers.

## Gate

**Plan status: APPROVED.** The user approved all recommended choices. Version-sensitive settings were checked against official Keycloak 26.8.1 and Polaris 1.8.0 documentation. Both U2 Infrastructure Design artifacts were reviewed and approved. U2 Code Generation planning may proceed. No runtime identity or catalog state is changed by this plan approval.

### Build-and-Test routing refinement (approved 2026-10-28)

Runtime verification showed that `.localhost` resolves to loopback inside the Polaris container. The user approved preserving canonical issuer `http://keycloak.localhost:8080/realms/lakehouse` and using Docker service DNS for JWKS. Polaris therefore disables discovery, explicitly validates that issuer, and fetches JWKS at `http://keycloak:8080/realms/lakehouse/protocol/openid-connect/certs`. Keycloak uses a fixed frontend hostname so host discovery and token issuer remain stable. This adjustment does not create a new identity or change role semantics.
