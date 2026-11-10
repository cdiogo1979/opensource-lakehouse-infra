# Unit 1 Functional Design Plan — Identity Provisioning

## Unit Context

Design the business behavior for provisioning the dedicated StarRocks Kerberos identity/keytab and RustFS identity/policy through the existing identity-provisioning boundary. The unit owns FR-4/FR-5, identity-related parts of NFR-1/NFR-2, and US-04.

Relevant current behavior:

- `infra/identity-provisioner/provision-kerberos-identities.sh` creates/reuses named principals, exports keytabs only when absent, verifies them with `kinit`, and provisions existing identities.
- `infra/identity-provisioner/provision-rustfs-identities.py` creates/reuses RustFS identities, attaches named policies, validates credentials, and has optional temporary-object authorization probes for existing identities.
- `scripts/bootstrap-local.sh` creates protected credential files only when absent; `.runtime/credentials/` is ignored and secrets must remain redacted.
- `scripts/provision-identities.sh` runs the existing all-platform provisioner and then renders/restarts Hive configuration.
- The approved design requires a dedicated StarRocks service identity for HMS and a separate RustFS identity scoped to the Iceberg warehouse. Existing credentials must not be implicitly rotated.

## Functional Design Tasks

- [x] Read the Unit 1 definition, US-04, FR-4/FR-5, NFR-1/NFR-2, and canonical identity/workload design.
- [x] Inspect current Kerberos, RustFS, local credential generation, and provisioner orchestration behavior.
- [x] Resolve identity naming, invocation, RustFS scope, drift, and verification from the questions below.
- [x] Resolve the partial-failure continuation rule using `unit-1-functional-design-clarification.md`.
- [x] Complete ambiguity analysis after the follow-up answer; no further ambiguity remains.
- [x] Define the identity provisioning business logic, entities, relationships, and states.
- [x] Define validation, idempotency, failure handling, and data preservation rules.
- [x] Generate `construction/unit-1-identity-provisioning/functional-design/business-logic-model.md`.
- [x] Generate `construction/unit-1-identity-provisioning/functional-design/business-rules.md`.
- [x] Generate `construction/unit-1-identity-provisioning/functional-design/domain-entities.md`.
- [x] Validate traceability to US-04, FR-4/FR-5, NFR-1/NFR-2, and the approved Unit 1 boundary.
- [x] Present the completed functional design for explicit approval before Unit 1 NFR Requirements.

## Functional Design Questions

Fill each `[Answer]:` line with an option letter. Choose `D) Other` and describe your choice if no listed option fits.

### Question 1 — Identity names and credential references

What names should distinguish the StarRocks Kerberos principal and RustFS account while keeping them separate identities?

A) Use `starrocks` in each separate identity system: Kerberos principal `starrocks@<realm>`, RustFS access-key ID `starrocks`, and distinct keytab/secret files.

B) Use purpose-specific names: Kerberos principal `starrocks-hms@<realm>` and RustFS access-key ID `starrocks-storage`, with distinct credential files.

C) Use a host/service principal for HMS (for example `starrocks/<service-host>@<realm>`) and `starrocks` as the RustFS access-key ID.

D) Other (describe after `[Answer]:`)

[Answer]:A

### Question 2 — Provisioning entry point

How should operators invoke StarRocks identity provisioning relative to the existing all-platform identity command?

A) Add StarRocks identities to the existing `scripts/provision-identities.sh` flow; one rerun reconciles all identities and performs the existing Hive config/restart step.

B) Add a StarRocks-only command using the same identity-provisioner component, so an operator can provision StarRocks identities without rerunning unrelated provisioning or restarting Hive.

C) Support both the existing all-platform flow and a targeted StarRocks-only command, sharing the same idempotent provisioning logic.

D) Other (describe after `[Answer]:`)

[Answer]:A

### Question 3 — RustFS policy scope

Which object prefix should the single StarRocks RustFS identity be allowed to read and write?

A) Only the current sample database paths `lake/warehouse/databaseA.db/` and `lake/warehouse/databaseB.db/`.

B) The complete existing Iceberg warehouse prefix `lake/warehouse/`, covering current and future databases under that warehouse.

C) The exact Iceberg warehouse prefix/path from the current Hive configuration, with the policy generated from that value rather than hard-coded sample database names.

D) Other (describe after `[Answer]:`)

[Answer]:A

### Question 4 — Existing-state drift

If the StarRocks principal/account or its local credential reference already exists but authentication or policy validation fails, what should provisioning do?

A) Fail closed with redacted diagnostics and preserve the existing principal, keytab, RustFS secret, and policy for operator reconciliation; never rotate implicitly.

B) Preserve credentials but automatically update the StarRocks RustFS policy to the approved scope, then validate again; stop if authentication still fails.

C) Fail closed by default; allow a separate explicit operator action to replace only StarRocks credentials after manual confirmation.

D) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — Provisioning validation

What verification should the identity-provisioning operation perform before reporting success?

A) Verify the Kerberos keytab can obtain a TGT and the RustFS key authenticates with a non-mutating scoped bucket/list request; leave object-level read/write/deny probes to integrated verification.

B) Also run disposable RustFS object probes for allowed write/read and denied out-of-scope access, with guaranteed cleanup and redacted results.

C) Verify principal/account/policy resources exist only; run all authentication and authorization checks in integrated verification.

D) Other (describe after `[Answer]:`)

[Answer]:A

### Question 6 — Partial failure and retry

If Kerberos provisioning succeeds but RustFS provisioning fails (or vice versa), how should the operation behave?

A) Preserve the successfully created resource, return a redacted per-provider status, exit as failed, and allow an idempotent retry to complete the missing side.

B) Remove only resources created during the failed attempt and report failure, leaving pre-existing resources untouched.

C) Continue all remaining steps, collect errors, then return a failed aggregate status; a later rerun reconciles incomplete work.

D) Other (describe after `[Answer]:`)

[Answer]:A

### Follow-up Question 6a — Continue after provider failure

The selected answer requests per-provider outcomes when Kerberos or RustFS provisioning fails, while the draft's ordered fail-fast flow would skip RustFS after a Kerberos failure. What should the command do after one provider fails?

A) Attempt both independent providers, report each as ready/failed, and return overall failure if either fails. Keep successful resources for a retry.

B) Fail fast in the order Kerberos then RustFS; after a Kerberos failure, report RustFS as not attempted. Retain successful prior resources.

C) Other (describe after `[Answer]:`)

[Answer]:

## Applicability Notes

- Frontend/UI component questions do not apply to this infrastructure identity-provisioning unit.
- TGT refresh inside the running StarRocks service is owned by later NFR and Infrastructure Design; this unit defines only provisioning/authentication of its keytab.
- No code or runtime configuration is changed during Functional Design planning.
