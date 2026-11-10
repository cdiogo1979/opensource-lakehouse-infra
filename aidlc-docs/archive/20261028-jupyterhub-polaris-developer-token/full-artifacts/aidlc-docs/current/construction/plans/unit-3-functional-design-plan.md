# Unit 3 Functional Design Plan — Polaris Authorization and RustFS Credential Vending

## Purpose

Define the business behavior for resolving a Spark user's Keycloak identity and role in Polaris, enforcing the approved developer/analyst data-access matrix, and vending temporary RustFS credentials for authorized locations. This stage records behavior and domain rules; it does not change code, provider configuration, catalog grants, buckets, or runtime state.

## Unit context

- **Unit:** Unit 3 — Polaris role authorization and RustFS credential vending, from `aidlc-docs/current/inception/application-design/unit-of-work.md`.
- **Stories:** US-04 (developer reads across environments and writes only dev), US-05 (analyst reads production only), and Unit 3 responsibilities of US-06 (safe, diagnosable access decisions).
- **Requirements:** FR-4, FR-5, and FR-6 in `aidlc-docs/current/inception/requirements/requirements.md`.
- **Dependencies:** Unit 1 OIDC admission and Unit 2 token broker/Spark handoff; existing Keycloak `lakehouse` realm, Polaris principal and role mappings, the approved catalogs and buckets, and the existing authorization grants.
- **Unit boundary:** Role-claim interpretation, Polaris principal resolution and operation decisions, RustFS credential-vending behavior, denial/failure semantics, and focused Unit 3 acceptance rules. Cross-component browser-to-object-store verification remains Unit 4.
- **Constraints:** Preserve the canonical issuer, explicit `polaris` audience, `preferred_username` principal mapping, allow-listed product-role claims, existing catalog and bucket layout, and approved role grants. Never substitute the shared writer or bootstrap identity for a human user; never give Spark long-lived RustFS root/bootstrap keys.

## Approved authorization matrix

| Role | Read production | Read UAT | Read dev | Write production | Write UAT | Write dev |
|---|---:|---:|---:|---:|---:|---:|
| `role-default-developer` | Allow | Allow | Allow | Deny | Deny | Allow |
| `role-default-analyst` | Allow | Deny | Deny | Deny | Deny | Deny |

An absent, malformed, expired, wrong-issuer, wrong-audience, or unrecognized-role token is denied. An identity with both approved roles receives the union of their grants, consistent with the approved Unit 1 dual-membership behavior.

## Functional design work plan

- [x] Model JWT validation and map a verified `preferred_username` and allow-listed `resource_access/polaris/roles` claim to the existing Polaris principal and role.
- [x] Model catalog, namespace, table, and object-location authorization for the approved role matrix and current catalog/bucket layout.
- [x] Define operation classes covered by read and write, including metadata discovery, table creation, append/overwrite, and destructive operations.
- [x] Model the authorized-operation flow from Spark Iceberg REST request through Polaris authorization, credential vending, and direct RustFS access.
- [x] Define temporary credential scope, lifetime/renewal behavior, response handling, and safe failure semantics without exposing credential values.
- [x] Define denial behavior for missing/ambiguous identity or role, unauthorized environment/location, malformed location, vending failure, and RustFS rejection; fail closed with no fallback identity.
- [x] Define safe audit/correlation data and token/credential redaction for allowed and denied operations.
- [x] Generate `business-logic-model.md`, `business-rules.md`, and `domain-entities.md` under `aidlc-docs/current/construction/unit-3/functional-design/`.
- [x] Validate traceability to US-04, US-05, US-06, FR-4, FR-5, FR-6, and the approved Unit 3 boundary.

## Clarification questions

### Q1 — Scope of role-derived access when a user has both approved roles

Unit 1's approved rule says dual membership yields the union of grants. Should Unit 3 preserve that behavior at Polaris for the full Spark session?

A) Yes. Resolve both approved roles from the verified token and apply the union of grants (Recommended; consistent with Unit 1 and the existing role model).

B) Reject tokens carrying both roles and require exactly one role.

