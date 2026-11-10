# Unit 2 Build and Test Plan — Keycloak and Polaris Authorization

## Objective

Verify that the generated U2 Keycloak realm, Polaris OIDC/RBAC configuration, and explicit membership reconciliation work with the pinned U1 runtime. Establish the U2 identity and authorization contracts before U3 storage and U4 product orchestration are integrated.

This plan covers local development verification only. It does not authorize shared or production use. The generated reconciler currently uses the protected Keycloak bootstrap administrator to write a Polaris principal-ID user attribute; that least-privilege gap must remain explicit in the test report and be resolved before shared or production deployment.

## Scope and prerequisites

- Verify only `opensource-lakehouse-infra-v2` and its `lakehouse-local` Compose project.
- Use the pinned Keycloak 26.8.1 and Polaris 1.8.0 services and project-scoped data stores.
- Use runtime credential files only as inputs to the documented helpers. Never print, copy into reports, or expose their values in process arguments, logs, or test output.
- U2 tests may create or update only the `lakehouse` Keycloak realm and U2-owned test identities/groups/roles, and Polaris principals/roles created by the U2 helpers. Use clearly named test identities and clean up only those exact test identities after evidence is recorded.
- Do not remove volumes, reset databases, delete existing users/catalogs, change RustFS, or touch unrelated/legacy Compose projects.
- At the time of initial U2 execution, the three catalogs were pending U4. U4 has since created them and verified grant provisioning; effective per-user grant tests remain open in the U4 access matrix.
- Do not use production or shared credentials. If the local runtime is not isolated or the expected services are unavailable, stop before any mutation and report the prerequisite.

## Verification sequence

### 1. Static and build checks

- [x] Validate Compose interpolation and configuration without changing running services.
- [x] Compile Python helpers and validate shell syntax and the Keycloak contract JSON. (No credential-bearing properties file was read.)
- [x] No image rebuild was required; the change was a mounted Polaris properties correction. The Polaris service was recreated using the existing pinned image.
- [x] Reviewed this turn's config, generator, verification helper, and documentation changes; no secret values or destructive volume operations were added.

### 2. Runtime readiness and Keycloak realm contract

- [x] Confirm the project-scoped Keycloak and Polaris services are healthy. The approved routing keeps the canonical issuer and fetches JWKS through private service DNS. All five services were healthy after the temporary outage test.
- [ ] Run the Keycloak realm bootstrap with an explicit callback URL and an existing owner username; verify the realm and owner membership. This remains open because no real owner username or application callback URI has been supplied; do not invent either value.
- [x] Verify the configured human access-token lifetime is five minutes and the writer client is confidential/client-credentials only through the read-only Keycloak Admin API.
- [x] Verify repeated realm bootstrap converges without duplicate groups, clients, or memberships. Conflict and missing/ambiguous-owner validation remain unverified until the owner/callback inputs are available.
- [ ] Confirm diagnostics do not expose passwords, client secrets, access tokens, refresh tokens, or authorization headers.

### 3. Polaris identity provider and principal reconciliation

- [x] Verify Polaris accepts the approved mixed authentication mode: internal bootstrap authentication remains usable and a Keycloak-issued writer token authenticates against the single `keycloak.localhost` issuer. The realm override uses the Polaris 1.8.0 syntax `polaris.authentication."lakehouse".type=mixed`.
- [x] Run a redacted writer-token smoke check and verify Polaris resolves the configured username and `role-default-writer`, while denying a privileged management operation.
- [x] Corrupt only the signature portion of the otherwise valid writer JWT and verify Polaris rejects it with HTTP 401.
- [x] Verify Polaris reaches JWKS through `http://keycloak:8080`, validates the exact canonical token issuer, and rejects wrong-issuer, corrupted-signature, wrong-audience, and expired tokens with HTTP 401. The wrong-audience token came from a disposable unrelated Keycloak client; the expired token was validly signed and had a one-second lifetime.
- [x] Reconcile an isolated temporary analyst test user; verify stable username-to-Polaris-principal mapping and effective analyst role assignment.
- [x] Remove the temporary analyst's Keycloak group membership and reconcile again; verify the managed Polaris analyst role is removed. The exact temporary Keycloak user and Polaris principal were then cleaned up; no existing membership was changed.
- [ ] Verify duplicate/missing users, unsupported groups, provider errors, and incomplete Polaris updates fail closed with actionable redacted diagnostics.
- [x] Verify a Keycloak outage prevents a successful reconciliation and does not report stale state as current. During a brief stop of only the project Keycloak service, new token requests failed, reconciliation returned failure, and Polaris continued to validate an already-issued, unexpired writer token. Keycloak was restarted and all project services returned healthy.
- [ ] Record the current use of the Keycloak bootstrap administrator for the principal-ID attribute write as a local-only limitation; do not claim least-privilege completion.

