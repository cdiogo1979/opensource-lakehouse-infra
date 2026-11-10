# Unit 2 NFR Requirements Plan — Identity and Catalog Authorization

## Unit context

U2 defines Keycloak authentication, product-group entitlements, Polaris principal resolution, and catalog-role enforcement. Its approved Functional Design assigns human and service identities through four Keycloak groups and requires corresponding Polaris principals/grants. U1 Build and Test passed on `linux/arm64`; U2 Functional Design artifacts are approved.

This plan clarifies measurable quality expectations for identity, token validation, entitlement reconciliation, access revocation, secret operations, and diagnostics. It refines approved project NFR-01, NFR-04–NFR-08 without changing the access matrix or choosing provider implementation details reserved for U2 NFR Design and Infrastructure Design. It also inherits the approved U1 local-operation boundary. It does not authorize code changes or runtime identity/catalog mutations.

## Planning checklist

### Analyze approved design and requirements

- [x] Review U2 Functional Design artifacts and the approved U2 plan.
- [x] Review approved requirements FR-06–FR-10, FR-12; NFR-01, NFR-04–NFR-08; and stories US-03–US-08.
- [x] Preserve Keycloak as identity/group source and Polaris as the catalog authorization authority.
- [x] Keep RustFS authorization and credential vending in U3, and CLI/Spark end-to-end behavior in U4.
- [x] Separate measurable NFR expectations from OIDC configuration and implementation choices.

### Plan approval gate

- [x] Collect answers to all clarification questions below. User approved the recommended answer for each question with “approved and continue”.
- [x] Resolve ambiguity and check consistency with the approved access matrix and Functional Design.
- [x] Obtain explicit approval of this completed plan before generating NFR Requirements artifacts.

### Generate NFR Requirements artifacts after plan approval

- [x] Generate `aidlc-docs/current/construction/unit-2/nfr-requirements/nfr-requirements.md`.
- [x] Generate `tech-stack-decisions.md` documenting constraints without selecting implementation details reserved for later design.
- [x] Validate traceability to approved requirements/stories and identify Build and Test evidence.
- [x] Present both artifacts for explicit NFR Requirements approval.

## NFR clarification questions

Replace each `[Answer]:` with a selected option or a concrete alternative.

### Question 1 — Canonical local Keycloak issuer

The same token issuer must work in a browser on the host, from host-side bootstrap clients, and from Polaris on the Compose network. Which local hostname contract should the later design verify?

A) Use `http://keycloak.localhost:8080/realms/lakehouse` as the canonical issuer; publish Keycloak only on host loopback and add `keycloak.localhost` as a Compose network alias so host and container resolution reach the correct endpoint (Recommended: one issuer string without a manual host-file edit; validate host/browser and Docker DNS behavior on the supported platform).

B) Use a manually configured local DNS/hosts name that resolves to loopback on the host and to Keycloak from the Compose network; document the required host setup.

C) Other (provide the exact canonical issuer URL and how it resolves from host, browser, and Polaris).

[Answer]:A

### Question 2 — Keycloak-to-Polaris entitlement reconciliation trigger

Keycloak group membership changes must be reflected in Polaris principal-role assignments. How should reconciliation be initiated?

A) Run an explicit, idempotent reconciliation command after each membership change; a change is not considered complete until reconciliation succeeds (Recommended for the local stack: no background service or event listener, with an observable completion step).

B) Trigger synchronous reconciliation from the supported user/group management workflow so a membership update returns only after Polaris converges.

C) Run a periodic background reconciler; specify the maximum interval and outage behavior.

D) Other (specify trigger and how failed or delayed reconciliation is reported).

[Answer]:A

### Question 3 — Maximum access-revocation delay

After removing a user from a Keycloak product group and successfully reconciling Polaris, how long may existing access tokens continue to authorize requests?

A) At most 5 minutes; use a short access-token lifetime and verify the worst-case expiry/revocation path (Recommended balance for local human access).

B) At most 1 minute; require a mechanism that invalidates or rechecks tokens/entitlements within that bound.

C) At most 15 minutes; document the longer exposure window and test it.

D) Other (specify the maximum permitted elapsed time).

[Answer]:A

### Question 4 — Human access-token lifetime and renewal

What maximum lifetime should apply to human OIDC access tokens used with Polaris?

A) 5 minutes; clients renew through the supported interactive OIDC session, and Polaris must not accept expired tokens (Recommended and aligned to a 5-minute revocation target).

B) 15 minutes; accept a matching revocation window up to 15 minutes.

C) Other (specify access-token lifetime and whether refresh tokens may be issued/stored by clients).

[Answer]:A

### Question 5 — Writer client-secret rotation

The writer uses OAuth client credentials. What operational rotation expectation should the NFR require?

A) Operator-managed rotation at least every 90 days and immediately after suspected exposure; support a controlled overlap so the writer can move to the replacement secret without logging either value (Recommended for this local deployment).

B) Rotate only after suspected exposure or service-owner change; document the manual procedure and remove the old secret immediately after validation.

C) Other (specify cadence, overlap, and emergency response expectation).

[Answer]:A

### Question 6 — Identity-provider outage behavior

How should new and existing Polaris requests behave while Keycloak is unavailable?

A) Fail closed: no request may gain authorization through cached identity/group data or a fallback Polaris credential; report the dependency failure without secrets (Recommended and consistent with approved NFR-05).

B) Continue accepting already-issued, unexpired JWTs that Polaris can validate locally, but deny new token issuance and document the maximum remaining-token lifetime.

C) Other (specify allowed behavior and maximum stale-authorization window).

[Answer]:A

### Question 7 — Security diagnostics and audit detail

What identity/authorization event detail may appear in local operator diagnostics?

A) Record operation outcome, provider, principal username, product role, catalog, and failure category; never record token contents, passwords, client secrets, or full authorization headers (Recommended: actionable while keeping credentials out of logs).

B) Record only aggregate success/failure counts and provider status; omit principal names and role names.

C) Other (specify permitted fields and retention expectations).

[Answer]:A

## Answer analysis

The user approved the recommended option for each question. These choices are consistent with the approved Functional Design and global NFRs: one `keycloak.localhost` issuer reachable by the host and Compose clients; explicit reconciliation after each Keycloak group change; a maximum five-minute access-token/revocation window; writer client-secret rotation at least every 90 days and immediately after suspected exposure; fail-closed behavior for product requests during Keycloak outage; and actionable diagnostics without credential material. The `.localhost` resolution behavior, exact Polaris token/role behavior, the rotation overlap mechanics, and outage/failure handling are verification items for later NFR Design, Infrastructure Design, and Build and Test. No implementation details beyond these measurable requirements are selected here.

## Gate

**Plan status: APPROVED.** Both NFR Requirements artifacts were reviewed and approved. U2 NFR Design planning may proceed. No code or runtime identity/catalog state was changed.
