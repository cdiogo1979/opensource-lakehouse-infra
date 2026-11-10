# Unit 4 Technology Decisions — Dremio Source and Query Identity

| Area | Decision | Rationale and limit |
|---|---|---|
| Dremio server | Retain the existing Dremio Community 26.0.5 image. | It is the deployed and approved PoC baseline; no upgrade is needed for requirements assessment. Exact Community authorization behavior remains a verification gate. |
| Hive connector | Retain the existing Hive 3.x source and Kerberos/SASL connection to Hive Metastore 3.1.3. | Dremio already connects and queries data. Preserve the source's existing RustFS S3A settings and writer credential. |
| Query identities | Use separate Dremio local accounts named `user_a` and `user_b`. | Matches the approved Hive usernames and enables distinct Dremio-authenticated query sessions. Dremio account creation/configuration is a later implementation task. |
| Hive identity propagation | Use Storage Based with User Impersonation and as-is usernames; keep VDS-based Access Delegation disabled for user-specific view queries. | The intended identity path is Dremio query user → matching Hive effective user. The configured behavior and authorization result must be demonstrated on the pinned deployment. |
| Hive authorization | Evaluate Hive Metastore storage-based authorization over the current RustFS-backed paths. | The checked-in Hive Metastore template currently lacks the storage-based authorization listener/provider declaration. No enforcement claim is made until configuration and all matrix outcomes are verified. |
| Credential storage | Keep generated Dremio local passwords in ignored, permission-restricted `.runtime/credentials/` files. | The PoC already separates local runtime credentials from source-controlled configuration. Never reuse Kerberos or RustFS credentials. |
| Verification interface | Use Dremio SQL/JDBC or REST with distinct local accounts, plus redacted Dremio/Hive evidence. | Direct Hive source queries isolate Hive decisions; Space/view queries are supplemental. No external identity provider, monitoring, or report service is added. |
| Evidence storage | Keep a concise redacted result record in local workflow/runtime evidence. | Supports reproducibility for one local operator without adding a centralized audit system or formal retention commitment. |
| RustFS credentials | Keep the current source-level RustFS credential unchanged for Unit 4. | Explicitly follows user direction. Shared credentials prove source access only, not per-user RustFS authorization. |

## Deferred decisions and feasibility gates

- Confirm Dremio 26.0.5 Community supports provisioning and authenticating the two local query users through a supported interface.
- Confirm the pinned Hive Metastore/RustFS combination enforces the approved per-database matrix under effective-user impersonation.
- If either gate fails, preserve the current stack and return a narrowly scoped adjustment proposal for review before changing architecture or credentials.
