# U2 Business Logic Model — Identity and Catalog Authorization

## Purpose and boundary

U2 defines how Keycloak identities and product groups become enforceable Polaris catalog privileges for the initial `default` data product. It does not create RustFS buckets or storage policies (U3), and it does not run the operator CLI or Spark smoke-table workload (U4). U2 designs authorization metadata only; RustFS remains a separate enforcement layer.

The default data product spans these catalog/namespace pairs:

| Environment | Polaris catalog | Namespace |
|---|---|---|
| Production | `lakehouse` | `default_lh` |
| Dev | `lakehouse-dev` | `default_lhdev` |
| UAT | `lakehouse-uat` | `default_lhuat` |

## Identity and token lifecycle

1. **Platform bootstrap identity is distinct.** A protected operator bootstrap identity provisions the product. It is not the Keycloak realm administrator, a Polaris superuser for daily use, or the RustFS root user. The human who creates the product is assigned the product-owner group.
2. **Human authentication uses OIDC.** Browser-based clients use Authorization Code with PKCE. Human users are provisioned separately and receive access through Keycloak group membership. Password grant is not used.
3. **The writer is a service identity.** Keycloak issues its short-lived token through the client-credentials grant. The client secret is delivered through the protected runtime secret boundary, rotated separately, and never printed. The service identity is a member only of `role-default-writer`.
4. **Tokens identify a Polaris principal and active product role(s).** Keycloak emits a stable principal name and only the product role claims derived from group membership. Polaris validates issuer, signature, audience, and time claims before resolving a principal. Missing, malformed, or unrecognized claims fail closed.
5. **Issuer URL is a single shared contract.** Browser, host-side bootstrap clients, and Polaris must use the same canonical Keycloak issuer and receive identical `iss` values. Network routes may differ: Polaris can retrieve JWKS through private service DNS while it validates the canonical issuer. Split host/container issuer values are invalid. The exact local hostname and JWKS routing are verified during U2 Build and Test.

Keycloak groups map to dedicated client roles used for Polaris role claims. Group membership is the human entitlement source. The built-in Polaris authorizer still requires known Polaris principals and Polaris metastore grants; a token claim alone does not create a principal or grant catalog access. Principal onboarding and group-membership changes therefore require an idempotent entitlement reconciliation that aligns each principal's Polaris principal-role assignments with its current Keycloak product-group membership. Revocation must remove the corresponding Polaris assignment; active JWTs may remain usable until expiry, so token lifetime and revocation behavior must be verified.

## Polaris authorization model

Polaris retains its built-in authorizer and external Keycloak OIDC authentication. The design separates:

1. Keycloak groups and client roles: identity membership and token role claims.
2. Polaris principals: stable identities matched by Keycloak username, not a guessed Polaris-generated ID.
3. Polaris principal roles: `role-default-developer`, `role-default-analyst`, `role-default-owner`, and `role-default-writer`.
4. Per-catalog Polaris catalog roles: concrete privileges on catalogs, namespaces, tables, and data.
5. Grants: catalog roles assigned to the corresponding Polaris principal role.

Polaris's documented Keycloak integration uses JWT claim mapping and requires external principals to exist in the Polaris metastore when the built-in authorizer is used. Polaris also separates principal roles from per-catalog roles. The configuration should use mixed authentication during bootstrap if the pinned Polaris release requires its internal bootstrap token endpoint; internal bootstrap credentials remain operator-only. The final OIDC mode and bootstrap sequence must be validated against Polaris 1.8.0 before implementation.

## Approved access matrix

The functional meaning of read, write, and manage is:

- **Read:** list catalog/namespace/table metadata, read table properties, and read table data.
- **Write:** read plus create/register tables and write table data/properties in the permitted environment. Write does not imply dropping tables, changing catalog configuration, or granting privileges.
- **Manage product:** manage product catalog content and product access grants in all three catalogs. This remains distinct from Keycloak realm administration and RustFS administration.

| Keycloak group / Polaris principal role | `lakehouse` | `lakehouse-dev` | `lakehouse-uat` |
|---|---|---|---|
| `role-default-developer` | Read | Read and write | Read |
| `role-default-analyst` | Read | Denied | Denied |
| `role-default-owner` | Manage content and catalog grants | Manage content and catalog grants | Manage content and catalog grants |
| `role-default-writer` | Read and write | Read and write | Read and write |

Proposed grant composition uses reader catalog roles for the read environments, contributor catalog roles for write environments, and owner catalog roles combining `CATALOG_MANAGE_CONTENT` and `CATALOG_MANAGE_ACCESS`. Contributor grants include the minimum needed to list/read tables and create/write table data, but exclude drop, catalog-property changes, and grant management. Exact Polaris privilege names, inheritance/scope, and whether the minimal contributor set supports the pinned Spark/Iceberg client are integration-test items. U3 must independently enforce the matching object-store matrix; Polaris authorization does not replace RustFS policy enforcement.

