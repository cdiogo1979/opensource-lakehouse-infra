# Unit of Work Plan — Keycloak + Polaris `default` Bootstrap

## Scope and inputs

This brownfield decomposition implements the approved requirements, US-01–US-08, and Application Design. Airflow, JupyterHub, Jenkins, and StarRocks remain deferred. The default local journey includes Keycloak, Polaris with dedicated PostgreSQL, RustFS, a host bootstrap CLI, and one-shot Spark smoke job. No user data migration or destructive cleanup is planned.

Existing canonical designs at `aidlc-docs/knowledge/hive-dremio-rustfs/` describe the previous FreeIPA/Hive architecture. The approved current-intent Application Design is the target baseline. At closure, canonical knowledge is updated per the execution plan; the prior archive remains immutable.

## Initial unit proposal

The following boundaries are proposed for review; final unit boundaries depend on answers below. Units represent implementation and verification groupings within this repository, not new independently deployed microservices.

| Proposed unit | Candidate scope | Rationale |
|---|---|---|
| U1 — Runtime composition and legacy removal | Compose/default profiles, persistent Keycloak and Polaris PostgreSQL wiring, Polaris and RustFS base services, remove FreeIPA/Hive/MIT Kerberos from the target journey and retire dependent configuration | Establishes the runnable service foundation and prevents legacy services from remaining implicit dependencies. |
| U2 — Identity and catalog authorization | Keycloak realm/client/groups and writer identity; Polaris external OIDC mapping, principal/principal roles, catalogs/namespaces/catalog roles/grants | Identity claims and Polaris RBAC form one authorization contract and need shared role-matrix tests. |
| U3 — Object storage and credential vending | Three RustFS buckets/locations, protected bootstrap provisioning access, Polaris-to-RustFS storage integration and vended credential behavior | Owns storage boundaries and the protocol bridge that must match Polaris authorization. |
| U4 — Bootstrap CLI and Spark verification | Host CLI, ordered coordinator, provider adapters, one-shot Spark smoke job, safe reporting, end-to-end access and rerun checks | Delivers the user journey and integrates the provider units without adding a permanent admin service. |

Proposed dependency order: U1 → U2 and U3 → U4. U2 and U3 may be developed in parallel after U1, but their integration contract must be agreed before U4. Existing components retain their boundaries; the CLI/coordinator is new because it introduces a distinct operator workflow.

## Planning checklist

### Map work to existing components and knowledge

- [x] Read approved execution plan and canonical knowledge impact inventory.
- [x] Read approved Application Design components, methods, services, dependencies, and consolidated design.
- [x] Map requirements and US-01–US-08 to existing/new component responsibilities.
- [x] Identify legacy components to remove from the initial journey: FreeIPA, Hive Metastore/schema-init, and MIT Kerberos/KDC/configuration.
- [x] Keep deferred client integrations out of implementation units unless specifically required to remove a dependency.
- [x] Resolve unit grouping, dependencies, ownership, domain alignment, deployment lifecycle, and repository organization questions below.

### Plan approval gate

- [x] User completed all `[Answer]:` fields.
- [x] Analyze answers for ambiguity; all six answers are consistent with approved requirements and Application Design.
- [x] Present and obtain explicit approval of the completed plan before generating unit artifacts.

### Generate mandatory unit artifacts after plan approval

- [x] Generate `aidlc-docs/current/inception/application-design/unit-of-work.md` with unit definitions, responsibilities, and brownfield code-organization notes.
- [x] Generate `unit-of-work-dependency.md` with dependency matrix and delivery order.
- [x] Generate `unit-of-work-story-map.md` mapping all stories and requirements to units.
- [x] Validate unit boundaries, dependencies, canonical knowledge mapping, and full story coverage.
- [x] Present unit artifacts and obtain explicit approval before Construction.

## Decomposition questions

Replace each `[Answer]:` line with the selected option or a specific alternative.

### Question 1 — Story grouping and unit boundaries

Which decomposition best fits this journey?

