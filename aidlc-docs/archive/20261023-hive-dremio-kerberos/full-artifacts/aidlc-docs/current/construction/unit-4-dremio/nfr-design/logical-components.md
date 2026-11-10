# Unit 4 Logical Components — Dremio Source and Query Identity

Unit 4 uses the existing local Compose components only. No additional application, queue, cache, monitoring, centralized audit, or authorization service is introduced.

| Component | Responsibility in Unit 4 | Boundary and evidence |
|---|---|---|
| Dremio Community 26.0.5 | Authenticate the local query users, plan and execute direct-source and supplemental view queries, and pass the query username through the configured Hive impersonation path. | Uses the existing Hive source, Kerberos service identity, bounded proxy configuration, and unchanged RustFS source credential. Dremio auth/source/Space failures are classified separately. |
| Hive Metastore 3.1.3 | Serve catalog metadata and apply the selected storage-based authorization checks under the effective Hive user. | Current template lacks the storage-based authorization listener/provider declaration. That configuration and effective-user enforcement are a feasibility gate, not a claimed capability. |
| Kerberos KDC | Issue service/test identity credentials used by Dremio and other platform flows. | Dremio's service keytab remains distinct from local Dremio passwords and RustFS S3 keys. Test-user keytabs are not substituted for Dremio web/JDBC login. |
| RustFS | Store the existing Hive-backed Iceberg table objects and apply its configured source credential policy. | Dremio uses a shared source-level writer credential. RustFS behavior under individual Dremio users is not inferred from a successful query. |
| Local Unit 4 query runner/operator | Execute one scenario at a time, track expected versus actual results, and classify failures. | No independent service is required. The operator uses distinct Dremio credentials and reruns only failed safe checks after diagnosis. |
| Local evidence files | Store concise scenario results and approved redacted diagnostics. | Keep evidence local; exclude passwords, keytabs, ticket contents, S3 keys, tokens, and credential-bearing URLs. No formal retention period is defined. |

## Query path

`Dremio local user` → `Dremio Hive source` → `Hive Metastore under matching effective user` → `RustFS-backed Iceberg table`

The query runner records the outcome and effective identity evidence locally. A failed component does not imply authorization denial by another component.
