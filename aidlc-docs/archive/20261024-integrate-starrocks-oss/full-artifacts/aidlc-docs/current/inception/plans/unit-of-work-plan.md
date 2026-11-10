# Unit of Work Plan — StarRocks OSS Integration

## Purpose

Decompose the approved StarRocks integration into reviewable implementation units while preserving the approved Application Design boundaries. This is a brownfield Compose project; code organization strategy for greenfield projects does not apply.

## Approved Baseline and Mapping Inputs

- Requirements: `aidlc-docs/current/inception/requirements/requirements.md` (FR-1 through FR-7; NFR-1 through NFR-6).
- Stories: `aidlc-docs/current/inception/user-stories/stories.md` (US-01 through US-05).
- Components: `aidlc-docs/current/inception/application-design/` (StarRocks Runtime, Identity Provisioning, SQL Bootstrap, shared lakehouse services, SQL Clients and Operations).
- Canonical knowledge inventory: `aidlc-docs/current/inception/plans/execution-plan.md` (project application design update, lakehouse workload/access update, and new StarRocks analytics functional design).
- Sibling Airflow/Jenkins remains out of scope; existing Hive/Spark/Jupyter/RustFS services and data must be preserved.

## Planning Tasks

- [x] Read the approved requirements, stories, Application Design, and execution-plan knowledge inventory.
- [x] Resolve unit grouping, dependencies, ownership, technical deployment, domain boundary, and cross-cutting work questions below.
- [x] Analyze answers for ambiguity, contradiction, or missing decomposition rules; add follow-up questions if needed.
- [x] Map each story and requirement to its owning unit and canonical design path.
- [x] Prepare unit definitions, dependency matrix, and story map after plan approval.
- [x] Validate that each story is assigned once, dependencies are acyclic and complete, and unit boundaries match the approved Application Design.
- [x] Obtain explicit approval of this decomposition plan before generating unit artifacts.
- [x] Generate `aidlc-docs/current/inception/application-design/unit-of-work.md` with unit definitions and responsibilities.
- [x] Generate `aidlc-docs/current/inception/application-design/unit-of-work-dependency.md` with the dependency matrix.
- [x] Generate `aidlc-docs/current/inception/application-design/unit-of-work-story-map.md` mapping all stories to units.
- [x] Validate unit boundaries, dependencies, and story coverage.
- [x] Present the generated artifacts for explicit approval; artifacts approved.

## Unit Decomposition Questions

Fill each `[Answer]:` line with an option letter. Choose `D) Other` and describe your choice if no listed option fits.

### Question 1 — Story grouping

How should implementation work be grouped into units?

A) Three component-aligned units: Identity Provisioning; StarRocks Runtime; SQL Bootstrap (catalog, users, and grants). Assign integration checks and docs across those units.

B) Four units: Identity Provisioning; StarRocks Runtime; SQL Bootstrap; and a separate Integration Verification and Operations Documentation unit.

C) One end-to-end unit covering identities, runtime, bootstrap, docs, and verification because this is one local Compose PoC.

D) Other (describe after `[Answer]:`)

[Answer]:A

### Question 2 — Inter-unit dependencies

How should work that depends on identities, runtime readiness, and catalog bootstrap be scheduled?

A) Sequential: Identity Provisioning -> StarRocks Runtime -> SQL Bootstrap -> integrated verification.

B) Build identity provisioning and runtime configuration in parallel; SQL Bootstrap follows both; integrated verification follows bootstrap.

C) Keep all implementation and verification within one coordinated unit, with no unit-to-unit handoff.

D) Other (describe after `[Answer]:`)

[Answer]:A

### Question 3 — Team and ownership alignment

What ownership model should the unit definitions assume?

A) One operator/developer owns all units and follows their dependency order; unit boundaries support review and staged implementation.

B) Separate owners can work independently on identity provisioning and StarRocks runtime, with one owner coordinating SQL bootstrap and integration.

C) Units should be assigned to functional owners (platform identity, data platform, analytics) even if that requires coordinated handoffs.

