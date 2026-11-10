# Unit 2 Functional Design Plan — StarRocks Runtime

## Unit Context

- **Unit:** Unit 2 — StarRocks Runtime.
- **Primary story:** US-05 — Run StarRocks in the local PoC.
- **Requirements:** FR-1, FR-7, NFR-1, NFR-3, NFR-4, NFR-5, and NFR-6.
- **Dependencies:** Unit 1 StarRocks Kerberos keytab and RustFS credential contract; existing Compose network and shared lakehouse services.
- **Completion boundary:** One FE and one BE can start, become ready, retain their own state across container recreation, use the protected Unit 1 credential inputs, and expose only the approved loopback host endpoints. Hive Iceberg catalog registration, StarRocks SQL users/grants, and catalog query/write behavior belong to Unit 3.
- **Canonical design ownership:** `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/starrocks-analytics.md`.

## Approved Functional Baseline

- Local single-node deployment consists of one StarRocks FE and one BE.
- FE/BE state uses named volumes and survives container recreation; existing project volumes and services must be preserved.
- Host SQL and FE UI ports bind to loopback only.
- Runtime consumes the read-only Unit 1 keytab and RustFS secret contract. Credential values must not appear in tracked configuration or logs.
- StarRocks uses its service identity for HMS and object-store access; end-user Kerberos propagation is out of scope.
- Unit 2 readiness covers the FE/BE runtime. Unit 3 owns the external Iceberg catalog and SQL authorization setup.
- Image/version selection, detailed health checks, resource sizing, mounts, and Compose wiring are resolved in NFR and Infrastructure Design, not by reopening the approved single-node scope here.

## Functional Design Tasks

- [x] **Step 1 — Analyze unit context:** Review approved requirements, story map, Unit 1 credential handoff, canonical component boundary, and current Compose topology.
- [x] **Step 2 — Define approved baseline and boundary:** Capture FE/BE responsibilities, runtime credential use, persistence, readiness scope, and Unit 3 exclusions.
- [x] **Step 3 — Identify behavior requiring clarification:** Prepare focused questions for ticket-refresh failure and invalid persistent runtime state/partial node failure.
- [x] **Step 4 — Resolve questions:** Q1 A and Q3 A accepted. Clarification 1 A authorizes initial pair initialization only when both volumes are empty on first startup; one-sided empty state or invalid/incompatible existing state fails without reset.
- [x] **Step 5 — Generate functional design:** Created business logic model, business rules, and domain entities under `aidlc-docs/current/construction/unit-2-starrocks-runtime/functional-design/`.
- [x] **Step 6 — Validate and present:** Checked traceability to approved requirements, Unit 2 boundary, and the canonical knowledge inventory. Artifacts are presented for explicit approval before NFR Requirements.
- [x] **Step 7 — Record approval:** User approved Functional Design on 2026-10-24; advanced to Unit 2 NFR Requirements.

## Questions

Fill each `[Answer]:` line with an option letter. Choose the last option, `Other`, and describe your choice if none fits.

### Question 1 — Kerberos ticket refresh failure

The runtime must maintain the service principal's renewable/refreshed TGT lifecycle. If refresh temporarily fails while the current ticket is still valid, how should StarRocks behave?

A) Keep the runtime available while the current ticket is valid, retry refresh at the designed interval, and report a degraded credential state; fail catalog operations naturally if the ticket expires.

B) Mark the runtime not ready immediately on any refresh failure and keep retrying until credentials recover.

C) Stop the StarRocks runtime on refresh failure and require an operator to restart it after correcting the cause.

D) Other (please describe after `[Answer]:` below)

[Answer]: A

### Clarification 1 — First-start initialization

**Answer:** A — initialize FE and BE together only when both volumes are empty on first startup; fail and preserve data if only one side is unexpectedly empty or existing state is invalid/incompatible.

## Answer Review

- **Q1 A:** Keep the runtime available while a valid TGT remains, retry refresh at the designed interval, report degraded credential state, and allow catalog operations to fail if the ticket expires.
- **Q2 A + Clarification 1 A:** Initialize both nodes together only on first startup when both volumes are empty. Fail and preserve data if only one side is empty after initialization or if persisted state is invalid/incompatible.
- **Q3 A:** Report the overall runtime not ready on a node failure, permit configured Compose recovery, and preserve both volumes.

### Question 2 — Missing or invalid FE/BE persistent state

At startup, what should the runtime do if an FE or BE data volume is missing, invalid, or incompatible?

A) Fail startup with an actionable diagnostic and preserve the volume for operator inspection; never delete or reinitialize it automatically.

B) Attempt a documented, non-destructive recovery and fail while preserving the original volume if recovery is unsuccessful.

C) Reinitialize the affected volume automatically so the PoC becomes available, accepting loss of that StarRocks node's local state.

D) Other (please describe after `[Answer]:` below)

[Answer]: A

### Question 3 — FE/BE partial failure behavior

If one StarRocks node becomes unhealthy while the other remains available, what user-visible runtime behavior should the design specify?

A) Report the overall StarRocks runtime as not ready, allow Compose's configured service recovery, and preserve both nodes' persistent volumes.

B) Keep reporting the healthy node as available, report the failed node separately, and leave recovery to the operator.

C) Stop the paired runtime and require coordinated FE/BE recovery by the operator, preserving both volumes.

D) Other (please describe after `[Answer]:` below)

[Answer]: A

## Applicability Notes

- Frontend/UI design is not applicable; this unit adds a SQL engine runtime without a project-owned user interface.
- End-user authentication and grants are owned by Unit 3. Unit 2 handles only the service credentials already defined by Unit 1.
- Security Baseline is disabled for this intent; the specifically approved local-security requirements still apply. Property-Based Testing is partial and applies only if this unit adds pure functions or serialization round-trips. No code or tests are created in this planning step.
- Runtime image compatibility, resource requirements, persistence implementation, endpoint bindings, health-check mechanics, and Compose lifecycle details will be designed in the later NFR/Infrastructure stages.