C) Other behavior (please specify).

[Answer]: A — Preserve both approved roles and apply the union of their grants.

### Q2 — Operation mapping for “write”

The requirements specify environment-level read/write, but the exact Polaris operation mapping should be explicit. Which write semantics should the functional rules use?

A) Allow all supported data-changing operations in the developer's dev scope (create/alter/drop namespace or table, append, overwrite, delete, and other Polaris-authorized mutations); deny every mutation outside dev and for analysts (Recommended; treats “write” consistently as all mutations).

B) Allow data-row writes only in dev; deny metadata mutations such as create/drop/alter.

C) Other operation mapping (please specify).

[Answer]: A — Allow all supported data-changing operations only in the developer's dev scope; deny mutations outside dev and all analyst mutations.

### Q3 — Temporary RustFS credential renewal during a Spark session

Polaris vends temporary storage credentials for authorized locations. How should Unit 3 define behavior when those credentials expire during a long-running Spark session?

A) Use the supported Iceberg/Polaris credential-vending refresh path for subsequent storage requests; if refresh is unavailable or denied, fail the affected operation and require a new Spark session, with no static-key fallback (Recommended; preserves least privilege and avoids extending credential lifetime).

B) Require the user to restart Spark before any credential expiry; do not attempt refresh inside the session.

C) Other behavior (please specify).

[Answer]: A — Use the supported Polaris/Iceberg vending refresh path where available; otherwise fail the operation and require a new Spark session, with no static-key fallback.

### Q4 — Authorization boundary for catalog discovery

Should catalog and namespace listings reveal names from environments the role cannot read?

A) Filter or deny discovery so the analyst sees production only, while the developer sees all three approved environments; do not disclose unauthorized catalog/namespace names (Recommended; keeps metadata visibility aligned with the role matrix).

B) Allow catalog/namespace names to be listed across environments but deny table metadata and data access outside the role's read scope.

C) Other visibility rule (please specify).

[Answer]: A — Align catalog and namespace discovery with the read grants: developer sees all three environments, analyst production only.

## Category analysis

- **Business workflow:** Spark sends the exact Unit 2 user JWT to Polaris → Polaris validates issuer/signature/expiry/audience → maps principal and approved role claims → authorizes the catalog operation and resolved storage location → vends scoped temporary credentials → Spark accesses RustFS directly.
- **Entities:** Verified user principal, Keycloak role claim, Polaris product role, catalog resource, namespace, table, object location, authorization decision, vended credential set, and correlation ID.
- **Business rules:** Only the explicit allow-listed developer/analyst roles grant access. Apply the approved matrix at both catalog-operation and object-location boundaries. No policy ambiguity, missing role, or service outage may broaden access.
- **Data flow:** The user JWT travels from Spark to Polaris over the configured REST path. Temporary RustFS credentials travel only to the requesting Spark process for the authorized operation/location. Tokens and storage secrets never enter logs, persistent configuration, notebook output, or shared runtime files.
- **Integration points:** Keycloak JWT claims, Polaris OIDC/principal/role mapping and authorization, Iceberg REST, Polaris credential vending, and RustFS S3-compatible access. Exact configuration and SDK behavior will be validated in later design/code stages against pinned service versions.
- **Failure handling:** Invalid identity/claims, denied operation, expired session, credential-vending error, or RustFS denial returns a bounded failure and no fallback credentials or identity. Retry is permitted only where the selected client protocol safely supports it; no authorization failure is retried as another identity.
- **Cross-unit boundary:** Unit 3 owns focused role/operation/location/vending checks. The complete OIDC login → Spark → Polaris → RustFS journeys and live revocation behavior remain Unit 4 acceptance work.

## Next gate

The user approved all recommendations. Q1 preserves union-of-grants for dual membership; Q2 treats write as all supported mutations in dev only for developers; Q3 uses protocol-supported vending renewal and otherwise fails closed with no static-key fallback; Q4 aligns catalog/namespace discovery with read grants. The three functional-design artifacts are generated and await review. No application code, provider configuration, catalog grants, buckets, or runtime services have been changed.