## Product-owner and writer boundaries

- The product creator is added to `role-default-owner` and receives product-scoped Polaris grants only.
- Product owners can administer Polaris product grants but cannot modify Keycloak realm configuration, manage product-group membership, or access RustFS root credentials.
- The writer service account receives `role-default-writer` and read/write grants on all three catalogs. It has no realm-admin, Polaris superuser, catalog grant-management, or RustFS root authority.
- The developer and analyst groups confer no owner, writer, realm-admin, or direct storage-administration privileges.

## Provisioning and reconciliation flow

1. Confirm Keycloak, Polaris, and their persistence services are ready. Stop if a dependency is unavailable.
2. Ensure the product groups, writer client/service account, role-to-claim mappings, and initial owner membership exist in Keycloak.
3. Configure and validate Polaris OIDC issuer, audience, principal-name mapping, and role-claim mapping. Establish only the protected setup principal/credential required by the selected Polaris bootstrap mode.
4. Ensure Polaris principal roles and per-catalog catalog roles exist with the approved privilege sets.
5. Create or validate the writer and product-creator Polaris principals; reconcile their current role assignments from Keycloak group membership. Future user onboarding and membership changes use the same reconciliation contract.
6. Ensure the three catalogs and namespaces only as required by U2 integration fixture setup; production bootstrap orchestration and resource creation belong to U4. No bucket or smoke table is created by U2.
7. Verify positive and negative Polaris operations using representative tokens for all four role classes. Do not infer RustFS results from Polaris checks.

All `ensure` operations are additive and idempotent. Matching existing state is validated; a conflicting name, issuer, audience, role definition, grant, or catalog binding fails with an actionable error. Partial success is reported and retained for a safe rerun; no automatic deletion or broad rollback occurs.

## Failure behavior

- Keycloak or Polaris unavailable: do not start dependent provisioning or report authorization as ready.
- Invalid signature, issuer, audience, time claim, principal name, role claim, or unknown Polaris principal: deny the request and emit a redacted diagnostic.
- Missing or ambiguous group-to-role mapping: do not grant a fallback role; fail closed.
- Reconciliation cannot remove a stale grant: report the principal and role identifier without token or secret material; do not claim revocation complete.
- Insufficient Polaris privilege: fail the operation and identify the required role/grant category without exposing credentials.
- A failure after some resources were created leaves those resources intact. A rerun validates them and resumes.

## Completion conditions

U2 Functional Design is complete when the Keycloak claim contract, stable principal resolution, product-group-to-Polaris role mapping, minimal catalog grant sets, entitlement reconciliation/revocation, positive/negative Polaris probes, and U2/U3/U4 boundaries are reviewed and approved. Exact OIDC configuration, claims emitted by the pinned Keycloak image, Polaris principal-role behavior, and privilege inheritance remain verification items for subsequent NFR/Infrastructure Design and Build and Test.

## Traceability

| Design area | Requirements/stories |
|---|---|
| Three catalog/namespace identities | FR-02, FR-03; US-02 |
| Keycloak product groups and creator owner membership | FR-06; US-03 |
| Writer non-interactive identity | FR-07, FR-12; US-07 |
| OIDC principal/role mapping and Polaris RBAC | FR-08; US-04–US-07 |
| Approved per-environment access matrix | FR-09, FR-10; US-04–US-07 |
| Fail-closed, safe reconciliation, redacted diagnostics | NFR-01, NFR-05, NFR-07; US-08 |
| RustFS enforcement and Spark smoke verification excluded | FR-04, FR-05, FR-11, FR-15; U3/U4 boundary |

## References and version-sensitive assumptions

- [Apache Polaris Keycloak integration guide](https://polaris.apache.org/guides/keycloak/) documents external Keycloak authentication with Polaris's built-in authorizer, principal pre-creation, and matching by name.
- [Apache Polaris 1.8.0 external identity provider configuration](https://polaris.apache.org/releases/1.8.0/managing-security/external-idp/) documents JWT principal/role claim mapping and the `internal`, `external`, and `mixed` authentication modes.
- [Apache Polaris 1.8.0 access control](https://polaris.apache.org/releases/1.8.0/managing-security/access-control/) documents the principal-role → catalog-role → privilege grant structure and the relevant catalog/table privileges.
- [Keycloak Server Administration Guide](https://www.keycloak.org/docs/latest/server_admin/) documents group, client-role, and token-claim configuration. Exact claim paths and issuer reachability must be checked with Keycloak 26.8.1 and Polaris 1.8.0 in the U2 integration tests.
