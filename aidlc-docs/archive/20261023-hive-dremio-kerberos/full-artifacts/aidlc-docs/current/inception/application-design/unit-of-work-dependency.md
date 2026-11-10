# Unit of Work Dependencies

## Development and Integration Approach

After shared contracts for service names, principal names, Hive database names, RustFS paths, and user mapping are agreed, units can be developed independently. Integrate into the single Compose project in the order shown below. Independent development does not imply separate deployment or an unordered final integration.

## Dependency Matrix

Rows depend on columns. `C` means contract/implementation dependency for integration; `D` means sample data dependency; `I` means full integration depends on the preceding unit.

| Unit | Unit 1: Foundations | Unit 2: Identity | Unit 3: ETL | Unit 4: Dremio | Unit 5: Jupyter |
|---|---:|---:|---:|---:|---:|
| Unit 1: Compose/catalog/storage | — | — | — | — | — |
| Unit 2: Identity/provisioning | C | — | — | — | — |
| Unit 3: Spark/ETL | C | C | — | — | — |
| Unit 4: Dremio | C | C | D | — | — |
| Unit 5: Jupyter/Spark access | C | C | D | — | — |

Units 4 and 5 can be developed independently after shared contracts and integrated in parallel after Unit 3 data exists. Final acceptance of the integrated environment checks both paths together.

## Integration Sequence and Checkpoints

1. **Agree shared contracts** — Compose aliases/ports, realm and principal names, database/table names, warehouse/bucket paths, and user mapping.
2. **Integrate Unit 1: Foundations** — bring up PostgreSQL, KDC, Hive Metastore, RustFS, bucket initialization, and lifecycle ordering. Check catalog/storage/KDC readiness and confirm the authorization mechanism can be evaluated.
3. **Integrate Unit 2: Identity/provisioning** — provision component users and credential scopes against the running foundation. Establish the writer's minimal database-creation/storage-write permissions; determine how test-user grants are applied after database creation.
4. **Integrate Unit 3: ETL** — run the one-shot loader as `write-service-account`, create/populate both Hive databases, then attempt Dremio Spaces and per-table views over JDBC. Record Community feasibility results without using admin as writer.
5. **Integrate Units 4 and 5** — configure Dremio source/identity and Jupyter per-user Spark sessions against the same catalog/data. These units may proceed in either order after shared contracts, but both depend on sample tables for complete access scenarios.
6. **Cross-path acceptance handoff** — document matching allow/deny outcomes and startup/cleanup steps in the owning unit docs. If a feasibility gate fails, stop that acceptance claim and request review of the proposed adjustment.

## External and Deferred Dependencies

- No Airflow or Jenkins service is part of any unit.
- No direct RustFS authorization demonstration is required, although user-specific RustFS credentials remain required for Spark sessions.
- Production authentication, external identity federation, and independently scalable deployment are out of scope.
