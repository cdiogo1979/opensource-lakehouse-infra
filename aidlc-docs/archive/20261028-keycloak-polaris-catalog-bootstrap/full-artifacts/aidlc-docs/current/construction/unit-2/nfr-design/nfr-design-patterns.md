# U2 NFR Design Patterns — Keycloak Identity and Polaris Authorization

## Design scope

This design applies to Keycloak authentication/group membership and Polaris OIDC principal resolution, catalog-role grants, and entitlement reconciliation for the `default` data product. RustFS bucket policies and credential vending are owned by U3. Operator CLI orchestration and Spark/Iceberg end-to-end execution are owned by U4. Concrete Compose settings, image configuration, command names, secret filenames, and exact Polaris privilege syntax remain Infrastructure Design or Code Generation decisions.

## Authentication and trust pattern

- Use the single approved issuer `http://keycloak.localhost:8080/realms/lakehouse` for host/browser and Compose clients. Polaris validates the exact issuer, signature, audience, and time bounds; issuer aliases or token rewriting are not accepted.
- Preserve the approved issuer string and `iss` value while Polaris fetches signing keys through Docker service DNS. Host-side discovery remains on the canonical issuer; Polaris uses the private JWKS endpoint and an explicit issuer check because `.localhost` resolves to loopback inside containers. If JWKS or trust configuration is unavailable or inconsistent, deny access and report a safe provider failure.
- Human clients use Authorization Code with PKCE. The writer uses OAuth client credentials and a dedicated noninteractive service identity. Human password grant is prohibited.
- Resolve the Polaris principal using the configured stable Keycloak username/service-account username. Retain immutable subject identifiers for safe correlation and detect username-to-subject conflicts rather than silently remapping an existing principal.
- A valid token is necessary but insufficient: Polaris must resolve a known principal and effective explicitly granted product role. Do not infer authorization from display names, untrusted claims, or Keycloak group membership alone.
- Keep a separate protected operator bootstrap credential for explicit provisioning and reconciliation. It is read from a protected file, restricted to operator workflows, and never supplied to product-user clients or Spark workloads. User requests never fall back to it.

## Entitlement reconciliation pattern

1. Read the complete current product-group membership and stable identity attributes from Keycloak.
2. Validate the identity and desired product role set before changing Polaris.
3. Ensure the corresponding Polaris principal exists and matches the stable configured name; stop safely on identity conflicts.
4. Apply only required changes to the product principal-role assignments. Preserve unrelated principals, roles, and grants.
5. Read back effective assignments and report success only after the desired state is verified.
6. On partial failure, report non-convergence with a correlation ID. A retry repeats the same desired-state comparison; it does not clear and recreate all grants.

Keycloak group membership is authoritative; Polaris assignments are derived, reconcilable state. Every membership change requires an explicit successful reconciliation before it is considered complete. There is no polling service, event queue, or background synchronizer in this design.

## Revocation and outage pattern

- Human Polaris access tokens have a maximum five-minute lifetime and expired tokens are rejected.
- After a successful group-removal reconciliation, the maximum residual authorization window is five minutes. Do not claim instantaneous revocation or add an unapproved revocation service.
- Do not cache group membership or derived entitlements beyond the approved token/reconciliation bound.
- When Keycloak is unavailable, fail closed for product authorization as required by U2-NFR-06. Do not accept cached group membership, stale identity data, or a fallback identity. Resume normal authorization only after Keycloak is healthy and token validation succeeds.
- When Polaris is unavailable or effective grants cannot be verified, product operations fail and reconciliation remains visibly non-converged. Recovery waits for provider readiness, then reruns idempotent reconciliation before reporting completion.

## Least-privilege catalog authorization pattern

Keep identity membership separate from catalog privileges. Map the four Keycloak product groups to matching Polaris principal roles, then bind those principal roles to narrowly scoped catalog roles in each of `lakehouse`, `lakehouse-dev`, and `lakehouse-uat`.