A) Use the four proposed units U1–U4 above: runtime foundation, identity/catalog authorization, object storage/credential vending, and CLI/Spark integration (Recommended: provider concerns remain testable while authorization and credential integration are isolated).

B) Combine U2 and U3 into one access-control unit, then use U1 runtime foundation and U2/U3 platform access and U4 bootstrap journey.

C) Use one unit for the entire implementation, with internal modules rather than separate per-unit design cycles.

X) Other (describe after `[Answer]:`).

[Answer]:A

### Question 2 — Dependencies and integration checkpoints

How should provider units coordinate?

A) Implement U1 first; U2 and U3 may proceed in parallel against agreed interfaces; integrate both into U4 with end-to-end checks for group claims, Polaris grants, vended storage scope, and smoke tables (Recommended).

B) Implement all units strictly sequentially in U1 → U2 → U3 → U4 order.

C) Build a shared Compose environment first and develop provider units concurrently against that runtime, integrating continuously into U4.

X) Other (describe after `[Answer]:`).

[Answer]:A

### Question 3 — Ownership and collaboration

How should unit ownership be organized?

A) Treat this as one repository and one implementation owner; use unit boundaries as review/test checkpoints rather than separate team handoffs (Recommended unless multiple contributors are planned).

B) Assign separate owners by unit: runtime, identity/catalog, storage, and workflow/Spark.

C) Other (state the contributor/team structure and handoff expectations).

[Answer]:A

### Question 4 — Business-domain alignment

Should the four role outcomes be split into separate implementation units, or stay with their enforcing provider units?

A) Keep role behavior with its enforcement domains: Keycloak claims and Polaris RBAC in U2, storage/vended credentials in U3, with the full matrix tested in U4 (Recommended: matches the approved component dependencies).

B) Create one separate role-management unit that owns the full role matrix across Keycloak, Polaris, and RustFS.

C) Other (describe the ownership boundary).

[Answer]:A

### Question 5 — Deployment boundaries and service lifecycle

Should all units share one Compose project and lifecycle, or should any become separately deployed?

A) Keep one Compose project for the local journey. `docker compose up` starts only the core long-running services; the Spark smoke job and bootstrap CLI run on demand; deferred services remain opt-in (Recommended: matches the approved single-machine journey).

B) Split identity/catalog/storage into separate Compose projects with independently managed networks and lifecycle.

C) Other (describe the deployment boundary and which units need independent lifecycle).

[Answer]:A

### Question 6 — Brownfield code organization and legacy disposition

Where should new implementation files go, and how should deferred/legacy files be handled?

A) Preserve the current `infra/`, `scripts/`, `docker-compose.yml`, and docs structure. Add provider-specific files under `infra/keycloak/`, `infra/polaris/`, and existing `infra/bucket-init/` or a renamed RustFS location; put the operator CLI in `scripts/`. Remove FreeIPA/Hive/Kerberos from the default setup and delete their code/config only after checking active references; retain unrelated deferred services under explicit opt-in profiles (Recommended).

B) Create a new top-level `bootstrap/` application package and move provider helpers into it; retain the current service tree.

C) Remove all old services and all unrelated deferred components in this intent.

X) Other (describe desired file layout and retention boundary after `[Answer]:`).

[Answer]:A

## Answer review

The user selected option A for all six questions. The four proposed units are retained. U1 establishes a single Compose runtime and removes FreeIPA/Hive/Kerberos from the target default setup; U2 owns Keycloak claims and Polaris RBAC; U3 owns bucket/storage configuration and credential vending; U4 delivers the CLI and Spark journey. U2 and U3 may proceed in parallel after U1, with integration contracts agreed before U4. One implementation owner uses the units as review and verification checkpoints. Deferred services stay opt-in rather than being removed by this intent. The answers are specific and consistent; no follow-up is needed.

## Generation status and gate

The approved four-unit decomposition has been generated in `unit-of-work.md`, `unit-of-work-dependency.md`, and `unit-of-work-story-map.md`. All requirements and all eight stories are mapped; the dependencies and brownfield organization notes are recorded. The generated unit artifacts now await explicit user review and approval before Construction. No application source or runtime services were changed.
