# U2 Business Rules — Identity and Catalog Authorization

1. **Keep authorities separate.** Keycloak authenticates identities and owns product-group membership; Polaris owns catalog principals, roles, and catalog grants; RustFS owns object-store authorization. A successful decision in one provider does not imply access in another.
2. **Use the approved product groups exactly.** The four product groups are `role-default-developer`, `role-default-analyst`, `role-default-owner`, and `role-default-writer`. The first three represent human entitlements; the writer is a non-interactive service identity.
3. **Keep platform administration separate from product ownership.** The bootstrap operator and Keycloak realm administrator are distinct identities. Product creator membership grants product-owner rights only; it does not grant realm-admin or RustFS-root authority.
4. **Use interactive human authentication.** Human clients use OIDC Authorization Code with PKCE. Do not use password grant for human login.
5. **Use client credentials for the writer.** The writer authenticates non-interactively with a protected client secret and short-lived OAuth tokens. Never log tokens or secret values.
6. **Use one canonical issuer.** Keycloak's token `iss`, Polaris's configured issuer, browser discovery, and host-side clients must all use the same issuer URL and exact `iss` value. Polaris may fetch JWKS through private service DNS while validating that canonical issuer; never treat different internal and external issuer values as equivalent.
7. **Resolve Polaris principals by stable name.** Map a stable Keycloak username/service-account username to the pre-created Polaris principal. Do not guess or configure a Polaris-generated principal ID in Keycloak.
8. **A token claim alone grants nothing.** A valid OIDC token must resolve to a known Polaris principal and an explicitly granted product principal role. Unknown principals and unrecognized role claims are denied.
9. **Map roles through Polaris RBAC.** Keycloak group/client roles identify the product entitlement. Polaris catalog roles hold concrete privileges, and grants connect those catalog roles to the matching Polaris principal role.
10. **Preserve least privilege by environment.** Developers read all three catalogs and write only `lakehouse-dev`; analysts read production only; owners manage product content and grants in all three; writers read/write all three without grant-management or administration privileges.
11. **Do not give contributors destructive authority by implication.** Developer and writer write grants do not automatically include table drop, catalog configuration changes, catalog grant management, or namespace deletion. Any extra privilege required by Spark must be justified and tested explicitly.
12. **Reconcile identity membership changes.** When Keycloak group membership changes, reconcile the corresponding Polaris principal-role assignments. Do not report grant/revocation completion until Polaris reflects the new state. Existing signed tokens can remain valid until expiry; the tested expiry/revocation bound must be documented.
13. **Keep storage enforcement independent.** Polaris metadata authorization and vended credentials do not replace RustFS policies. U2 verifies Polaris behavior only; U3 verifies direct and vended object access.
14. **Fail closed.** Unavailable identity/catalog providers, invalid tokens, issuer/audience mismatch, missing principal/role claims, unknown users, stale/unreconciled assignments, and insufficient grants never fall back to a broader identity or privilege.
15. **Bootstrap is additive and idempotent.** Create missing resources; validate matching resources; fail safely on conflicts. Preserve completed state after partial failure and allow a rerun to continue.
16. **Never print credentials or tokens.** Progress and failures may identify a provider, principal name, role identifier, or operation category, but not passwords, client secrets, bearer tokens, or credential payloads.
17. **Keep unit ownership clear.** U2 defines identity and Polaris authorization; U3 defines RustFS buckets/policies and storage credentials; U4 defines operator CLI orchestration, Spark smoke tables, and end-to-end access tests.

## Required U2 verification cases

- Developer: read production/dev/UAT; create/write in dev; deny writes in production and UAT.
- Analyst: read production; deny dev/UAT catalog access and writes everywhere.
- Owner: manage catalog content and catalog grants in all three product catalogs; deny realm administration and RustFS root operations.
- Writer: read/write all three catalogs; deny grant management and realm administration.
- All roles: deny missing/invalid/expired tokens, unknown principals, invalid issuer/audience, missing role claim, and unmapped role claim.
- Membership lifecycle: adding a Keycloak group membership yields the expected Polaris access after reconciliation; removing membership revokes it within the documented token/reconciliation bound.
- Reconciliation: a second run makes no duplicate roles/principals/grants; conflicting existing definitions stop safely; partial failure retains valid state and can resume.