### 4. Polaris authorization bootstrap and safe reruns

- [x] Run focused in-memory unit checks for the approved role matrix, all-catalog preflight stopping before any mutation, and reconciliation removing stale managed roles while preserving unrelated roles (3 passed).
- [x] Confirm the helper's preflight refuses before mutation when `lakehouse` is missing, using a mocked Polaris response (no provider mutation).
- [x] With U4 catalogs created, verify the Developer, Analyst, Owner, and Writer read/write access matrix with allowed and denied operations through temporary identities and Spark; see `construction/unit-4/build-test-report.md`.
- [x] Rerun roles-only authorization bootstrap and membership reconciliation; both completed successfully on reruns. U4 later reran the complete product bootstrap successfully; the per-user catalog-grant matrix remains open.

### 5. Persistence and stop behavior

- [x] Verify realm and Polaris principal/role metadata survive a normal Compose stop/start; the idempotent bootstrap, roles-only helper, and reconciliation all passed afterward.
- [x] Confirm the documented stop operation preserves volumes. The project stop/start commands were used; no `down -v`, prune, or manual volume deletion was run.

## Explicitly deferred checks

- Catalogs and role grants now exist; effective per-user authorization across the full matrix remains unverified (tracked in the U4 build/test report).
- RustFS bucket/policy and credential-vending behavior belongs to U3.
- Browser callback completion, full CLI journey, smoke tables, Spark access, and cross-service end-to-end authorization belong to U4.
- Replacing the Keycloak administrator with a narrowly scoped reconciler identity remains required before shared/production use.

## Evidence and completion criteria

Record command outcomes, image/platform information, health/readiness, realm/client/group state, principal and managed-role convergence, positive/negative auth results where dependencies exist, safe-rerun results, persistence behavior, and all deferred checks in `construction/unit-2/build-test-report.md`. Redact all credentials and bearer tokens. Mark U2 Build and Test complete only when all currently applicable checks pass or an explicitly scoped verification waiver is approved. Do not represent deferred U3/U4 checks as passed.

## Approval gate

## Partial execution status

**Plan status: APPROVED; PARTIALLY VERIFIED.** Compose validation, Python compilation, in-memory authorization checks, repeated Keycloak realm bootstrap, product-role verification, and repeated writer group reconciliation passed. Polaris uses the documented realm override `polaris.authentication."lakehouse".type=mixed`. Writer authentication resolves the expected principal/role and returns the expected 403 for privileged `GET_PRINCIPAL`; corrupted-signature, wrong-issuer, wrong-audience, and expired tokens return 401. A disposable analyst identity gained and then lost the managed Polaris analyst role after membership add/remove and reconciliation, then was cleaned up. The Keycloak outage check passed: token issuance became unavailable, reconciliation failed closed, and already-issued unexpired tokens remained valid at Polaris. Keycloak and all dependent project services recovered. Read-only client checks verified five-minute human token lifetime, PKCE human client, and confidential writer client-credentials settings. Normal stop/start preserved state. Evidence is in `construction/unit-2/build-test-report.md`.

Human owner/callback verification remains open because no exact application callback was supplied. Duplicate/missing-user and incomplete-update reconciliation diagnostics also remain unverified. U4 has since created the catalogs and role grants and verified the end-to-end Spark smoke-table journey and four-role access matrix; see `construction/unit-4/build-test-report.md`. No volumes were removed during this verification, and RustFS data was preserved.
