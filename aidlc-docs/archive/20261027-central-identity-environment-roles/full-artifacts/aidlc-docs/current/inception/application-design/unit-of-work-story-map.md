# Unit of Work Story Map — Central Identity and Environment Access

Each story has one primary unit. Cross-component effects are verified in the primary unit and again during integrated verification.

| Story | Capability | Primary unit | Requirement trace | Primary acceptance evidence |
|---|---|---|---|---|
| US-01 — Manage human identities and role membership centrally | FreeIPA users, groups, service identities | Unit 1 — FreeIPA Identity Foundation | Identity and role matrix; identity integration | Role groups resolve, users authenticate, service identity remains non-interactive |
| US-02 — Reconcile group membership to data-access policies | Directory-to-RustFS role lifecycle | Unit 2 — RustFS Policies and Reconciliation | Identity integration; authorization; safety | Add/remove membership changes effective RustFS policy; reconciliation fails closed and verifies state |
| US-03 — Keep production data in the existing lake bucket | Existing production object/database preservation | Unit 2 — RustFS Policies and Reconciliation | Storage layout; migration safety | Existing objects preserved; production DB locations explicit; conflicts stop safely |
| US-04 — Isolate development and UAT data | New bucket and database location setup | Unit 2 — RustFS Policies and Reconciliation | Storage layout; authorization | Buckets created idempotently; development/UAT paths explicit; no prod fallback |
| US-05 — Enforce developer read-all and development-write access | Direct Spark/RustFS allow and deny | Unit 2 — RustFS Policies and Reconciliation | Role matrix; authorization | S3 read/write probes match developer scope; integrated Spark check in Unit 3 |
| US-06 — Enforce analyst read-only production access | Production-only S3 read access | Unit 2 — RustFS Policies and Reconciliation | Role matrix; authorization | Analyst reads production; dev/UAT reads and all writes denied |
| US-07 — Run ETL with dedicated writer identity | Existing non-interactive writer remains broad | Unit 2 — RustFS Policies and Reconciliation | Role matrix; identity integration; safety | Writer reads/writes all approved buckets; credentials preserved and not exposed to notebooks |
| US-08 — Authenticate human notebook users with FreeIPA | LDAP/TLS login and group-based spawning | Unit 4 — JupyterHub Per-User Spark Identity | Identity integration; verification | Valid approved users authenticate; invalid/non-member/service users are rejected |
| US-09 — Use the requesting user’s identity for notebook Spark | Per-user Kerberos/S3 identity and revocation | Unit 4 — JupyterHub Per-User Spark Identity | Identity integration; authorization | No cross-user credential access; Spark allow/deny follows role; revoke stops active session |
| US-10 — Enforce StarRocks query permissions from directory roles | StarRocks LDAP Group Provider and native roles/grants | Unit 5 — StarRocks LDAP Group Roles | Authorization; verification | SQL role matrix passes; StarRocks RBAC is not claimed to protect direct Spark requests |
| US-11 — Replace test users safely | Staged retirement, preservation and rollback | Unit 6 — Staged Cutover and Integrated Verification | Migration safety; verification | Old users denied after replacement verification; admin/writer/data/workspaces preserved |

## Integrated verification

After Units 1–5, run the complete allow/deny matrix through Jupyter/Spark/HMS/RustFS and StarRocks native RBAC, verify user revocation behavior, and confirm retained production objects and the writer's RustFS S3 key. Unit 6 owns the final cutover evidence; passing a single query path does not satisfy other enforcement paths.
