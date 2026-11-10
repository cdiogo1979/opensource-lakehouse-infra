# Unit 3 NFR Requirements Plan — SQL Bootstrap and Catalog Access

## Unit Context

- **Unit:** Unit 3 — SQL Bootstrap and Catalog Access.
- **Approved Functional Design:** `aidlc-docs/current/construction/unit-3-starrocks-sql-bootstrap/functional-design/`.
- **Scope:** Operator-invoked StarRocks SQL bootstrap for the Hive-backed Iceberg catalog, the built-in `root` and application SQL credentials, access policy reconciliation, and safe diagnostics.
- **Out of scope:** Changes to Unit 1 Kerberos/RustFS identity provisioning, Unit 2 FE/BE runtime behavior, Airflow/Jenkins integration, production HA, external identity providers, and end-user Kerberos delegation.
- **Fixed technology and behavior:** Existing Docker Compose project and StarRocks SQL endpoint; existing `.runtime/credentials/` convention; generated per-identity passwords preserved on reruns; root and `admin` remain distinct; writer has DML on existing tables only; broad/conflicting state and credential drift fail closed.

## NFR Assessment Tasks

- [x] **Step 1 — Analyze Functional Design:** Review bootstrap lifecycle, catalog and SQL identity boundaries, selected writer permissions, failure handling, and preservation rules.
- [x] **Step 2 — Establish fixed constraints:** Carry forward the local PoC scope, password file convention, secret redaction, idempotency, and no-destructive-reconciliation behavior.
- [x] **Step 3 — Identify remaining NFR decisions:** Prepare questions for workload scale, invocation/availability, FE readiness and retry behavior, concurrent runs, and diagnostics retention.
- [x] **Step 4 — Resolve questions:** All five answers are A and consistent with approved Functional Design and project requirements.
- [x] **Step 5 — Generate NFR artifacts:** Created `nfr-requirements.md` and `tech-stack-decisions.md` under `aidlc-docs/current/construction/unit-3-starrocks-sql-bootstrap/nfr-requirements/`.
- [x] **Step 6 — Validate and present:** Traced requirements to FR-2/3/6, NFR-1/2, US-01 through US-04, and preservation rules. Artifacts are ready for explicit approval before NFR Design.
- [x] **Step 7 — Record approval:** User approved NFR Requirements and continued to Unit 3 NFR Design on 2026-10-24.

## Questions

Fill each `[Answer]:` line with an option letter. Choose `Other` and describe your choice if none fits.

### Question 1 — Workload and scale

What workload should the SQL bootstrap and catalog-access validation support?

A) The two existing sample databases and the fixed four SQL identities, with occasional manual SQL use; no concurrency, throughput, or query-latency SLA.

B) Define larger data, user, or concurrency targets; provide the values after `[Answer]:`.

C) Other (describe below).

[Answer]: A

### Question 2 — Invocation and availability

What operating model applies to the Unit 3 bootstrap?

A) Operator-triggered local operation; no uptime or recovery-time objective. The operator corrects a failure and reruns the idempotent bootstrap. Airflow/Jenkins automation remains future work.

B) The bootstrap must run unattended from an existing scheduler or CI system; specify the required behavior after `[Answer]:`.

C) Other (describe below).

[Answer]: A

### Question 3 — FE readiness and transient SQL failures

How should the bootstrap handle an FE that is not ready or a transient SQL connection error?

A) Check FE SQL readiness at startup and fail with a redacted actionable error if unavailable; make one attempt per SQL operation and rely on a later safe operator rerun.

B) Wait for FE readiness and retry transient SQL connection errors within a bounded time; specify the maximum wait/retry policy after `[Answer]:`.

C) Other (describe below).

[Answer]: A

### Question 4 — Concurrent bootstrap invocations

How should overlapping runs against the same FE and credential directory be handled?

A) Permit only one active run; a second run exits safely with a redacted busy diagnostic. No concurrent mutations are allowed.

B) Support concurrent runs and ensure all inspection/reconciliation operations remain safe under races; describe the required guarantee after `[Answer]:`.

C) Other (describe below).

[Answer]: A

### Question 5 — Diagnostics and operation history

What diagnostic retention is required for this local PoC?

A) Concise redacted stdout/stderr with per-step and final status; no persistent audit store or log service.

B) Also write a local redacted operation report with an explicit retention/rotation policy; specify it after `[Answer]:`.

C) Add a monitoring or centralized logging service; describe the required signals and retention after `[Answer]:`.

D) Other (describe below).

[Answer]: A

## Fixed Security and Preservation Constraints

- Runtime passwords remain in ignored `.runtime/credentials/` files. Existing project convention is owner-only directories (`0700`) and secret files (`0600`); new Unit 3 password files must follow it.
- Password values, keytabs, Kerberos tickets, RustFS secrets, SQL authentication material, and secret-bearing responses must never appear in tracked files or diagnostics.
- Existing password files are preserved unchanged. Root and `admin` use distinct credentials. Credential drift does not trigger implicit reset or rotation.
- Catalog, users, roles, grants, databases, tables, and data are not dropped or recreated as routine reconciliation. Existing unrelated grants and objects are preserved; conflicting or broader target state fails closed.
- `user_a`, `user_b`, and `write_service_account` receive only the approved Functional Design access. The writer is limited to DML on existing tables in both databases.
- Unit 3 SQL grants do not alter direct Spark, Hive, Kerberos, or RustFS authorization.
- Security Baseline and Resiliency Baseline extensions are disabled. Explicit project security and preservation requirements remain binding. Property-Based Testing remains partial and applies only to qualifying pure functions/serialization if introduced later.
- Integrated Build and Test must separately validate allowed/denied queries and writes, secret handling, rerun behavior, conflict handling, and actual HMS/Iceberg/RustFS compatibility.

## Answer Review

- **Q1 A:** Existing sample databases and four application identities; no concurrency, throughput, or query-latency SLA.
- **Q2 A:** Manual operator invocation, no uptime/RTO, and safe operator rerun; Airflow/Jenkins remains future work.
- **Q3 A:** Check FE readiness before mutation, make one attempt per SQL operation, and rely on a later safe rerun.
- **Q4 A:** Allow only one active mutating run; reject a concurrent invocation without changing state.
- **Q5 A:** Redacted per-operation and final console status only; no persistent audit/logging service.

## Review Status

- **Artifacts ready:** `nfr-requirements/nfr-requirements.md` and `nfr-requirements/tech-stack-decisions.md`.
- **Approval gate:** Approved by the user on 2026-10-24; Unit 3 NFR Design is active.
- **Verification boundary:** These are requirements and technology decisions; no implementation, build, test, or runtime verification is claimed.
- **Approval status:** Recorded; see Step 7.
