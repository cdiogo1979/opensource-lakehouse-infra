# NFR Requirements — Unit 3 StarRocks SQL Bootstrap and Catalog Access

## Scope

These requirements apply to the local, operator-invoked Unit 3 bootstrap that registers the existing Hive-backed Iceberg catalog, establishes StarRocks SQL credentials, and reconciles the approved user/role access matrix. They refine the approved Unit 3 Functional Design. Unit 1 identity provisioning and Unit 2 FE/BE runtime behavior are dependencies; Airflow/Jenkins automation is future work. Actual catalog compatibility, query/write behavior, authorization, and end-to-end security remain subject to integrated Build and Test.

## Availability and Recovery

- **NFR-1.1 — Operator-triggered best effort:** The bootstrap is manually invoked for this local PoC. No uptime or recovery-time objective applies. After correcting a failure, the operator can rerun the idempotent operation.
- **NFR-1.2 — Readiness preflight:** Before changing SQL state, verify that the StarRocks FE SQL endpoint is available. If it is unavailable, exit with a redacted actionable diagnostic and make no SQL mutations. Starting or recovering FE/BE belongs to Unit 2 operations.
- **NFR-1.3 — Single active run:** At most one bootstrap invocation may mutate a given FE/credential directory at a time. A concurrent invocation exits safely with a redacted busy status and does not mutate SQL or credential state.
- **NFR-1.4 — No automatic retry:** Each SQL operation is attempted once per invocation. On transient failures, preserve completed additive changes, return failure, and let the operator rerun after the cause is corrected. Do not perform automatic rollback or destructive compensation.
- **NFR-1.5 — Safe partial completion:** A failed run must leave existing catalog objects, SQL accounts, grants, passwords, and data intact. Additive work completed before failure may remain; a later rerun must inspect state and continue safely.

## Scale and Performance

- **NFR-2.1 — Fixed PoC scope:** Support the two existing sample databases (`databaseA`, `databaseB`) and four application SQL identities (`admin`, `user_a`, `user_b`, and `write_service_account`), plus the built-in `root` bootstrap identity. No dynamic identity fleet or horizontal scaling is required.
- **NFR-2.2 — Interactive workload:** The target is occasional manual SQL use against the existing sample databases. No concurrent-query, throughput, query-latency, or bootstrap-completion SLA is established. Bootstrap mutation concurrency is separately restricted by NFR-1.3.
- **NFR-2.3 — Functional completion:** The bootstrap reports success only after prerequisite checks, catalog/account/grant reconciliation, and the defined account authentication checks complete. An observed duration may be recorded during Build and Test but is not a service guarantee.

## Security and Credential Handling

- **NFR-3.1 — Host file protection:** Store generated SQL passwords under ignored `.runtime/credentials/`. The containing runtime/credential directories use owner-only mode (`0700`); individual password files use owner read/write mode (`0600`), matching the existing project convention.
- **NFR-3.2 — Credential preservation:** Generate a password file only when absent. Preserve existing file contents unchanged and do not rotate credentials implicitly. Keep built-in `root` and application `admin` passwords distinct.
- **NFR-3.3 — Secret redaction:** Passwords, SQL authentication material, keytabs, Kerberos tickets, RustFS secrets, and secret-bearing server responses must not appear in tracked files, stdout/stderr, or diagnostics. Report safe identity names and failure categories only.
- **NFR-3.4 — Identity boundary:** Use the Unit 1 StarRocks service Kerberos and RustFS identities for HMS/object-store access. Do not propagate SQL client identities to HMS or RustFS. SQL grants govern StarRocks SQL sessions only.
- **NFR-3.5 — Least privilege:** Enforce the approved access matrix, including writer DML on existing tables only. No target account receives broader direct or inherited privileges than its approved scope. (FR-6)

## Reliability and State Preservation

- **NFR-4.1 — Idempotent rerun:** A repeat run against compliant state validates and reuses it without changing password contents, unrelated grants, catalog/data objects, or existing tables.
- **NFR-4.2 — Fail closed on drift:** Existing-account/password mismatch, conflicting catalog configuration, or broader-than-approved effective grants cause a redacted failure. Do not reset passwords, revoke unrelated grants, or rewrite conflicting objects automatically.
- **NFR-4.3 — Shared data preservation:** Routine bootstrap and recovery never drop/recreate Hive databases, Iceberg tables, RustFS objects, SQL identities, catalog entries, or unrelated platform services. Writer verification uses a disposable table or reversible test data only.
- **NFR-4.4 — Connectivity versus authorization:** Report FE, HMS/Kerberos, RustFS, catalog, and SQL authorization failures as distinct categories where diagnosable. Do not classify dependency connectivity failures as access denials.

## Diagnostics and Maintainability

- **NFR-5.1 — Console diagnostics:** Emit concise per-operation and final status to stdout/stderr with a safe failure category and remediation guidance. Do not include secret values or sensitive response bodies.
- **NFR-5.2 — No persistent diagnostic service:** Do not add a local audit database, persistent report store, monitoring stack, centralized logging, or alerting service for this PoC.
- **NFR-5.3 — Existing project workflow:** Keep the bootstrap within the existing local Docker Compose/operator workflow. Airflow/Jenkins integration and unattended scheduling are out of scope.
- **NFR-5.4 — Operator documentation:** Document prerequisites, expected FE readiness, credentials, account mapping, safe rerun behavior, conflict resolution boundary, output interpretation, and access matrix.

## Verification Criteria for Integrated Build and Test

1. An unavailable FE causes a redacted failure before SQL mutations; ready FE allows the bootstrap to proceed.
2. Concurrent invocation is rejected safely while one run is active, with no overlapping SQL/credential mutation.
3. A compliant rerun preserves password file contents, unrelated grants, and catalog/table/data objects; a partial additive run can be safely completed by a later rerun.
4. New password directories/files have the required `0700`/`0600` modes, remain Git-ignored, and are not printed. Root and `admin` use distinct credentials.
5. Existing credential drift, conflicting catalog state, and broader target grants fail closed without implicit reset, cleanup, or rotation.
6. Output and diagnostics are reviewed for passwords, keytabs, tickets, RustFS secrets, and sensitive SQL responses.
7. Demonstrate the approved query and write allow/deny matrix against real Hive/Iceberg/RustFS dependencies; distinguish connectivity errors from SQL authorization denials.
8. Verify writer DML against a disposable or reversible target and confirm it cannot perform database/table DDL or StarRocks administration.

## Traceability

These requirements refine **FR-2**, **FR-3**, **FR-6**, **FR-7**, **NFR-1**, and **NFR-2**, and support **US-01** through **US-04**. They preserve the approved Functional Design's catalog type, identity boundaries, access matrix, writer scope, fail-closed behavior, and non-destructive reconciliation. Unit 1/2 runtime verification and actual integration compatibility remain for Build and Test.

## Extension Applicability

- Security Baseline extension: disabled; explicit password, identity, least-privilege, and redaction requirements above remain binding.
- Property-Based Testing extension: partial; these NFRs do not independently require pure-function or serialization behavior.
- Resiliency Baseline extension: disabled; the selected manual, best-effort, no-automatic-retry behavior remains binding.
