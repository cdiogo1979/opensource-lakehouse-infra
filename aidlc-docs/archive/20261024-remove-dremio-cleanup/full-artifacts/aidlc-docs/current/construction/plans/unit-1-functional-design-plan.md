# Unit 1 Functional Design Plan — Retained Lakehouse Workload

## Unit Definition

Use the existing lakehouse workload boundary documented in `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/lakehouse-workload-and-access.md`. The unit preserves the Spark-to-Hive/RustFS TPCH ETL and removes the optional Dremio-only JDBC phase. It introduces no new business entities, public API, or data transformation.

## Functional Design Steps

- [x] Review the approved requirements, canonical workload design, and component inventory.
- [x] Map retained workload behavior and removed Dremio behavior to FR-2 and FR-5.
- [x] Document retained data flow and integration boundaries.
- [x] Document workload invariants and expected failure behavior.
- [x] Assess domain entities; mark new entity modeling not applicable because schemas and tables are preserved.
- [x] Assess PBT applicability under the selected partial mode.
- [x] Check whether any design clarification is required; none identified within the approved scope.

## Functional Design Artifacts

- `construction/unit-1/functional-design/business-logic-model.md`
- `construction/unit-1/functional-design/business-rules.md`
- `construction/unit-1/functional-design/domain-entities.md`

## Testable Properties

- No new pure helper or serialization logic is planned by this design. PBT-02/03/07/08 apply if implementation changes create such pure logic.
- The retained workload's integration behavior is verified with focused examples/smoke checks in Build and Test; no property test is defined for external service I/O.