D) Other (describe after `[Answer]:`)

[Answer]:A

### Question 4 — Technical deployment boundary

How should FE and BE deployment work be represented in the unit plan?

A) Keep FE and BE together in one StarRocks Runtime unit because they form one local deployment and share readiness/persistence concerns.

B) Split FE and BE into separate units so their configuration and lifecycle can be developed independently, then integrate them.

C) Put FE/BE deployment together with SQL catalog bootstrap as one StarRocks service unit; keep identity provisioning separate.

D) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — Business/domain boundary

How should catalog setup and SQL authorization be grouped?

A) Keep catalog registration and SQL user/role/grant provisioning together in SQL Bootstrap because both are reconciled through StarRocks SQL after FE readiness.

B) Split Iceberg catalog integration from SQL user/role/grant management into separate units because they have distinct owners and validation.

C) Group catalog integration with the StarRocks Runtime unit and keep SQL account/grant provisioning separate.

D) Other (describe after `[Answer]:`)

[Answer]:A

### Question 6 — Cross-cutting documentation and verification

Where should shared operations documentation and end-to-end verification be owned?

A) Assign each unit its setup/validation documentation; keep end-to-end query/write/access-matrix verification as a final integrated activity after all units.

B) Create a separate integration unit owning all operations docs and end-to-end validation after the component units.

C) Keep documentation in the runtime unit and assign integration checks to the SQL Bootstrap unit.

D) Other (describe after `[Answer]:`)

[Answer]:A

## Proposed Unit Decomposition and Ownership

Based on the answers, the plan uses three component-aligned units and an integrated verification activity. One operator/developer follows the sequential dependencies. FE and BE stay together; catalog registration and SQL users/grants stay together.

| Unit | Boundary and primary responsibility | Requirements (primary ownership) | Stories (primary ownership) | Canonical design ownership |
|---|---|---|---|---|
| Unit 1 — Identity Provisioning | Extend the existing identity provisioner for the dedicated StarRocks HMS Kerberos identity and scoped RustFS identity/policy. Preserve all existing credentials and identities. | FR-4, FR-5, NFR-1 credential handling, NFR-2 idempotency | US-04 | `knowledge/hive-dremio-rustfs/functional-design/starrocks-analytics.md`; shared identity interactions in `functional-design/lakehouse-workload-and-access.md` |
| Unit 2 — StarRocks Runtime | Add the pinned single-FE/single-BE Compose deployment, mounted config/credential contracts, health/readiness, loopback endpoints, and persistent volumes. | FR-1, FR-7, NFR-1 endpoint exposure, NFR-3, NFR-4, NFR-5, NFR-6 runtime operations | US-05 | `functional-design/starrocks-analytics.md`; project boundary update in `knowledge/hive-dremio-rustfs/application-design.md` |
| Unit 3 — SQL Bootstrap and Catalog Access | Add explicit repeatable bootstrap for the HMS Iceberg catalog and native SQL accounts/roles/grants; support reads and controlled writes through StarRocks. | FR-2, FR-3, FR-6, NFR-1 SQL credential handling, NFR-2 bootstrap idempotency | US-01, US-02, US-03 | `functional-design/starrocks-analytics.md`; shared workload/access update in `functional-design/lakehouse-workload-and-access.md` |

**Shared responsibility:** FR-7 preservation spans all units; Unit 2 owns Compose/service preservation, Unit 1 preserves existing credentials/identities, and Unit 3 avoids destructive catalog/table actions. NFR-6 documentation is authored within each owning unit. End-to-end query, write/readback, access-matrix, persistence, and preservation verification runs as an integrated activity after Units 1–3; it is not a fourth implementation unit. This aligns with the approved canonical inventory and does not add a new domain component.

## Approval Gate

All six answers are complete and mutually consistent. Review this proposed decomposition and explicitly approve the plan before unit artifacts are generated. Generated unit artifacts will be presented for a separate approval before Construction begins.
