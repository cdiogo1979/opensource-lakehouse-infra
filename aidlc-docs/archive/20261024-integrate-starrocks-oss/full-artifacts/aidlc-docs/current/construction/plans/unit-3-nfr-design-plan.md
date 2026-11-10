# Unit 3 NFR Design Plan — SQL Bootstrap and Catalog Access

## Unit Context

- **Unit:** Unit 3 — SQL Bootstrap and Catalog Access.
- **Inputs:** Approved Functional Design and NFR Requirements under `aidlc-docs/current/construction/unit-3-starrocks-sql-bootstrap/`.
- **Design focus:** Secret-safe SQL setup, bootstrap execution components, single-run coordination, readiness/failure flow, catalog reconciliation, and operator diagnostics.
- **Fixed scope:** Manual local Compose workflow; no automatic retry; only one active mutating run; no new audit/logging service; preserve all existing state; writer DML on existing tables only.
- **Out of scope:** Airflow/Jenkins integration, Unit 1 identity provisioning changes, Unit 2 runtime changes, production HA, and external identity providers.

## Documentation Findings — Credential-Bearing SQL

- The official [StarRocks CREATE USER documentation](https://docs.starrocks.io/docs/sql-reference/sql-statements/account-management/CREATE_USER/) allows native passwords as plaintext or ciphertext. The pinned project image is StarRocks 4.1.6, so the supported syntax must be confirmed against its corresponding release behavior before implementation.
- The official [Iceberg catalog documentation](https://docs.starrocks.io/docs/data_source/catalog/iceberg/) shows S3-compatible catalog setup using `aws.s3.access_key` and `aws.s3.secret_key` properties in `CREATE EXTERNAL CATALOG`.
- StarRocks [logging documentation](https://docs.starrocks.io/docs/administration/management/logs/) describes FE profile logs containing SQL statement text and audit logs recording detailed query information. The [AuditLoader schema](https://docs.starrocks.io/docs/administration/management/audit_loader/) includes an original `stmt` field.
- **Design consequence:** Do not assume credentials embedded in user/catalog DDL are automatically redacted from FE logs or other SQL history. The approved NFR prohibits secrets in diagnostics. Confirm a safe supported handling pattern for the pinned version before implementing credential-bearing statements; if no pattern satisfies the approved NFR, stop and return the conflict for explicit resolution.

## NFR Design Tasks

- [x] **Step 1 — Analyze NFR Requirements:** Review availability, no-retry behavior, single-run requirement, file protection, no-secret diagnostics, idempotency, and compatibility boundary.
- [x] **Step 2 — Identify applicable design patterns:** Evaluate secure configuration, fail-fast preflight, serialization, idempotent reconciliation, and observable operator actions. Production HA, audit aggregation, and persistent monitoring are out of scope.
- [x] **Step 3 — Identify implementation choices needing clarification:** Prepare questions on SQL credential/log safety, bootstrap execution location, local lock behavior, and handling when no safe secret path is available.
- [x] **Step 4 — Resolve questions:** All four answers are A and preserve the approved NFR Requirements.
- [x] **Step 5 — Generate NFR design artifacts:** Created `nfr-design-patterns.md` and `logical-components.md` under `aidlc-docs/current/construction/unit-3-starrocks-sql-bootstrap/nfr-design/`.
- [x] **Step 6 — Validate and present:** Traced the design to FR-2/3/6/7, NFR-1/2, US-01 through US-04, and official StarRocks documentation. Artifacts are ready for explicit approval before Infrastructure Design.
- [x] **Step 7 — Record approval:** User approved NFR Design and continued to Unit 3 Infrastructure Design on 2026-10-24.

## Questions

Fill each `[Answer]:` line with an option letter. If a decision would weaken an approved NFR, identify that explicitly; the NFR requirement must be reopened and approved before proceeding.

### Question 1 — Credential-bearing SQL and FE logs

The catalog DDL requires RustFS credential properties, and account DDL can carry password material. StarRocks documentation describes SQL text in FE profile/audit logging. How should the design proceed while preserving the approved no-secret-in-diagnostics requirement?

A) Require a supported and verified method for the pinned StarRocks version to prevent plaintext passwords, password verifiers, and RustFS secrets from reaching FE logs, query history, command arguments, or diagnostics. If no such method can be demonstrated, stop before applying credential-bearing DDL and return the incompatibility for explicit resolution.

B) Allow credential-bearing DDL to appear in local FE logs if log files are owner-protected and retained only locally. This relaxes the approved no-secret-in-diagnostics requirement and requires reopening NFR Requirements.

C) Other (describe below).

