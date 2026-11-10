# NFR Design Patterns — Unit 3 SQL Bootstrap and Catalog Access

## Secure Configuration and Secret Handling

- Keep generated SQL passwords in the existing ignored host credential directory with the approved directory/file modes. Generate only when absent; preserve existing contents.
- Run the bootstrap from the host over the existing loopback FE SQL endpoint, as selected. Use a supported host SQL client/library and protected file inputs. Do not put secrets in process arguments, shell tracing, temporary SQL files, or console output.
- StarRocks user DDL supports plaintext or ciphertext authentication values, and Iceberg S3-compatible catalog creation uses access/secret properties. Do not assume ciphertext prevents exposure: it remains authentication material under the approved NFR.
- **Credential exposure gate:** Before credential-bearing DDL is submitted, demonstrate on the pinned StarRocks 4.1.6 image that passwords/verifiers and RustFS secrets do not appear in FE profile/audit logs, query history, client diagnostics, or process arguments. Use non-secret canary values for this verification. If a supported log-safe route cannot be demonstrated, stop before submitting real credentials and report the incompatibility for explicit resolution.
- A secret-safe client transport alone is insufficient if FE logging records the SQL statement. FE profile logging includes SQL statement text and audit facilities expose statement fields in their schema; see [StarRocks logging](https://docs.starrocks.io/docs/administration/management/logs/) and [AuditLoader](https://docs.starrocks.io/docs/administration/management/audit_loader/). The DDL forms are described in [CREATE USER](https://docs.starrocks.io/docs/sql-reference/sql-statements/account-management/CREATE_USER/) and [Iceberg catalog](https://docs.starrocks.io/docs/data_source/catalog/iceberg/).

## Preflight and Failure Pattern

- Run one preflight before any SQL mutation: acquire the local run lock, confirm expected credential paths/modes, and confirm the FE SQL endpoint is ready.
- If a preflight condition fails, stop before SQL changes and report a redacted failure category. Do not start or restart FE/BE from Unit 3.
- Attempt each SQL operation once. A transient error returns failure; additive work already completed remains and is inspected on a later operator rerun.
- Separate dependency failures (FE, HMS/Kerberos, RustFS, catalog) from authorization denials where the available checks permit.

## Single-Run Coordination

- Use one owner-only lock in ignored project runtime state, keyed to the target project/FE. Acquire it before credential creation or SQL mutation.
- If the lock is held, exit without touching credentials or SQL state and identify the operation as already running.
- Release the lock on normal exit. If a prior process left ambiguous lock state, fail safely and require the operator to confirm that no bootstrap remains active before clearing it. Do not infer that a stale lock authorizes concurrent changes.
- The exact portable lock primitive and interruption cleanup are finalized in Infrastructure Design.

## Idempotent Reconciliation and Authorization

- Inspect the existing catalog, account/password authentication state, and effective grants before changing them.
- Add only missing expected catalog/account/role/grant state. Preserve unrelated grants and objects. Broader-than-approved grants, credential drift, or conflicting catalog properties stop the run without automatic cleanup.
- Validate the effective SQL access matrix, including inherited roles. The writer may perform DML only on existing tables; no database/table DDL or StarRocks administration is granted.
- Use no automatic rollback. A later run must safely inspect partial additive progress and converge after an operator resolves the reported cause.

## Diagnostics and Operations

- Emit concise per-step and final outcomes to stdout/stderr, with identity names and safe failure categories only.
- Do not persist a separate operation report, audit store, monitoring service, or logging service.
- Do not claim success until the catalog/account/grant checks and credential authentication checks pass and the credential exposure gate has been satisfied for the pinned release.

## Scope and Traceability

- **NFR-1.1–1.5:** Manual best effort, fail-fast FE readiness, single-run lock, one attempt per SQL operation, and safe partial reruns.
- **NFR-2.1–2.3:** Fixed sample-data/user scope and no latency or concurrency SLA.
- **NFR-3.1–3.5:** Protected files, secret redaction, separate service identities, and least privilege.
- **NFR-4.1–4.4:** Idempotency, fail-closed drift handling, preservation, and connectivity/error classification.
- **NFR-5.1–5.4:** Console diagnostics and operator documentation without new persistent services.

## Feasibility Status

The design preserves the approved security requirement but does not yet establish that StarRocks 4.1.6 can create the required catalog without retaining credential-bearing SQL in FE logs/query history. That release-specific behavior must be demonstrated with non-secret canaries before real credentials are submitted. If it cannot be demonstrated through a supported mechanism, Unit 3 bootstrap is blocked pending an explicit requirements/design resolution. No runtime validation is claimed here.
