# Unit 1 Functional Design Plan — JupyterHub Foundation and OIDC Admission

## Purpose

Define Unit 1's business logic and state transitions for browser login, role-group admission, and user server lifecycle. This design covers no code or infrastructure implementation choices except where a requirement constrains the behavior.

## Unit context

- Unit definition: `aidlc-docs/current/inception/application-design/unit-of-work.md` — Unit 1.
- Assigned stories: US-01, US-02, and the Unit 1 responsibilities of US-06 in `aidlc-docs/current/inception/application-design/unit-of-work-story-map.md`.
- Functional requirements: FR-1, FR-2, FR-7 in `aidlc-docs/current/inception/requirements/requirements.md`.
- Component baseline: `aidlc-docs/current/inception/application-design/` and `aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md`.
- Existing implementation areas: `infra/jupyter/hub/`, `infra/jupyter/singleuser/`, and `docker-compose.deferred.yml`. Existing Hub auth is FreeIPA/LDAP-based and is to be replaced by the approved Keycloak OIDC journey.
- Unit boundary: user sign-in and group admission, encrypted Hub auth-state lifecycle, user server spawn/stop lifecycle, per-user isolation, and persistent home ownership. Token broker implementation is Unit 2; Polaris role mapping and data authorization are Unit 3.

## Functional design work plan

- [x] Model the OIDC login workflow, identity result, required claims/groups, and denial outcomes.
- [x] Define admission rules for developer/analyst membership, including membership ambiguity and membership change behavior.
- [x] Model user/server lifecycle states and per-user home-volume ownership across login, spawn failure, stop, and restart.
- [x] Define validation and fail-closed error behavior for OIDC state, user eligibility, auth-state persistence, and server lifecycle.
- [x] Check UI scope: existing JupyterHub pages only; no custom frontend is requested.
- [x] Generate business logic, business rules, and domain entity design artifacts for Unit 1.
- [x] Validate traceability against US-01, US-02, US-06, FR-1, FR-2, FR-7, and approved application design.

## Clarification questions

### Q1 — Membership in both admitted role groups

A Keycloak user could belong to both `role-default-developer` and `role-default-analyst`. Since developer access includes dev writes while analyst access is read-only production, which admission identity should Unit 1 preserve for this user?

A) Admit with both memberships and pass both roles to Polaris; effective data access is the union of grants (Recommended only if intentional).

B) Require exactly one of the two groups; deny spawn when both are present.

C) Apply a precedence rule (please specify which role takes precedence).

X) Other (please describe).

[Answer]: A — Admit users in both groups with both roles; Polaris effective permissions are the union of grants. Such a user can write to dev through the developer role and retains production-read access through both roles.

### Q2 — Group removal while a user server is running

If an admitted user's developer/analyst group is removed while their Jupyter server is already running, when should that existing server lose access?

A) Stop the server on the next Hub auth-state/admission revalidation; otherwise require an operator stop (Recommended fail-closed lifecycle).

B) Let the current server continue until the user stops it, but deny future login/spawn.

C) Other policy (please describe).

[Answer]: A — On the next Hub auth-state/admission revalidation, stop the existing server. If no revalidation event is available, an operator must stop it; the design does not promise instantaneous group-revocation detection.

## Category analysis

- **Business logic modeling:** Login → identity validation → group admission → spawn → stop/restart. Clarification Q2 resolves behavior on eligibility changes during the server lifecycle.
- **Domain model:** User identity, role-group membership, Hub auth state, user server, and per-user persistent home. Q1 resolves the meaning of dual membership.
- **Business rules:** Authorization Code flow only; admit only the two approved groups; no password grant; deny when OIDC/admission/auth-state validation fails. Q1 and Q2 cover the remaining access-lifecycle rules.
- **Data flow:** OIDC result enters Hub auth state; only an authenticated Hub user and bounded spawn configuration reach the Spawner. Refresh-token flow and Spark JWT handoff belong to Unit 2.
- **Integration points:** Keycloak OIDC and Hub Spawner lifecycle are in scope; exact JupyterHub APIs, image, Compose, and volume configuration are deferred to NFR/infrastructure/code-generation stages.
- **Error handling:** Invalid callback/state, failed identity/group resolution, persistence failure, and spawn failure deny or fail the operation without disclosing tokens. Unit 2 owns broker renewal errors.
- **Business scenarios:** Unapproved user, missing/ambiguous groups, OIDC outage, duplicate active spawn request, failed spawn, stop/restart with persistent home, and membership removal. Q1/Q2 answer policy-dependent cases.
- **Frontend:** No custom UI; standard JupyterHub login, callback, and spawn feedback only.

## Next gate

Both answers are specific and consistent with the approved grant model. The user chose union-of-grants behavior for dual membership and server stop at the next admission revalidation, with operator stop as fallback. The three Unit 1 functional design artifacts are generated below and await review. No code or runtime configuration was changed.

**Approval prompt recorded 2026-10-28T18:46:06Z:** “Review the Unit 1 Functional Design artifacts in `aidlc-docs/current/construction/unit-1/functional-design/`: `business-logic-model.md`, `business-rules.md`, and `domain-entities.md`. They define OIDC admission, dual-group union semantics, membership-revocation handling, server lifecycle, encrypted auth state, and per-user persistent home ownership. Approve Unit 1 Functional Design to continue to NFR Requirements, or request changes.”
