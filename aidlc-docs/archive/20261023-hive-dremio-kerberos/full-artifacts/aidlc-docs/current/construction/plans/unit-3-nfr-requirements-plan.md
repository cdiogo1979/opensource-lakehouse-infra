# NFR Requirements Plan — Unit 3 Spark Runtime and Sample ETL

## Scope

Assess non-functional requirements for Unit 3's one-shot TPCH generation/ETL and Dremio JDBC exposure. The approved Functional Design runs on the existing local Compose host, uses `write-service-account`, preserves data on reruns, and reports ETL and JDBC outcomes separately. This stage sets measurable quality expectations and does not change application configuration or claim feasibility gates have passed.

## NFR Assessment Checklist

- [x] Confirm fixed data scale and growth assumptions.
- [x] Confirm acceptable generation/load duration and whether a throughput target is needed.
- [x] Confirm data/credential persistence, cleanup, and recovery expectations.
- [x] Confirm secret access, logging, network, and identity isolation boundaries.
- [x] Confirm compatibility/version policy for Spark, Iceberg, Hive, RustFS, and Dremio JDBC.
- [x] Confirm readiness checks, bounded retry behavior, partial failure reporting, and rerun safety.
- [x] Confirm operator visibility and maintainability expectations.
- [x] Generate Unit 3 NFR requirements and technology decisions.
- [x] Validate consistency with the approved Unit 3 Functional Design.

## Answer Resolution

All seven answers select **A** and align with the Unit 3 Functional Design. The fixed scope is TPCH scale factor 1, eight tables in each database, no timing SLA, preserved matching data, restricted writer credentials, pinned versions pending feasibility evidence, bounded readiness retries, partial-result reporting, and no separate monitoring service.

## Questions

### Question 1 — Data scale

What local sample data scale should Unit 3 target?

A) Keep the existing TPCH generator default scale factor 1 and load its eight existing tables into each of the two databases. No growth or concurrent-job target is required (recommended; matches the current generator and fixed PoC scope).

B) Specify a different scale factor or data-volume target.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 2 — ETL performance

What runtime target should apply to generation and loading?

A) Prioritize correctness and clear progress reporting; do not set a duration/throughput SLA for this local PoC (recommended; no performance target was approved).

B) Define a maximum end-to-end duration or throughput requirement.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 3 — Data durability and reset

How should data be handled across ordinary reruns and cleanup?

A) Preserve matching existing tables and data; fail on mismatch; make destructive reset a separately documented and explicitly invoked operator action (recommended; matches the approved non-destructive Functional Design).

B) Recreate both sample databases and their data on every run.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 4 — Credential and runtime isolation

What security boundary should apply to ETL credentials and outputs?

A) Keep the writer keytab/ticket cache and RustFS credentials restricted to the one-shot workload; mount credential files read-only where possible; remove temporary ticket material; never log secrets; retain local/private Compose networking (recommended; follows approved requirements).

B) Specify an alternate local credential-delivery boundary and its tradeoffs.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — Compatibility and Dremio failure policy

How should incompatible component behavior be handled?

A) Keep approved pinned versions and writer privilege boundaries. Record the smallest version/configuration change needed for review if Spark/Hive or non-admin Dremio JDBC behavior is unsupported; do not silently elevate the writer (recommended; matches Functional Design feasibility gates).

B) Permit version changes or broader Dremio privileges within Unit 3 without a separate review.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 6 — Availability, retries, and partial failure

What recovery behavior is required?

A) Require dependencies to pass readiness checks; use bounded retry only for transient availability; stop conflicting data writes; preserve completed ETL if Dremio JDBC later fails; report the run as partial and allow a safe rerun (recommended; preserves state and separates outcomes).

B) Continue after all per-table failures and report only an aggregate result.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 7 — Operator reporting

What should the workload report?

A) Emit concise effective-identity, scale factor, per-database/table schema and row counts, and per-Space/view JDBC status with redacted diagnostics. Do not create a separate monitoring service (recommended; supports manual PoC operation).

B) Specify a durable report format or interactive monitoring requirement.

X) Other (describe after `[Answer]:`)

[Answer]:A

## Extension Compliance Summary

- **Security Baseline**: Disabled by user choice. Approved credential separation, local-only scope, secret redaction, and least privilege remain mandatory.
- **Property-Based Testing (Partial)**: Reassess for pure manifest/naming transformations; no code or tests are introduced by this planning stage.
- **Resiliency Baseline**: Disabled by user choice. Functional bounded retries and safe partial-failure behavior remain required.

## Current Status

Unit 3 Functional Design and NFR Requirements were approved by the user on 2026-10-23. Proceeded to Unit 3 NFR Design. No application configuration has been changed.
