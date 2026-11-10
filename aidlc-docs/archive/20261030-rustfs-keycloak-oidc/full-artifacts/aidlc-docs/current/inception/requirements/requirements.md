# Requirements — RustFS Keycloak OIDC Login

## Intent Analysis
- **User request**: "start a new aidlc intent , with the goal to integrate oidc login in rustfs"
- **Request type**: New Feature
- **Scope estimate**: Multiple Components — RustFS Compose service, Keycloak realm bootstrap and contract, protected runtime credentials, a new RustFS policy bootstrap, legacy script retirement, operator documentation, and canonical knowledge.
- **Complexity estimate**: Moderate — the configuration surface is native to RustFS 1.0.4, but its claim/policy semantics and container hostname resolution are unverified.
- **Requirements depth**: Standard
- **Clarifications**: `requirement-verification-questions.md` (13 answers; no contradictions detected).

## Functional Requirements

### FR-1 Console OIDC login
The RustFS console must offer browser sign-in through the Keycloak `lakehouse` realm using the OIDC Authorization Code flow and a dedicated confidential Keycloak client for RustFS. (Q1: A)

### FR-2 Admission
Users who belong to at least one of `role-default-owner`, `role-default-developer`, `role-default-analyst`, or `role-default-writer` may sign in. A user with none of these groups must not obtain any RustFS access through OIDC. (Q2: D)

### FR-3 Authorization by group
The Keycloak `groups` claim (plain group names, no path prefix) is used directly as the list of RustFS policy names. Four RustFS policies are named exactly after the groups and mirror the platform data-role model over the three environment buckets (Q3: A, Q5: B):

| RustFS policy (= Keycloak group) | `bucket-default` (prod) | `bucket-default-uat` | `bucket-default-dev` |
|---|---|---|---|
| `role-default-owner` | manage (read, write, delete, bucket config) | manage | manage |
| `role-default-developer` | read | read | read/write |
| `role-default-analyst` | read | none | none |
| `role-default-writer` | read/write | read/write | read/write |

- "Manage" means full S3 control of those three buckets. It does **not** include RustFS server administration (users, policies, server configuration), which stays with the root break-glass identity.
- A user in several groups receives the union of their policies.
- No policy grants access to buckets other than the three listed.

### FR-4 Policy provisioning
An idempotent operator bootstrap must create the four RustFS policies when missing, verify them when present, and refuse to change a conflicting existing policy. It runs server-side with the protected root keys and never prints credentials.

### FR-5 Keycloak client bootstrap
`infra/keycloak/bootstrap-realm.py` and `infra/keycloak/realm-contract.json` must declare and additively ensure the RustFS client and its client-scoped `groups` membership mapper, following the existing JupyterHub/Airflow pattern:
- Exact redirect URIs for both `localhost` and `127.0.0.1` on the RustFS console host port; no wildcards. (Q6: A)
- Refuse conflicting client, secret, callback, or mapper configuration.

### FR-6 Root break-glass login
The existing root access-key / secret-key console login stays available as a documented break-glass recovery path. (Q4: A)

### FR-7 Client secret handling
The RustFS client secret is generated once as a protected file under `.runtime/credentials/` (mode 0600), never replaced automatically, and delivered to RustFS at container start. It must not appear in Compose files, `.env`, logs, or command output, and should be kept out of `docker inspect` output where the RustFS configuration mechanism allows. (Q7: A)

### FR-8 Container-reachable identity provider
RustFS must reach Keycloak discovery, token, and signing-key endpoints from inside its container, while validating the canonical issuer `http://keycloak.localhost:8080/realms/lakehouse` that browsers use.

### FR-9 No regression of existing storage access
Polaris STS credential vending, bucket bootstrap, and the existing root-key S3 paths must keep working unchanged.

### FR-10 Retire legacy RustFS identity scripts
Retire `infra/identity-provisioner/reconcile-rustfs-roles.py`, `provision-rustfs-identities.py`, and `rustfs-role-policy.json`, and remove any references that would break (for example, image `COPY` lines). (Q8: B)

### FR-11 Documentation and knowledge
- Update `README.md` with the RustFS OIDC login, policy bootstrap, secret rotation, and break-glass procedure.
- Canonical knowledge: UPDATE `knowledge/opensource-lakehouse-infra-v2/application-design.md`; RETIRE `knowledge/hive-dremio-rustfs/`. (Q9: A)

## Out of Scope
- Programmatic `AssumeRoleWithWebIdentity` for CLI/SDK clients (Q1).
- RustFS server administration through OIDC.
- MFA, non-loopback exposure, and any change to JupyterHub, Airflow, or Polaris authentication.

## Non-Functional Requirements
- **Security (project conventions; Security Baseline extension not enabled)**: loopback-only published ports; secrets only as protected files; exact callback URIs; least-privilege policies limited to the three buckets; no secret values in logs, reports, or output.
- **Availability**: during a Keycloak outage, OIDC login is unavailable and root break-glass login keeps working.
- **Maintainability**: all bootstrap steps are rerunnable and fail closed on conflicts; versions stay pinned (RustFS 1.0.4, Keycloak 26.8.1).
- **Testability**: contract tests for the Keycloak client, the Compose service, and the policy documents. Under PBT Partial mode, Hypothesis property tests cover policy-document invariants and serialization round-trips (PBT-02, -03, -07, -08, -09).

## Verification Requirements (Q10: B)
- Automated contract tests and property tests pass.
- Local runtime checks: the OIDC provider is listed by RustFS, the console authorize request redirects to Keycloak with an exact registered callback, the four policies are present and match their definitions, and the Polaris STS check (`scripts/verify-rustfs-sts.py`) still passes.
- Interactive console login is confirmed by the user.

## Assumptions and Risks

> **Update 2026-10-30 (Functional Design findings F1–F10)**: Risk 1 is resolved — RustFS 1.0.4 maps a multi-valued `groups` claim to same-named policies and rejects logins with no resolvable policy. Risk 2 is resolved by a Keycloak alias on a dedicated RustFS identity network plus an exact egress allowlist. Risk 3 is resolved by an entrypoint wrapper that exports the secret from a mounted file. Risk 4 is resolved: the callback is `/rustfs/admin/v3/oidc/callback/default` on the console port. Risk 5 is unchanged. See `aidlc-docs/current/construction/plans/rustfs-keycloak-oidc-functional-design-plan.md`.
1. **Claim semantics (unverified)**: RustFS 1.0.4 is assumed to accept a multi-valued `groups` claim as policy names. Functional Design must verify this; if it doesn't hold, a change request is required, because Q5 fixed the mechanism.
2. **Hostname resolution**: `keycloak.localhost` resolves to loopback inside containers. Whether RustFS fetches keys from the discovery-advertised `jwks_uri` is unknown; this was the root cause of the Airflow login failure.
3. **Secret injection**: no file-based client-secret setting was observed, so delivering the secret without exposing it in container metadata needs design work.
4. **Callback path and port**: the exact RustFS console callback URL to register (console port 9001 vs. API port 9000) is unverified.
5. **Writer group**: `role-default-writer` is a service role. Interactive login for it requires a human Keycloak user in that group; none is created by this intent.

## Extension Configuration
| Extension | Decision |
|---|---|
| Security Baseline | No (Q11: B) |
| Property-Based Testing | Partial — PBT-02, PBT-03, PBT-07, PBT-08, PBT-09 enforced; others advisory (Q12: B) |
| Resiliency Baseline | No (Q13: B) |
