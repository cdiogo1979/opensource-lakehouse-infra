# Unit of Work Plan

## Purpose and Scope

Decompose the approved Hive/Kerberos PoC into implementation units using the approved component boundaries and the 11 approved stories. Units can be developed independently after shared contracts are agreed, then integrated in dependency order into one local Compose deployment. This stage plans units only; it does not generate unit artifacts or change application code until the approach is approved.

## Existing Components and Canonical Design Mapping

The approved execution-plan inventory and Application Design define these boundaries. No additional runtime boundary is proposed during Units Generation.

| Existing/approved component boundary | Canonical design path | Planned unit responsibility |
|---|---|---|
| Compose orchestration and lifecycle | `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/compose-orchestration.md`; `lifecycle-scripts.md` | Service graph, lifecycle and integration sequencing. |
| Kerberos KDC | `.../functional-design/kerberos-kdc.md` | Realm, principals, keytabs, service identity bootstrap. |
| Metastore PostgreSQL and Hive Metastore | `.../functional-design/metastore-postgresql.md`; `hive-metastore.md` | Metadata persistence, catalog service and Hive-owned authorization integration. |
| RustFS and bucket initializer | `.../functional-design/rustfs.md`; `bucket-initializer.md` | Bucket/warehouse and separate scoped storage credentials/policies. |
| Identity/permission provisioner | `.../functional-design/identity-provisioner.md` | One-shot setup coordination across component-owned identity/permission interfaces. |
| Spark runtime, TPCH generator and TPCH loader | `.../functional-design/spark-runtime.md`; `tpch-generator.md`; `tpch-loader.md` | Sample ETL as `write-service-account`; create/populate Hive databases and Dremio Spaces/views through JDBC. |
| Dremio | `.../functional-design/dremio.md` | Hive source, Kerberos/user mapping, query authorization path and JDBC account boundary. |
| JupyterHub and user Spark sessions | `.../functional-design/jupyterhub.md`; `spark-runtime.md` | Isolated per-user notebook credentials and query path. |
| SQL workloads and operator docs | `.../functional-design/sql-workloads.md`; `lifecycle-scripts.md` | Query scenarios, startup/cleanup and operator instructions. |

The abbreviated `...` paths above are relative to `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/`; the final unit artifact will use complete paths.

## Tentative Unit Decomposition

1. **Compose and catalog/storage foundations** — Compose/lifecycle, PostgreSQL, KDC, Hive Metastore, RustFS and bucket initializer. Owns foundational service configuration and readiness contracts.
2. **Identity and permission provisioning** — the approved one-shot provisioner plus component-native bootstrap inputs. Owns coordination of identities and initial permissions; does not introduce runtime policy authority.
3. **Spark workload and sample ETL** — Spark runtime, TPCH generation/loading, Hive database/table creation, and the Dremio Space/view calls made by the loader as `write-service-account`.
4. **Dremio source and query identity** — Hive source connectivity, Kerberos service identity, local user mapping, and Dremio-side query/access scenarios.
5. **Jupyter and per-user Spark access** — JupyterHub, user-isolated Spark runtime configuration, Kerberos keytabs, RustFS credentials, and notebook query scenarios.
SQL scenarios, lifecycle changes, and operator documentation are delivered within the units that own those behaviors; there is no separate cross-cutting documentation unit.

## Planning Questions

### Question 1 — Story grouping and unit size

Which grouping should guide the final units?

A) Use component-aligned units, assign each story to its primary owner, and record cross-unit integration checkpoints (recommended; fits the approved Application Design).

B) Use vertical feature slices that combine multiple components to deliver each user-visible outcome.

X) Other (describe after `[Answer]:`)

[Answer]: A

### Question 2 — Dependencies and integration order

How should units coordinate shared Compose, identity, and catalog contracts?

A) Implement sequentially in dependency order: foundations, identity/permissions, ETL, Dremio/Jupyter query paths, then operator integration (recommended; the PoC has shared configuration and an explicit critical path).

B) Treat units as independently implementable in parallel after defining shared contracts.

X) Other (describe after `[Answer]:`)

[Answer]: B

### Question 3 — Team ownership

What ownership model should the unit plan assume?

A) One maintainer/operator owns the integrated PoC; units are reviewable change groupings, not separate team assignments (recommended; no multi-team ownership was specified).

B) Assign separate owners to the component-aligned units and plan explicit handoffs.

X) Other (describe after `[Answer]:`)

[Answer]: A

### Question 4 — Deployment and scale constraints

What technical deployment boundary should shape unit independence?

A) Keep one local Docker Compose deployment and optimize units for ordered integration; independent scaling/deployment is not required (recommended; matches the approved PoC scope).

B) Prepare units for independent deployment or multiple environments as part of this intent.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — Business capability alignment

Should unit boundaries follow the user capabilities or the approved technical components?

