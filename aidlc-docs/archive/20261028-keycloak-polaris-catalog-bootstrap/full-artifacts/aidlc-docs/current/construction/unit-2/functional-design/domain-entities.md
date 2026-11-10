# U2 Domain Entities — Identity and Catalog Authorization

These are logical design entities. They do not prescribe implementation class names or make runtime changes.

## Entities

### Product Role Group

Represents one approved Keycloak group for the `default` data product.

- **Identity:** Exact group name and product identifier.
- **Role kind:** Developer, analyst, owner, or writer.
- **Members:** Human Keycloak users, except writer, which is a non-interactive service identity.
- **Mapped token roles:** Zero or more narrowly scoped Keycloak client roles emitted for Polaris.
- **Authority boundary:** Cannot confer realm administration or RustFS root access.

### Identity Principal

Represents an authenticated human or service identity.

- **Identity:** Stable Keycloak username/service-account username and immutable Keycloak subject identifier.
- **Kind:** Human or non-interactive service.
- **Issuer/audience:** Expected canonical Keycloak issuer and Polaris audience.
- **Group memberships:** Current product role groups in Keycloak.
- **Polaris principal:** Matching metastore principal provisioned by name.
- **Lifecycle:** Provisioned, active, disabled, or reconciliation-required.

### OIDC Access Token

Represents a signed, time-bounded identity assertion used by Polaris.

- **Issuer:** The one canonical URL shared by browser, host clients, and Polaris.
- **Subject/principal name:** Stable identity mapped to the Polaris principal.
- **Audience:** Intended Polaris service/client.
- **Product role claims:** Only mapped Keycloak product roles represented by current group membership.
- **Validity:** Bounded by issued-at and expiration claims; existing tokens can persist until expiry after membership changes.
- **Secret handling:** Token contents are never logged or persisted in repository artifacts.

### Polaris Principal

Represents a human or service identity known to the Polaris built-in authorizer.

- **Identity:** Principal name matching the configured Keycloak claim.
- **Source:** Created/reconciled by privileged bootstrap or the authorized onboarding/reconciliation operation.
- **Principal roles:** Zero or more product principal roles, reconciled to the identity's current Keycloak membership.
- **State:** Present, matching, conflicting, or absent.

### Polaris Principal Role

Groups Polaris principals under a named product entitlement.

- **Identity:** One of the four product role names.
- **Members:** Polaris principals whose current Keycloak group membership has been reconciled.
- **Catalog-role bindings:** Per-catalog catalog roles that grant the role's approved permissions.
- **Lifecycle:** Ensured additively; conflicting definitions fail rather than being overwritten.

### Polaris Catalog Role

Defines concrete privileges within one Polaris catalog.

- **Identity:** Catalog-scoped role name and catalog name.
- **Privileges:** Explicit catalog, namespace, table metadata, table read/write, and grant-management privileges as applicable.
- **Scope:** One of production `lakehouse`, dev `lakehouse-dev`, or UAT `lakehouse-uat`.
- **Bindings:** Granted to one or more Polaris principal roles.
- **Invariant:** Contributor roles do not gain destructive or grant-management access unless explicitly approved.

### Polaris Grant

Associates a catalog role with a Polaris principal role.

- **Grantor:** Protected bootstrap/authorized product-admin identity.
- **Recipient:** Product principal role.
- **Resource:** Catalog and applicable descendants.
- **Privileges:** Explicit grant set from the approved access matrix.
- **Reconciliation:** Desired grants are added; stale/unauthorized grants are removed through controlled reconciliation; unrelated grants are not silently overwritten.

### Entitlement Reconciliation

Synchronizes current Keycloak product-group membership with Polaris principal and principal-role state.

- **Input:** Keycloak identity subject, username, and current product-group/client-role membership.
- **Target:** Matching Polaris principal and exact product principal-role assignments.
- **Behavior:** Idempotent; adds newly entitled roles and removes stale product-role assignments.
- **Result:** Converged, partial, conflict, or failed.
- **Security:** Uses a least-privilege administrative credential; reports identifiers and outcomes without token or secret values.
- **Revocation evidence:** Records that Polaris assignments changed; effective token expiry/revocation bound remains explicit and testable.

### Product Catalog

Represents one environment-specific Polaris catalog for product `default`.

- **Production:** Catalog `lakehouse`, namespace `default_lh`.
- **Development:** Catalog `lakehouse-dev`, namespace `default_lhdev`.
- **UAT:** Catalog `lakehouse-uat`, namespace `default_lhuat`.
- **Authorization:** Has catalog roles and grants appropriate to its environment.
- **Storage:** Bucket and path are owned by U3; no RustFS policy is implied by a Polaris grant.

## Relationships and invariants

- A Product Role Group contains Identity Principals; the writer group contains the non-interactive writer identity.
- An Identity Principal maps by stable name to at most one Polaris Principal.
- An OIDC Access Token maps to one Identity Principal and carries only the roles derived from its current Keycloak membership at issue time.
- An Entitlement Reconciliation keeps Polaris Principal and Polaris Principal Role assignments aligned with Keycloak membership; failed reconciliation is visible and cannot be reported as successful revocation.
- A Polaris Principal Role may receive multiple Polaris Grants across the three Product Catalogs.
- A Polaris Grant assigns a catalog-scoped Polaris Catalog Role to a product principal role; it does not alter Keycloak group membership or RustFS policy.
- Product-owner authority is restricted to product catalogs/grants and never implies Keycloak realm administration or RustFS root access.
- Polaris write authority does not imply drop, catalog-property mutation, or grant management.
- User/catalog bootstrap and test operations preserve unrelated or conflicting state and never delete RustFS objects.
