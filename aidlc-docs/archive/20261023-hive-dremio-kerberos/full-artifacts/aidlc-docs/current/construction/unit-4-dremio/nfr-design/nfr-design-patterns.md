# Unit 4 NFR Design Patterns — Dremio Source and Query Identity

This design applies the approved Unit 4 NFRs to the existing Dremio/Hive authorization demonstration. It introduces no new service, runtime, or deployment component.

## Execution and scale

- Run the four primary user/database scenarios serially: `user_a` on `databaseA` and `databaseB`, then `user_b` on `databaseA` and `databaseB`.
- Keep each query small and deterministic, using an existing table and a bounded result (for example, a count or a small row limit) so the objective is identity and authorization evidence rather than performance.
- Use direct Hive source paths as the primary checks. Exercise the existing Space views only as supplemental checks, classifying Dremio Space/view permission outcomes separately.
- Do not add connection pools, caching, parallel query execution, benchmark workloads, or scale-out mechanisms. No latency or throughput target is set.

## Failure classification and recovery

Classify each failure before retrying:

| Category | Handling |
|---|---|
| Dremio local authentication/account | Stop that user's checks; report account/authentication status without substituting another account. |
| Kerberos, Hive source, or proxy-user configuration | Stop the affected checks; report the failing boundary and preserve logs with secrets redacted. |
| Hive authorization | Count as a policy result only when the effective Hive user and Hive authorization decision are evidenced. |
| Dremio source/Space permissions | Record separately; do not treat as Hive denial evidence. |
| Missing database/table/view | Mark as invalid test precondition, not as an authorization denial. |
| RustFS/S3 credential or object access | Record separately; the source uses a shared RustFS key, so this cannot establish per-user storage authorization. |
| Transient service availability | Preserve state, diagnose the issue, and let the operator rerun only the failed non-destructive query checks. No automatic retries or restart orchestration are added. |

Do not reset volumes, delete sample data, rerun ETL, broaden proxy settings, grant administrative roles, or rotate the RustFS writer key as recovery actions for this unit.

## Identity and evidence protection

- Authenticate each test as a separate Dremio local user with its own password file under ignored, permission-restricted `.runtime/credentials/` storage.
- Keep Dremio's Kerberos service keytab mounted read-only and separate from Dremio web/JDBC passwords and RustFS credentials.
- Preserve the existing Dremio source-level RustFS writer credential for Unit 4.
- Capture only the Dremio username, expected/effective Hive username, database/table, timestamp, expected and actual result, and denial category needed for traceability.
- Redact passwords, access/secret keys, authorization headers, keytab/ticket contents, and credential-bearing URLs before retaining output.
- Keep the evidence local without a separate log store or formal retention period.

## Feasibility and fail-closed behavior

The Hive Metastore template currently lacks storage-based authorization listener/provider configuration. The design does not infer authorization from source connectivity or current writer-credential reads. If setup cannot expose the approved allow/deny matrix under matching effective users, mark the affected acceptance gate unverified, preserve state, and propose the smallest adjustment for review before changing the authorization architecture.
