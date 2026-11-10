# U2 Infrastructure Design — Keycloak Identity and Polaris Authorization

## Scope and baseline

This design configures Keycloak 26.8.1 and Apache Polaris 1.8.0 for the initial `default` data product. It extends U1's `lakehouse-local` Compose runtime, private network, canonical issuer, persistent database boundaries, and protected secret-file staging. It provisions identity/authentication configuration and the catalog authorization model; it does not create runtime identities or catalog state in this document. Implementation and live verification require the later Code Generation and Build and Test approvals.

The approved identity source is Keycloak realm `lakehouse`, with groups `role-default-developer`, `role-default-analyst`, `role-default-owner`, and `role-default-writer`. Polaris uses the built-in metastore-backed authorizer. Keycloak group membership is reconciled into Polaris principals and principal-role assignments. RustFS object policies remain independently enforced by U3.

## Keycloak realm and clients

- Provision the `lakehouse` realm from a version-controlled, secret-free realm template. Keep realm import additive: matching configuration is verified; conflicting realm/client/group definitions stop with a safe diagnostic instead of replacing the realm.
- Keep generated secret values outside the template and inject them through the approved protected-file workflow. Do not store a writer or Polaris bootstrap secret in JSON, Compose interpolation, source control, command-line arguments, or logs.
- Create a public human client using Authorization Code with PKCE. Permit only exact local redirect URIs needed by the approved UI/client; disable implicit and direct password grants. Configure the Polaris-facing human access-token lifetime to at most five minutes, without shortening unrelated realm/client tokens.
- Create a separate confidential service client with service accounts/client credentials for `write-service-account`. Disable unused interactive flows. Add this identity only to the writer group.
- Create only the four approved product groups. Assign corresponding narrowly scoped client roles and configure client scopes/protocol mappers to emit the Polaris role claim and stable username claim required by Polaris. Do not expose all realm groups or unrelated identity attributes to Polaris.
- Keep Keycloak realm administration separate from product-owner group membership. Product owner membership does not grant realm-admin roles.

## Polaris authentication and principal mapping

