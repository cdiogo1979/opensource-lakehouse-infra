# Unit 1 Functional Design Plan — Runtime Composition and Legacy Removal

## Unit context

U1 provides the runtime foundation for the `default` data-product bootstrap and removes FreeIPA, Hive Metastore, and MIT Kerberos/KDC setup from the target journey. The approved runtime journey includes Keycloak with persistent state, Polaris with dedicated PostgreSQL metadata, and RustFS. The bootstrap CLI and Spark job run on demand in U4. Airflow, JupyterHub, Jenkins, and StarRocks are deferred and remain opt-in; they are not migrated by this intent.

This Functional Design defines logical lifecycle and state ownership only. Compose syntax, profiles, image/version choices, port bindings, health-check commands, volume names, and database topology belong to Infrastructure Design. U1 is infrastructure-heavy; no new user-facing business domain or long-running application service is introduced.

## Planning checklist

### Analyze unit and canonical context

- [x] Read the approved U1 definition and dependency/story map.
- [x] Review approved requirements FR-13/FR-14 and NFR-02/NFR-03/NFR-06.
- [x] Review approved Application Design, including core service boundaries and deferred integrations.
- [x] Review brownfield code structure and legacy component inventory.
- [x] Treat previous canonical architecture as historical baseline; do not let retired FreeIPA/Hive/Kerberos assumptions override this intent.
- [x] Collect all five U1 design answers.
- [x] Review answers against approved NFR-01 and the unit non-destructive boundary.
- [x] Clarify that legacy volume cleanup is a separate explicit action, not normal bootstrap.

### Plan approval gate

- [x] User completed all `[Answer]:` fields.
- [x] Analyze answers for ambiguity and resolve the legacy-volume cleanup boundary.
- [x] Obtain explicit approval of the completed plan before generating Functional Design artifacts.

### Generate Functional Design artifacts after plan approval

- [x] Generate `aidlc-docs/current/construction/unit-1/functional-design/business-logic-model.md`.
- [x] Generate `business-rules.md` with lifecycle, state ownership, retirement, and error rules.
- [x] Generate `domain-entities.md` with the logical runtime resources and ownership relationships.
- [x] Validate alignment with U1 boundaries and requirements; keep implementation details for Infrastructure Design.
- [ ] Present artifacts for explicit Functional Design approval.

## Functional design questions

Replace each `[Answer]:` with a selected option or a concrete alternative.

### Question 1 — Existing legacy state and fresh platform state

The approved journey requires fresh Keycloak/Polaris/object resources and no migration. How should existing legacy persistent state be treated?

A) Do not mount or import old Hive/FreeIPA/KDC state into the new services. Leave existing legacy volumes untouched and provide no automatic deletion; the new platform starts with fresh named persistent state (Recommended: satisfies fresh creation and non-destructive requirements).

B) Delete the old legacy volumes as part of the transition so the machine is clean.

C) Other (identify which state is retained, migrated, or deleted).

[Answer]:B

### Question 2 — Legacy implementation/configuration retirement

What should happen to FreeIPA, Hive, and MIT Kerberos code/configuration after active dependencies are identified?

A) Remove their runtime services, service images/configuration, initialization scripts, and active client references from the project, after checking references; retain immutable AI-DLC archive/history. Keep only material strictly needed by deferred services out of the default journey and clearly marked as deferred (Recommended: makes “remove setup” clear without changing old volumes).

B) Remove them from default Compose but retain all legacy implementation files as dormant code.

C) Other (describe exactly what is deleted versus retained).

[Answer]:A

### Question 3 — Deferred integrations that depend on retired services

Airflow, JupyterHub, Jenkins, and StarRocks remain outside this intent. Some current configuration may still reference Hive or Kerberos. What should U1 do with those integrations?

A) Keep deferred services opt-in only, prevent them from starting by default, and remove or clearly quarantine stale Hive/Kerberos dependencies; document that these profiles are not expected to work until separately migrated (Recommended: preserves project components without claiming compatibility).

B) Retain their legacy dependencies under separate opt-in profiles so the old integrations continue to run alongside the new core.

C) Remove all deferred integrations and their source/configuration now.

X) Other (describe the retention and support boundary).

[Answer]:A

### Question 4 — Core startup/readiness behavior

The approved unit plan says default Compose startup contains only core long-running services; CLI and Spark run on demand. How should the core platform report a partial startup?

A) Each core service has an explicit ready/unavailable state; dependent work must not proceed until all required providers are ready. Preserve healthy service state and data if another service fails, report the unavailable dependency, and do not automatically tear down or delete resources (Recommended).

B) Treat the core stack as ready when any service starts and let the CLI discover failures later.

C) Treat startup as atomic and stop all healthy services if one provider fails.

X) Other (describe the desired readiness/failure contract).

[Answer]:A

## Answer analysis and follow-up

Answers 2–4 are specific and consistent with the approved unit boundaries: remove active FreeIPA/Hive/Kerberos setup after reference checks, keep deferred integrations opt-in and clearly unsupported until separately migrated, and report core readiness per dependency without tearing down healthy state.

Question 1 selects deletion of old legacy volumes. The approved NFR-01 says bootstrap is non-destructive and must never delete bucket data automatically. The answer can be reconciled by making legacy cleanup a separate, explicit transition action rather than part of normal startup/bootstrap. Confirm the exact scope in Question 5 before the plan is submitted for approval.

### Question 5 — Scope and trigger for legacy volume cleanup

Should the cleanup cover only volumes belonging to the retired FreeIPA, Hive/metastore, and MIT KDC services, and require an explicit one-time cleanup action?

A) Yes. Identify the exact legacy volume names first, then provide/run a separate explicit cleanup action for only those retired-service volumes. Normal Compose startup and product bootstrap never remove volumes or RustFS objects. Preserve all RustFS object-store and unrelated service volumes (Recommended: honors the fresh legacy reset while preserving NFR-01).

B) Delete all project volumes, including RustFS object data and deferred-service state, as part of normal bootstrap.

C) Do not delete legacy volumes; leave them detached and unused.

X) Other (describe exact volume scope and trigger).

[Answer]:A

## Gate

All five answers are complete and consistent with approved requirements. Legacy-volume cleanup is a separate explicit action limited to the retired FreeIPA, Hive/metastore, and MIT KDC volumes after exact names are identified; ordinary Compose startup and product bootstrap never delete volumes or RustFS objects. The plan was explicitly approved. Functional Design artifacts have been generated and are awaiting separate artifact approval. No runtime data or volumes have been deleted.