A) Follow the approved technical component boundaries and use story mapping/integration checkpoints to preserve capability outcomes (recommended; component ownership is established and default boundaries should be retained).

B) Combine components by business capability even when work crosses existing component boundaries.

X) Other (describe after `[Answer]:`)

[Answer]:A

## Answer Analysis

- **Q1, Q3, Q4, and Q5** select component-aligned reviewable units, one maintainer, a single local Compose deployment, and existing technical component boundaries.
- **Q2 and Follow-up Q6** are consistent: units may be developed independently after shared contracts, then integrated in dependency order into one Compose deployment.
- **Follow-up Q7** assigns SQL scenarios, lifecycle updates, and operator documentation to their owning units; no separate documentation unit will be created.
- Greenfield code-organization questions do not apply to this brownfield repository.

### Follow-up Question 6 — Parallel unit work and integration

Given the answers for independent work and one local Compose deployment, which approach should the final dependency plan use?

A) Units may be developed independently after shared contracts, then integrated in dependency order into the single Compose deployment (recommended; preserves both choices).

B) Implement and integrate each unit strictly in dependency order; independent implementation is not needed.

X) Other (describe after `[Answer]:`)

[Answer]: A

### Follow-up Question 7 — Operator documentation grouping

Where should SQL scenarios, lifecycle updates, and operator documentation be assigned?

A) Keep them within the component units that own the relevant behavior; no separate documentation unit (recommended; aligns with component ownership and avoids a cross-cutting standalone unit).

B) Keep a final integration unit for shared SQL scenarios and operator documentation, dependent on all implementation units.

X) Other (describe after `[Answer]:`)

[Answer]: A

### Code Organization — Applicability

This is a brownfield Compose project with established directories and service boundaries, so the greenfield multi-unit directory-structure question is not applicable. The plan will preserve existing project organization unless a component design requires a specific new path.

## Story Coverage Candidates

This is a tentative primary-owner mapping for review; cross-unit dependencies may be recorded in the final story map.

| Story | Candidate primary unit | Related units/integration |
|---|---|---|
| US-CAT-01 — Use Hive Metastore as the Iceberg catalog | Unit 1 | Units 3–5 consume the catalog. |
| US-CAT-02 — Initialize repeatable sample databases and tables | Unit 3 | Units 1–2 provide catalog, credentials and permissions. |
| US-ID-01 — Create disposable Kerberos identities and credentials | Unit 2 | Unit 1 supplies KDC foundations; Units 3–5 consume identities. |
| US-ID-02 — Administer in-scope platform components | Unit 2 | Native admin setup spans Units 1, 4 and 5. |
| US-ID-03 — Propagate Dremio identity to Hive | Unit 4 | Units 1–2 supply Hive/KDC and provisioned identities. |
| US-JH-01 — Use isolated Jupyter sessions for test users | Unit 5 | Units 1–2 supply KDC, catalog, and storage identity setup. |
| US-AUTH-01 — Enforce the two database access profiles | Unit 1 | Hive owns enforcement mechanism; Unit 2 coordinates grants; Units 4–5 consume it. |
| US-AUTH-02 — Verify Dremio allow and deny results | Unit 4 | Unit 2 coordinates grants; query examples/docs stay with Dremio and SQL owners. |
| US-AUTH-03 — Verify Spark allow and deny results in Jupyter | Unit 5 | Unit 2 coordinates grants; notebook query examples/docs stay with Jupyter/Spark owners. |
| US-JDBC-01 — Create an object in a Dremio Space | Unit 3 | Unit 4 provides JDBC/source setup; feasibility gate applies. |
| US-DOC-01 — Set up, demonstrate, and clean up the PoC | Unit 1 | Compose lifecycle owns the overall operator sequence; component-specific instructions are updated in Units 2–5. |

## Generation Checklist

- [x] Obtain all planning answers and resolve ambiguity.
- [x] Approve this unit-of-work plan — user approved on 2026-10-23.
- [x] Generate `aidlc-docs/current/inception/application-design/unit-of-work.md` with unit definitions and responsibilities.
- [x] Generate `aidlc-docs/current/inception/application-design/unit-of-work-dependency.md` with a dependency matrix.
- [x] Generate `aidlc-docs/current/inception/application-design/unit-of-work-story-map.md` with every story assigned to a unit.
- [x] Validate boundaries, dependencies, and complete story coverage.

## Extension Compliance Summary

- **Security Baseline**: N/A — disabled by user choice. Security requirements and feasibility gates remain represented in the unit boundaries.
- **Property-Based Testing (Partial)**: N/A for decomposition; no code or testable pure functions were introduced. Reassess during Functional Design if applicable.
- **Resiliency Baseline**: N/A — disabled by user choice.

## Current Status

The approved plan was executed: five component-aligned units are defined, all 11 stories are mapped to one primary unit, and the dependency/integration sequence is recorded. The three required unit artifacts are complete and awaiting user review and approval. No application changes have been made.
