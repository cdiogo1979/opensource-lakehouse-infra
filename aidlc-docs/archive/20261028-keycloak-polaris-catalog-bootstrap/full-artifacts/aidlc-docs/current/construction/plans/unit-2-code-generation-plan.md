# Unit 2 Code Generation Plan — Keycloak and Polaris Authorization

## Unit context

U2 Infrastructure Design is approved. U1 provides Keycloak 26.8.1, Polaris 1.8.0, their separate PostgreSQL stores, protected runtime-file preparation, and loopback/private networking. U2 adds Keycloak realm/client/group configuration, Polaris OIDC/RBAC configuration, and explicit identity reconciliation. U3 owns RustFS buckets/policies/vending; U4 owns the end-user CLI/coordinator, creation of the three product catalogs/namespaces and smoke tables, Spark execution, and end-to-end journey tests.

This plan authorizes tracked-source changes only after explicit approval. It does not authorize reading/writing `.runtime/credentials/`, generating live credentials, starting/rebuilding containers, applying Keycloak/Polaris configuration, creating runtime identities/catalogs/grants, changing Docker volumes, or running tests. Build and Test is a later approval gate.

## Approved implementation contracts

- Keycloak realm `lakehouse`; exact groups `role-default-developer`, `role-default-analyst`, `role-default-owner`, and `role-default-writer`.
- Separate public human Authorization Code + PKCE client and confidential writer client-credentials service identity. The creator is an existing Keycloak username supplied at invocation and is assigned owner membership; U2 does not create human accounts.
- One issuer: `http://keycloak.localhost:8080/realms/lakehouse`; Polaris 1.8.0 uses `mixed` authentication, internal credential mode, and the built-in metastore authorizer.
- Polaris principal mapping uses the stable Keycloak username claim; role mapping is restricted to the four product roles. Keycloak outage fails closed for product-user authorization.
- Reconciliation is explicit, short-lived, additive/idempotent, and verifies effective Polaris principal-role assignments before success.
- Catalog role/grant helper supports the three agreed catalogs after U4 creates them; U2 does not create product catalogs/namespaces or smoke tables. The helper never creates buckets or changes RustFS.
- Protected writer/bootstrap/reconciler credentials remain separate, file-backed, and secret-free in tracked files. Runtime secret creation and staging occur only through an explicit future operator action.
- No changes to deferred Airflow/JupyterHub/Jenkins/StarRocks integrations.

## Generation checklist

### Step 1 — Keycloak realm configuration

- [x] Add a version-controlled, secret-free `infra/keycloak/` realm/configuration template.
- [x] Define the four groups, dedicated Polaris client roles/mappers, the public human client with PKCE, and the confidential writer client/service account.
- [x] Make local browser redirect URI configuration explicit and narrowly validated; keep the exact U4 callback configurable until the CLI flow is implemented.
- [x] Do not include human account passwords, client secrets, or Polaris bootstrap credentials in the template.

### Step 2 — Polaris OIDC and network configuration

- [x] Extend the tracked Polaris configuration template with the approved mixed/internal mode, Keycloak OIDC tenant/issuer, stable username mapping, and filtered product-role mapping.
- [x] Preserve U1's PostgreSQL configuration and add only the required U2 settings.
- [x] Configure Keycloak's fixed canonical frontend hostname; configure Polaris to validate that exact issuer while fetching JWKS through private Docker service DNS, with Polaris metadata discovery disabled.
- [x] Extend protected runtime preparation only to support U2 file paths/mounts. Generated secrets remain absent from source and are not generated during code generation.

### Step 3 — Keycloak bootstrap helper

- [x] Add an explicit operator-invoked helper under `scripts/` or `infra/keycloak/` to validate/apply the realm contract additively.
- [x] Accept an existing owner username and assign only that user to `role-default-owner`; fail if the identity is absent or ambiguous.
- [x] Create/validate the writer service identity and groups without logging generated secret material.
- [x] Use a protected Keycloak administration credential source; do not print, pass on the command line, or store secret values in tracked configuration.

### Step 4 — Polaris authorization and reconciliation helpers

- [x] Add a short-lived explicit Polaris authorization bootstrap helper for metastore principals, the four principal roles, per-catalog roles, and grants following the approved matrix.
- [x] Require the expected catalogs to exist first; do not create catalogs, namespaces, tables, buckets, or object policies in U2.
- [x] Add an explicit reconciliation helper that reads the four approved Keycloak groups and converges Polaris principal-role assignments by stable username.
- [x] Use protected file-backed Keycloak and Polaris bootstrap credentials; fail on missing/duplicate identity, issuer/mapping conflict, unexpected grant, or incomplete verification.
- [ ] Replace the current use of the local Keycloak bootstrap administrator for Polaris principal-ID attribute writes with a narrowly scoped service identity. This is a known least-privilege gap; do not use this path in shared/production deployments until resolved.
- [x] Preserve unrelated users, roles, grants, and catalogs. No broad reset, replacement, or deletion path.

### Step 5 — Safe diagnostics and operator documentation

- [x] Propagate a generated operation ID through helper output where practical.
- [x] Report provider, username, role, catalog, outcome, and failure category; redact secrets, bearer tokens, token claims/payloads, and authorization headers.
- [x] Document the helper order and the U4 handoff. Clearly state that membership changes are incomplete until explicit reconciliation succeeds.
- [x] Update README/configuration docs only for U2 behavior; do not claim the overall product bootstrap is complete.

### Step 6 — Code generation review

- [x] Review generated source for scope, secret-handling intent, idempotency paths, conflict handling, and role-matrix fidelity.
- [x] Confirm no runtime state, credentials, volumes, buckets, or users were touched during this turn.
- [x] Update this plan, lifecycle state, execution plan, and audit.
- [x] Present generated changes for review; Build and Test remains a separate approval gate.

## Build and Test handoff

Later Build and Test must validate realm import/reconciliation, distinct human/writer flows, exact issuer and Polaris OIDC mapping, five-minute human token lifetime, group add/remove convergence, fail-closed Keycloak outage, catalog role/grant behavior across the three catalogs after U4 creates them, safe reruns/conflict handling, and credential-redacted diagnostics. U4 owns actual browser/CLI redirect flow and full product/Spark journey verification. U3 owns direct/vended RustFS authorization tests.

## Approval gate

**Plan status: APPROVED; SOURCE REVIEW APPROVED.** The user approved the generated source on 2026-10-28. Generated source is summarized in `construction/unit-2/code/code-summary.md`. No tests/builds or runtime operations were performed. The separate U2 Build and Test plan is at `construction/plans/unit-2-build-and-test-plan.md` and awaits approval. A least-privilege Keycloak reconciler identity remains an implementation hardening item because syncing the Polaris-generated principal ID requires writing one Keycloak user attribute.