Keycloak's fixed frontend URL follows the [Keycloak hostname configuration](https://www.keycloak.org/server/hostname). Polaris's direct JWKS route and explicit issuer validation follow [Quarkus OIDC configuration](https://quarkus.io/version/3.27/guides/security-oidc-configuration-properties-reference/); support remains subject to verification against the pinned Polaris runtime.

- Set Polaris authentication to `mixed` for the configured realm and retain internal credential mode with the built-in authorizer. Polaris 1.8.0 documents `mixed` as supporting internal authentication and external OIDC; its Keycloak integration guide uses this mode to preserve the internal setup token path while authenticating users through Keycloak.
- Explicitly allow only the `lakehouse` realm in Polaris realm-context resolution and require the `Polaris-Realm` request header. This prevents implicit selection of a default realm and ensures requests are scoped to the bootstrapped product realm.
- Configure the external OIDC tenant to validate the exact issuer `http://keycloak.localhost:8080/realms/lakehouse`. Keycloak uses this fixed frontend hostname so discovery and issued token `iss` stay identical. Polaris is a bearer-token service: disable its metadata discovery and fetch the JWKS directly from `http://keycloak:8080/realms/lakehouse/protocol/openid-connect/certs` over Compose service DNS, while explicitly validating the canonical issuer. Host clients use the canonical issuer URL; no token issuer rewrite or `.localhost` network alias is used.
- Configure Polaris principal mapping to use the stable Keycloak `preferred_username` (or equivalent explicitly configured username claim) as the metastore principal name. Do not set a guessed Polaris principal ID from Keycloak. The immutable Keycloak `sub` is retained by reconciliation/audit for identity correlation and conflict detection.
- Configure role extraction only from the dedicated Polaris client role claim. Map the four product-role values to Polaris principal-role names using the Polaris 1.8.0 role mapper (`PRINCIPAL_ROLE:<role-name>` convention). Filter unrelated Keycloak roles/scopes. Unknown or absent claims and principals are denied.
- Keep user authorization dependent on the metastore-backed principal and explicit grants. Do not enable fully external principals or replace the built-in authorizer with OPA.
- On Keycloak outage, normal product-user authorization fails closed as required by U2-NFR-06. Do not distribute internal Polaris credentials to human clients, Spark, or writer workloads. The internal token endpoint is available only to the protected operator/bootstrap execution path; its credential must not be mounted into normal application containers.

## Protected operator bootstrap and reconciliation

- Use a distinct Polaris internal bootstrap principal/credential for explicit setup and grant management. Restrict the source file to the operator; expose it only to the short-lived operator command/container and only for the required operation. It is not a general user identity or a product-user fallback.
- Reconciliation is an explicit, short-lived operator command. It reads current Keycloak membership through the supported administrative interface, validates the complete desired membership, then ensures only the necessary Polaris principals and principal-role assignments.
- Give the reconciler a dedicated Keycloak administrative client/service account limited to reading users and the four product groups. Avoid realm-wide administrator access if the Keycloak permission model supports the required least-privilege reads. Keep Polaris bootstrap authority separate from Keycloak read authority.
- Reconciliation verifies effective Polaris assignments before success. It preserves unrelated principals, roles, and grants; conflicts and partial failures return nonzero and visibly non-converged. A retry recomputes the desired state and is idempotent.
- Require healthy Keycloak and Polaris, a reachable private JWKS endpoint, and Polaris authentication readiness before any provisioning or reconciliation mutation. Host-side discovery remains available at the canonical issuer. On timeout or dependency failure, stop before role/grant changes.

## Polaris roles and grants

Use the four product names as Polaris principal roles. Define distinct catalog roles per catalog/environment and grant them to the corresponding principal roles. Keep content privileges separate from `CATALOG_MANAGE_ACCESS`; only product-owner catalog roles receive the grant-management privilege, scoped to the product catalogs.

| Principal role | `lakehouse` production | `lakehouse-dev` | `lakehouse-uat` |
|---|---|---|---|
| `role-default-developer` | Read | Read/write | Read |
| `role-default-analyst` | Read | No grant | No grant |
| `role-default-owner` | Product content + product-scoped access management | Product content + product-scoped access management | Product content + product-scoped access management |
| `role-default-writer` | Read/write | Read/write | Read/write |

- Implement read/write as explicit metadata and data privileges required for listing namespaces/tables and Iceberg read/write operations. Do not use broad full privileges for developer or writer roles.
- Do not grant `TABLE_DROP`, namespace drop, catalog configuration, or access-management privileges to developer or writer roles unless a later approved requirement and test demonstrate the need.
- Owner access-management is restricted to the product catalogs. It does not include platform service administration, Keycloak realm administration, or RustFS policy/root administration.
- Grant only the privileges and securable scopes needed for the approved role matrix. Verify effective inheritance so parent grants do not widen access.
- Exact privilege sets for Spark/Iceberg write operations are confirmed in U4 integration tests against the pinned Polaris version; any expansion is reviewed against the approved matrix.

## Secret files and rotation

- Store distinct generated files under `.runtime/credentials/` for Polaris bootstrap, the Keycloak writer client, and any dedicated reconciler credential. Keep owner-only host source files and use the U1 service-specific read-only staged mounts when a container needs access.
- Do not mount Polaris bootstrap authority into Keycloak, Polaris server, Spark, or ordinary user containers. The operator-only execution path reads it for explicit bootstrap calls.
- Writer-secret rotation follows U2's replacement-client overlap procedure when same-client overlap is unavailable: provision replacement, confirm its group and Polaris mapping, switch the protected file, verify a fresh token and writer operation, then disable the old client and remove its secret.
- Never print secret values, tokens, authorization headers, or secret-bearing response bodies. Use correlation IDs and safe identifiers for operation diagnostics.

## Readiness, recovery, and network

- Preserve the U1 10-minute bounded readiness coordinator and loopback-only provider publications. PostgreSQL stays private; Keycloak and Polaris APIs remain available to their approved local clients.
- U2 provisioning/reconciliation waits for database-backed provider health, Keycloak realm readiness, host-side discovery and private JWKS availability through service DNS, Polaris API readiness, and successful OIDC validation before mutation.
- A provider restart or interrupted reconciliation does not clear assignments. After readiness returns, invoke the idempotent reconciliation and verify current group-to-principal-role state.
- This unit does not add a background reconciler, queue, token revocation service, external secret manager, or additional host-published management endpoint.

## Traceability and verification

| Design area | Requirement coverage | Required evidence |
|---|---|---|
| Canonical issuer and claims | U2-NFR-01, U2-NFR-06 | Host discovery; private service-DNS JWKS from Polaris; exact token `iss`, audience, username and product-role claim checks. |
| Human client/token lifetime | U2-NFR-02 | PKCE login; maximum five-minute `iat`/`exp`; expired token denied. |
| Groups and reconciler | U2-NFR-03, U2-NFR-09, U2-NFR-10 | Membership add/remove, stable-name resolution, successful verified convergence, safe retry and conflict handling. |
| Revocation | U2-NFR-04 | Measure denial within five minutes after group removal reconciliation, including existing-token behavior. |
| Writer client/rotation | U2-NFR-05 | Client-credentials token, writer-group mapping, protected-file replacement, old-client retirement, no secret leakage. |
| Catalog grants | U2-NFR-08 | Positive and negative checks for all four roles across all three catalogs, including grant-management denial for developer/writer. |
| Diagnostics | U2-NFR-07 | Correlation across operation; credential canaries absent from output/logs. |
| Provider failures | U2-NFR-06, U2-NFR-10 | Keycloak and Polaris outage tests deny product access and leave reconciliation non-converged. |

## Compatibility references

- Apache Polaris 1.8.0 Identity Providers documents `internal`, `external`, and `mixed` authentication, OIDC principal/role mapping, and the `PRINCIPAL_ROLE:` convention: https://polaris.apache.org/releases/1.8.0/managing-security/external-idp/
- The Polaris 1.8.0 Keycloak integration guide demonstrates mixed auth, metastore-backed principals matched by name, and a protected internal setup token: https://polaris.apache.org/releases/1.8.0/getting-started/using-polaris/keycloak-idp/
- Polaris 1.8.0 RBAC documents principal roles, catalog roles, securable privileges, and `CATALOG_MANAGE_ACCESS`: https://polaris.apache.org/releases/1.8.0/managing-security/access-control/
- Keycloak 26.8.1 Server Administration Guide documents realm/client configuration, groups/client scopes and protocol mappers, access-token lifespan, PKCE/OIDC flows, and service-account client credentials: https://www.keycloak.org/docs/26.8.1/server_admin/

All version-sensitive settings still require integrated Build and Test verification before acceptance.
