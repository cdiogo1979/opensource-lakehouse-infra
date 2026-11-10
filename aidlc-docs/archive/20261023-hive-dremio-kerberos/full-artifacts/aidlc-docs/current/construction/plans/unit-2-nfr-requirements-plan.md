# NFR Requirements Plan — Unit 2 Identity and Permission Provisioning

## Scope

Assess non-functional requirements for Unit 2's one-shot identity/permission provisioner and its local interactions with Kerberos, Hive/Hadoop, PostgreSQL, RustFS, and Dremio. Unit 2 is limited to the approved one-host Docker Compose PoC. The approved Functional Design requires distinct component credentials, safe idempotent reruns, fail-fast behavior, redacted output, and a later post-ETL reader-grant phase. This stage does not change application configuration or certify authorization feasibility.

## NFR Assessment Checklist

- [x] Confirm identity count and growth/scaling assumptions.
- [x] Confirm provisioning performance expectations and timing target, if any.
- [x] Confirm credential durability, rotation, recovery, and partial-failure behavior.
- [x] Confirm secret storage, account separation, local network, and file-permission boundaries.
- [x] Confirm component-version compatibility and upgrade policy.
- [x] Confirm service readiness, safe retries, reporting, and completion criteria.
- [x] Confirm maintainability and operator support expectations.
- [x] Confirm provisioner interaction and result visibility.
- [x] Generate Unit 2 NFR requirements and technology decisions.
- [x] Validate consistency with the approved Unit 2 Functional Design and requirements.

## Extension Compliance Summary

- **Security Baseline**: Disabled by user choice. Approved functional credential-separation and least-privilege requirements remain mandatory.
- **Property-Based Testing (Partial)**: Reassess if implementation adds pure credential/configuration transformation logic; this planning stage adds no code or tests.
- **Resiliency Baseline**: Disabled by user choice. Functional retry and partial-failure behavior remains in scope.

## Questions

### Question 1 — Provisioning scale

What identity/account volume should the provisioner support?

A) Support the fixed PoC identities (`admin`, `write-service-account`, `user_a`, `user_b`, and the existing Hive service principal) on one Compose host; no bulk provisioning or horizontal scale target (recommended; matches approved scope).

B) Specify additional identity counts or concurrent provisioning needs.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 2 — Provisioning performance

What timing target should apply?

A) Prioritize correct, observable, repeatable account setup; no latency or throughput SLA. Provisioning may run sequentially to preserve safe ordering (recommended; no performance target was approved).

B) Define a maximum duration or concurrency target.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 3 — Credential persistence and rotation

How should credentials persist across normal runs?

A) Preserve existing protected local credentials and component accounts on safe reruns. Rotation is an explicit operator workflow that identifies consumers and requires coordinated updates; no automatic secret rotation (recommended; matches Functional Design).

B) Rotate credentials automatically on each provisioning run.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 4 — Credential security boundary

Which security guarantees should Unit 2 require?

A) Keep each Kerberos and component-native credential distinct in ignored, host-restricted runtime storage; mount only required files read-only; never expose values in logs, command output, or images; keep services local to loopback/private Compose networking (recommended; follows approved requirements).

B) Permit selected credentials to be stored in tracked configuration or shared among component accounts; specify the exception.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — Component compatibility policy

How should Unit 2 handle an unsupported native account or policy interface?

A) Preserve the existing component versions and approved credential boundaries; document the unsupported capability and smallest required adjustment for review before changing versions or broadening privileges (recommended; aligns with feasibility gates).

B) Allow version changes within this unit without separate review if they make provisioning easier.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 6 — Reliability and partial failure

What is the required failure behavior?

A) Require dependencies to be ready; retry only bounded, idempotent availability operations; stop at a failed required account/permission; preserve prior state for safe rerun and report incomplete status (recommended; follows approved Functional Design).

B) Continue setup after failures and mark the overall run successful if some identities were created.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 7 — Maintainability

What implementation structure should be targeted?

A) Keep setup steps component-owned and clearly separated behind small, reviewable interfaces; document prerequisites, credential ownership, and post-ETL grant sequencing; add no separate identity service or monitoring stack unless Infrastructure Design requires a one-shot container (recommended; matches the single-maintainer PoC).

B) Add a persistent identity-management service or administrative UI; specify its operational owner and need.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 8 — Operator visibility

What should provisioning report?

A) Provide concise per-component and per-identity statuses (`created`, `already-present`, `deferred`, `failed`) and safe diagnostics, plus the post-ETL grant command/sequence; omit all credential values (recommended; supports manual operation).

B) Provide a separate report file or interactive interface; specify the format.

X) Other (describe after `[Answer]:`)

[Answer]:A

## Current Status

All NFR answers select the recommended local-PoC defaults and are consistent with the approved Unit 2 Functional Design. The Unit 2 NFR Requirements and Technology Stack Decisions artifacts are generated and ready for review. No application configuration has been changed.
