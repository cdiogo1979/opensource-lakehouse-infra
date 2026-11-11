# Execution Plan — Materialized View Promotion

| Stage | Decision | Reason |
|---|---|---|
| Probes P1, P2 | Execute | The login and the marker decide the design |
| Application Design | Execute (short) | New module (MV deployer) and a new file type in product repositories |
| Units | Two | U1 platform (infra repository), U2 sample product (sample repository) |
| Functional Design | Execute for U1 | Deploy plan rules (create, replace, drop, keep, skip) |
| Code Generation | Execute | U1 then U2 |
| Build and Test | Execute | Unit and property tests; live UAT deploy of the example MV, a change, and a removal |
| Deploy | Execute | `start-airflow`; sample repository merge after approval |

## Canonical knowledge impact
| Path | Class | Reason |
|---|---|---|
| `functional-design/airflow-workflows.md` | UPDATE | New task and DAG |
| `functional-design/starrocks-sql-access.md` | UPDATE | Writer login path for the deployer; managed MVs |
| `functional-design/materialized-view-promotion.md` | CREATE | Only if the deployer is a separate component (decided at Application Design) |
| `application-design.md` | UPDATE | Promotion path for MVs |
| sample `knowledge/tpch/*`, `knowledge/opensource-lakehouse/*` | UPDATE | MV files and rules |
