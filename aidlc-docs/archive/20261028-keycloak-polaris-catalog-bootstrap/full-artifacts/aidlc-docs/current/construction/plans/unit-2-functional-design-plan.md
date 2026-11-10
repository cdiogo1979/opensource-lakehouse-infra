# Unit 2 Functional Design Plan — Identity and Catalog Authorization

## Unit context

- **Unit:** U2 — Identity and Catalog Authorization.
- **Approved requirements:** FR-02, FR-03, FR-06–FR-10, FR-12; NFR-01, NFR-03–NFR-07; US-02–US-07.
- **Prerequisite:** U1 provider runtime passed Build and Test on `linux/arm64`.
- **Providers:** Keycloak authenticates human users and the non-interactive writer identity; Polaris resolves principals and enforces catalog authorization.
- **Not in U2:** RustFS bucket creation/policies and credential vending belong to U3; operator CLI and Spark end-to-end smoke tables belong to U4.

**Plan status: APPROVED.** This approval authorizes U2 Functional Design artifact generation only. It does not authorize code changes, runtime identity/catalog mutations, bucket creation, or container reconfiguration.

## Approved behavior contracts

- Keycloak groups: `role-default-developer`, `role-default-analyst`, `role-default-owner`, `role-default-writer`.
- Product environments: `lakehouse` / `default_lh`, `lakehouse-dev` / `default_lhdev`, and `lakehouse-uat` / `default_lhuat`.
- The platform-admin operator identity is distinct from the Keycloak realm administrator. The creating user receives product-owner membership without realm-admin or RustFS-root access.
- `role-default-writer` is a non-interactive OAuth service identity, not a human login.
- Polaris principals, principal roles, catalog roles, and explicit grants are modeled separately; Keycloak groups do not bypass Polaris authorization.
- Preserve the approved role matrix exactly. U2 designs Polaris metadata permissions; U3 designs matching object-storage enforcement.
- Bootstrap behavior is additive and idempotent: create missing resources, validate matching resources, and fail safely on conflicting or ambiguous state.

## Sequential design steps

### Step 1 — Identity model

- [x] Define the Keycloak realm/client/group layout and ownership boundaries for human and writer identities.
- [x] Define the non-interactive writer OAuth flow, secret source/rotation boundary, and client scope.
- [x] Define group claims and token fields needed for stable Polaris principal resolution. Keep the issuer URL consistent with the U1 local network/host contract; exact local hostname/DNS is an integration test item.
- [x] Define creator-to-owner assignment and separate human user onboarding from product creation.

### Step 2 — Polaris principal and catalog authorization model

- [x] Define Polaris external authentication/principal resolution for Keycloak tokens; record principal synchronization and OIDC mode as verification items.
- [x] Define principal roles and catalog roles for each of the four product groups.
- [x] Map roles to production, dev, and UAT catalog/namespace grants using the approved matrix.
- [x] Keep platform administration, product ownership, and service writing separate; no product role receives realm-admin or RustFS-root privileges.

### Step 3 — Reconciliation, failure, and verification behavior

- [x] Define ordered creation/validation steps and idempotent rerun semantics.
- [x] Define conflict, unavailable-provider, invalid-token, missing-claim, and insufficient-grant behavior; authorization must fail closed.
- [x] Define positive and negative authorization probes for metadata operations in each environment.
- [x] Define redacted progress/error behavior without secret or token output.

### Step 4 — Artifacts and traceability

- [x] Generate U2 business logic, business rules, and domain entities under `aidlc-docs/current/construction/unit-2/functional-design/`.
- [x] Trace each design rule to approved requirements and stories; identify U2/U3/U4 ownership boundaries.
- [x] Record remaining version-specific integration assumptions as explicit Build and Test items.

## Expected artifacts

- `business-logic-model.md`
- `business-rules.md`
- `domain-entities.md`
- Requirement/story traceability and identified integration assumptions.

## Approval gate

The U2 Functional Design artifacts were generated and approved. NFR Requirements planning may proceed. Code changes and runtime identity/catalog changes remain outside this artifact approval.