[Answer]: A — require a supported, verified log-safe path for the pinned release; stop before real credential DDL if none can be demonstrated.

### Question 2 — Bootstrap execution boundary

Where should the operator-triggered SQL bootstrap execute?

A) A host-side project script connects to the existing FE through its loopback SQL endpoint; it uses an already available host client/library and protected file inputs.

B) A host-side project script uses `docker exec` to invoke the SQL client in the existing FE container; do not add a long-running or helper Compose service.

C) A one-shot helper container attached to the existing Compose network; it exits after bootstrap and does not persist state.

D) Other (describe below).

[Answer]: A — use a host-side project script connecting to the FE loopback SQL endpoint.

### Question 3 — Single-run lock design

NFR-1.3 requires rejecting overlapping mutations. Which lock boundary should the design use?

A) An owner-only host lock in the project's ignored `.runtime/` state, keyed to this project/FE. Acquire it before credential or SQL mutation and release it on normal exit; stale-lock handling must fail safely.

B) A lock held inside the StarRocks FE container, coordinated through the operator's Docker invocation; describe the mechanism after `[Answer]:`.

C) Other (describe below).

[Answer]: A — use a project-local owner-only lock in ignored `.runtime/` state; ambiguous stale locks fail safely.

### Question 4 — Credential-safe failure when no supported path exists

If the pinned StarRocks version records sensitive DDL in a log that cannot be safely redacted or disabled without violating other approved behavior, what should the bootstrap do?

A) Fail closed before submitting the secret-bearing statement. Document the incompatibility and require an explicit requirements/design change before attempting another approach.

B) Submit the statement after warning the operator, and rely on manual log cleanup. This changes the approved preservation and secret-handling contract and requires reopening NFR Requirements.

C) Other (describe below).

[Answer]: A — fail closed before submitting any credential-bearing statement if the approved secret-safety condition cannot be met.

## Fixed Design Constraints

- Password generation remains create-on-absence using the project's existing cryptographic random generation capability; files stay under `.runtime/credentials/` with the approved modes and are not overwritten.
- Root and `admin` remain distinct; all target SQL identities must authenticate against their protected credential files before success.
- No password, password verifier, RustFS secret, keytab, ticket, or sensitive SQL response may appear in tracked artifacts, command-line arguments, stdout/stderr, FE diagnostics, or query/audit history.
- Catalog and account reconciliation remains additive and fail-closed. Do not reset passwords, revoke unrelated grants, or drop/recreate existing objects.
- The concrete SQL syntax and any FE logging behavior must be verified against StarRocks 4.1.6, the pinned project image.
- No code, SQL, image build, tests, or runtime mutations are part of this planning step.

## Answer Review and Design Status

- **Q1 A:** Preserve the approved no-secret-in-diagnostics requirement. Verify the pinned StarRocks 4.1.6 behavior with non-secret canaries; do not submit real credential-bearing DDL unless a supported safe path is demonstrated.
- **Q2 A:** Run a host-side script through the existing FE loopback SQL endpoint; exact host client/library selection is deferred to Infrastructure Design.
- **Q3 A:** Use a project-local owner-only lock in ignored runtime state; resolve ambiguous stale locks safely rather than permitting overlap.
- **Q4 A:** Fail before credential-bearing DDL if no safe supported path exists; document the incompatibility for explicit resolution.
- **Artifacts ready:** `nfr-design/nfr-design-patterns.md` and `nfr-design/logical-components.md`.
- **Approval gate:** Approved by the user on 2026-10-24; Unit 3 Infrastructure Design is active.
- **Feasibility limitation:** Secret-safe execution has not been demonstrated against the running pinned image. This is an explicit precondition for implementation, not a passed verification.
