# Unit 4 Domain Entities — Dremio Query Identity

| Entity | Meaning | Key relationships |
|---|---|---|
| Dremio local user | Account used by a person/client to authenticate to the Dremio server. | `user_a` and `user_b` each map to the matching Hive effective username. Each has its own Dremio credential. |
| Hive service identity | Kerberos service principal used by Dremio to authenticate to the Kerberized Hive Metastore. | `dremio@LAKEHOUSE.LOCAL` submits metadata requests and is permitted to proxy only to the approved local users. |
| Hive effective user | Username evaluated for a Dremio query under Storage Based with User Impersonation. | Derived as-is from the Dremio query username for this PoC. |
| Database access profile | Expected read permissions for one query identity across the sample databases. | `user_a`: `databaseA` only; `user_b`: both databases. |
| Hive source | Dremio source configuration connecting to Hive Metastore and RustFS-backed Iceberg data. | Uses Kerberos, bounded impersonation, Storage Based with User Impersonation, and existing source-level RustFS credentials. |
| Authorization evidence | Redacted record of a query attempt and its effective identity/result. | Links one Dremio user and effective Hive user to a database/table and an allow/deny outcome. |

## Relationship constraints

- Each Dremio query user maps to exactly one same-named Hive effective user in this test scope.
- The Hive service identity is not a substitute for either test user's effective identity.
- The source-level RustFS key is shared by Dremio's Hive source and is not a per-user identity.
- A database access profile is considered demonstrated only when both allowed and denied paths are tested and the effective identity is observable.