| Product role | Production `lakehouse` | Dev `lakehouse-dev` | UAT `lakehouse-uat` | Grant management |
|---|---|---|---|---|
| `role-default-developer` | Read | Read/write | Read | No |
| `role-default-analyst` | Read | None | None | No |
| `role-default-owner` | Product content and grants | Product content and grants | Product content and grants | Product-scoped only |
| `role-default-writer` | Read/write | Read/write | Read/write | No |

- Use catalog-scoped roles with explicit namespace/table descendants and only the operations in the approved matrix.
- Keep product-owner grant-management privileges separate from content-write privileges and scoped to the three product catalogs. They do not confer Keycloak realm administration, Polaris platform administration, RustFS root access, or bucket-policy administration.
- Developer and writer data-write grants do not imply table drop, namespace deletion, catalog configuration, or grant-management privileges. If a required Iceberg operation needs additional privileges, justify and test that exact privilege before changing the matrix.
- Verify effective inherited grants, including defaults and parent scopes, so no broader privilege is introduced indirectly.
- Polaris grants authorize catalog operations only; U3 independently enforces direct/vended RustFS access.

## Writer-secret rotation pattern

- Rotate at least every 90 days and immediately after suspected exposure.
- Use a protected file and never print either the current or replacement secret.
- If Keycloak does not support overlapping secrets on one client, create a temporary replacement writer client. Verify its membership and Polaris mapping, switch the protected secret source, obtain a fresh token and verify an approved writer operation, then disable the previous client and remove its secret.
- If validation fails, retain the old identity only for controlled rollback until the replacement is verified; report the rotation as incomplete. Do not leave both active beyond the cutover window.

## Diagnostics pattern

- Create a non-secret operation/correlation ID and propagate it through reconciliation and provider calls where supported.
- Record operation, provider, outcome, principal username or subject identifier where known, product role, catalog, and safe failure category.
- Never log passwords, client secrets, access/refresh tokens, token claims/payloads, authorization headers, or secret-bearing request bodies.
- Bound local diagnostic retention in implementation design. Error output should identify the failed step and retry/action needed without echoing provider response bodies that may contain credentials.

## Recovery and idempotency pattern

- Preserve identity and catalog state across ordinary restarts. Do not reset unrelated Keycloak groups, Polaris principals, roles, or grants during recovery.
- After both providers report ready, query Keycloak as the source of truth and rerun reconciliation. Verify the resulting Polaris assignments before restoring the operation to a converged state.
- Conflicting names, role definitions, claim mappings, or unexpected grants stop the operation with a redacted conflict report. Do not repair conflicts by broad deletion or privilege expansion.
- An operator may explicitly correct a conflict and rerun; no destructive repair is automatic.

## Mapping to U2 NFRs

| Requirement | Design response |
|---|---|
| U2-NFR-01 | One canonical issuer and exact token issuer validation across host and Compose clients. |
| U2-NFR-02 | Human tokens capped at five minutes; expired tokens denied; PKCE interactive renewal. |
| U2-NFR-03 | Explicit desired-state reconciliation after every membership change; verify before success. |
| U2-NFR-04 | Five-minute maximum residual access after successful removal reconciliation. |
| U2-NFR-05 | 90-day/emergency writer rotation with protected-file cutover and replacement-client overlap when needed. |
| U2-NFR-06 | Product authorization fails closed during Keycloak outage; bootstrap credential is separate. |
| U2-NFR-07 | Correlated, actionable diagnostics exclude credential and token material. |
| U2-NFR-08 | Environment-scoped catalog roles; content and grant-management privileges are separated. |
| U2-NFR-09 | Additive/idempotent changes; conflicts fail without broad replacement. |
| U2-NFR-10 | Provider/validation/reconciliation failures remain non-authorizing and visibly non-converged. |

## Deferred implementation decisions

Infrastructure Design and Code Generation specify the exact Polaris authentication mode, token claim paths, operator credential mechanism, least-privilege reconciliation API, catalog-role privilege syntax, Keycloak client/group mapper configuration, and safe diagnostic retention. Build and Test must verify these behaviors against the pinned Keycloak and Polaris versions before U2 acceptance.
