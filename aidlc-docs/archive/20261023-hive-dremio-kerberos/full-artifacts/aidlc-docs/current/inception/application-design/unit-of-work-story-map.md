# Story-to-Unit Map

Every approved story has one primary owning unit. Related units are listed where the acceptance outcome crosses component boundaries; they do not change primary ownership.

| Story | Primary unit | Related units | Ownership rationale |
|---|---|---|---|
| US-CAT-01 — Use Hive Metastore as the Iceberg catalog | Unit 1 — Compose, catalog, identity foundation, and storage | Units 3, 4, 5 | Unit 1 owns the catalog service and foundation; ETL and query units consume it. |
| US-CAT-02 — Initialize repeatable sample databases and tables | Unit 3 — Spark runtime and sample ETL | Units 1, 2, 4 | TPCH loader owns database/table creation as the writer; it depends on catalog/storage and identity setup and exposes data to Dremio. |
| US-ID-01 — Create disposable Kerberos identities and credentials | Unit 2 — Identity and permission provisioning | Units 1, 3, 4, 5 | The provisioner coordinates identity creation; KDC owns principal/keytab mechanics and workload units consume the identities. |
| US-ID-02 — Administer in-scope platform components | Unit 2 — Identity and permission provisioning | Units 1, 4, 5 | The provisioner coordinates component-native admin accounts; each component retains its own administrator mechanism. |
| US-ID-03 — Propagate Dremio identity to Hive | Unit 4 — Dremio source and query identity | Units 1, 2 | Dremio owns source authentication and username mapping; KDC/Hive and provisioning supply dependencies. |
| US-JH-01 — Use isolated Jupyter sessions for test users | Unit 5 — JupyterHub and per-user Spark access | Units 1, 2 | JupyterHub/Spark owns notebook isolation and credential mounts; KDC/catalog/storage identities are supplied by foundation/provisioning. |
| US-AUTH-01 — Enforce the two database access profiles | Unit 1 — Compose, catalog, identity foundation, and storage | Units 2, 4, 5 | Hive owns authorization enforcement; Unit 2 coordinates grants and query units demonstrate the effective policy. |
| US-AUTH-02 — Verify Dremio allow and deny results | Unit 4 — Dremio source and query identity | Units 1, 2, 3 | Dremio owns the query path and observable outcomes; Hive policy, grants, and sample data are dependencies. |
| US-AUTH-03 — Verify Spark allow and deny results in Jupyter | Unit 5 — JupyterHub and per-user Spark access | Units 1, 2, 3 | Jupyter/Spark owns the notebook query path; Hive policy, user credentials, and sample data are dependencies. |
| US-JDBC-01 — Create an object in a Dremio Space | Unit 3 — Spark runtime and sample ETL | Unit 4 | TPCH loader creates the matching Spaces/views over JDBC as writer; Dremio owns JDBC capabilities and is a required feasibility dependency. |
| US-DOC-01 — Set up, demonstrate, and clean up the PoC | Unit 1 — Compose, catalog, identity foundation, and storage | Units 2, 3, 4, 5 | Compose/lifecycle owns the overall startup/cleanup sequence; each component unit contributes its own instructions and query examples. |

## Coverage Check

- Approved story count: 11.
- Stories assigned to exactly one primary unit: 11.
- Stories without an owning unit: 0.
- Cross-unit dependencies are represented in [unit-of-work-dependency.md](unit-of-work-dependency.md).
- Dremio Community JDBC permissions, Hive/RustFS authorization, and Dremio storage identity behavior remain feasibility gates; mapping a story to a unit does not claim those gates have passed.
