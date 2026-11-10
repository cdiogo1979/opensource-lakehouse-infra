# Requirements Verification Questions — RustFS Keycloak OIDC Login

Intent: integrate OIDC login in RustFS using the existing Keycloak `lakehouse` realm.
Context: `aidlc-docs/current/inception/reverse-engineering/`.

## Question 1 — Login scope
Which RustFS OIDC capabilities are in scope?

A) Browser console login only (Authorization Code flow to the RustFS console)

B) Console login plus programmatic `AssumeRoleWithWebIdentity` (exchange a Keycloak token for temporary S3 credentials from CLI/SDK)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2 — Who may sign in
Which Keycloak product groups may sign in to RustFS through OIDC?

A) `role-default-owner` only

B) `role-default-owner` and `role-default-developer`

C) Owner, developer, and analyst (exclude the `role-default-writer` service role)

D) All four product groups, including `role-default-writer`

X) Other (please describe after [Answer]: tag below)

[Answer]: D

## Question 3 — RustFS permissions for OIDC users
What RustFS permissions should an authorized OIDC user receive?

A) Mirror the platform data-role model per group: owner manages all three environment buckets; developer reads all and writes dev; analyst reads production; writer reads/writes all

B) Read-only console access to all three environment buckets for every authorized user

C) Owner gets RustFS administrator; every other authorized group gets read-only

D) Full RustFS administrator for every authorized user

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4 — Root static-key console login
What happens to the existing root access-key / secret-key console login?

A) Keep it as a documented break-glass recovery path (as with the Airflow local admin)

B) Keep it unchanged with no special documentation

C) Hide or disable it in the console once OIDC works

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5 — Group-to-policy mapping mechanism
How should Keycloak membership map to RustFS policies?

A) Decide in design after verifying RustFS 1.0.4 claim/policy behavior, preferring a dedicated client-scoped Keycloak claim that carries RustFS policy names

B) Use the existing `groups` claim directly, with RustFS policies named exactly after the Keycloak groups

C) Use a dedicated client-scoped Keycloak claim that carries RustFS policy names (decided now)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 6 — Console callback hosts
Which browser host(s) should the RustFS console OIDC callback be registered for?

A) Exact loopback callbacks for both `localhost` and `127.0.0.1` on the console port (same pattern as Airflow; no wildcards)

B) `127.0.0.1` only

C) A new `rustfs.localhost` hostname

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7 — Client type and secret handling
How should the RustFS Keycloak client authenticate?

A) Confidential client; the secret is created as a protected file under `.runtime/credentials/` and injected at container start without appearing in Compose files or `docker inspect` output where avoidable

B) Confidential client with the secret passed as a plain Compose environment variable from `.env`

C) Public client with PKCE, if RustFS 1.0.4 supports it

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 8 — Legacy RustFS identity scripts
What should happen to the FreeIPA-era RustFS scripts in `infra/identity-provisioner/` (`reconcile-rustfs-roles.py`, `provision-rustfs-identities.py`, `rustfs-role-policy.json`)?

A) Leave them untouched (out of scope)

B) Retire them in this intent, since the new policy provisioning replaces them

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 9 — Stale canonical knowledge
`aidlc-docs/knowledge/hive-dremio-rustfs/` still describes the retired Hive/Dremio design. How should this intent treat it?

A) Mark it RETIRE in this intent's knowledge inventory (archive and remove from active knowledge at closure)

B) Out of scope; RETAIN unchanged

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 10 — Verification scope
What verification is required before Build and Test can pass?

A) Automated contract tests plus local runtime checks (provider listed, authorize redirect, callback registered) plus a confirmed interactive console login per authorized test user, with denied login for an unapproved user

B) Automated contract tests plus local runtime checks; interactive login confirmed by the user

C) Automated contract tests and configuration validation only

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 11 — Security Baseline extension
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 12 — Property-Based Testing extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)

B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)

C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 13 — Resiliency Baseline extension
Should the resiliency baseline be applied to this project?

Enabling it applies directional, design-time best practices derived from the AWS Well-Architected Framework (Reliability Pillar). It does not make the workload production-ready or certify any availability, RTO, or RPO target.

A) Yes — apply the resiliency baseline as directional best practices and design-time guidance (recommended for business-critical workloads, as an informed starting point that you can validate and harden before go-live)

B) No — skip the resiliency baseline (suitable for PoCs, prototypes, and experimental projects where rapid iteration matters more than reliability)

X) Other (please describe after [Answer]: tag below)

[Answer]: B
