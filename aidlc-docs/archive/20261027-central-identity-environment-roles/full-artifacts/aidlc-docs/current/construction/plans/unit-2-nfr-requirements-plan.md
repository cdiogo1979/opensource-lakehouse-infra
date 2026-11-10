# Unit 2 NFR Requirements Plan — RustFS Role Policies and Reconciliation

## Unit and Approved Functional Baseline

Unit 2 reconciles FreeIPA's canonical users and role-group memberships into RustFS IAM users/groups and exact version-controlled policies for `lake`, `lake-dev`, and `lake-uat`. It preserves all bucket contents, the writer's existing RustFS secret, the current `admin` mapping, and `user_a`/`user_b` pending integrated cutover. The role matrix, deny-on-conflict behavior, safe partial-failure reporting, and positive/negative S3 probes are defined in `construction/unit-2/functional-design/`.

The scope is a local Docker Compose proof of concept. Unit 2 uses an explicit operator-triggered reconciliation; it does not introduce a scheduler or a high-availability control plane. FreeIPA remains isolated at this point and MIT Kerberos remains the active authority. This plan sets quality requirements for the RustFS reconciler only; it does not expand to Hive authorization, Jupyter credential delivery, Ranger/StarRocks, or final identity cutover.

## NFR Assessment Checklist

- [x] Review approved Unit 2 Functional Design and trace reliability, security, performance, audit, recovery, and compatibility concerns.
- [x] Inspect the current RustFS provisioner, bucket initializer, secret mounts, and existing Compose boundaries without changing runtime state.
- [x] Confirm expected number of managed identities, reconciliation frequency, and any completion-time target: A.
- [x] Confirm RustFS API timeout/retry behavior, single-run serialization, and partial-failure recovery expectations: A.
- [x] Confirm protection requirements for root/admin credentials, per-user IAM credentials, transport, logs, and persisted reconciliation state: A.
- [x] Confirm audit event content and retention expectations without capturing credentials or object contents: A.
- [x] Confirm whether a protected pre-change IAM-state export/backup is required and how it can be restored safely: A.
- [x] Confirm pinned RustFS compatibility and whether any new library/service is allowed: A.
- [x] Complete the answer fields and check for conflicts with approved Functional Design.
- [x] Generate `construction/unit-2/nfr-requirements/nfr-requirements.md` and `tech-stack-decisions.md` for review before Unit 2 NFR Design.

## Assessment Boundaries

- **Scale/performance**: The current named roles and three buckets make this a small PoC. No user growth or reconciliation latency SLA has been approved.
- **Availability/recovery**: Reconciliation is explicit and single-host. RustFS/FreeIPA unavailability must stop the run before mutation where possible; partial application must be visible and safely repeatable.
- **Security**: RustFS root credentials are highly privileged; user secrets must be protected and never logged. Data-role probes must use non-root credentials. Unit 4 owns human credential delivery and active session revocation.
- **Consistency**: RustFS admin operations span resources and are not assumed transactional. A concurrent run could race membership or policy changes; the design should define serialization and handling of interrupted runs.
- **Auditability**: Record policy version, run state, safe operation counts, and sanitized failure category. Do not log secret-bearing API bodies, access keys, secret keys, or object contents.
- **Persistence/recovery**: Existing object and IAM state must persist. Determine whether to require an operator-created, protected state snapshot before first policy replacement; no automated backup service is in scope by default.
- **Compatibility/maintenance**: Preserve the pinned RustFS image and existing Python identity-provisioner container unless a documented compatibility gate requires a reviewed change.
- **Verification**: Functional allow/deny coverage is specified in the approved design. NFRs should define execution repeatability, failure cases, and evidence safety rather than restating business permissions.

## Questions

Choose an option for each question. The recommended option matches the approved local PoC direction. Choose `X` and describe the desired requirement if none fits.

### Question 1 — Supported scale and reconciliation cadence

What identity and run volume should this reconciler support?

A) Fixed local PoC: the named developer, analyst, writer, admin, required component identities, three buckets, and a small manually managed extension; operator-triggered runs with no growth or throughput target. **(Recommended)**

B) Set an initial identity count, expected growth, reconciliation interval, and maximum completion time in `X`.

X) Other (describe scale/cadence).

[Answer]:A

### Question 2 — Completion time and API latency

What timing requirement applies to a successful reconciliation?

A) Correctness only; no end-to-end latency SLA. Use bounded per-request timeouts and report elapsed time for diagnosis. **(Recommended)**

B) Define a maximum run time and API response percentile/load assumption in `X`.

X) Other (describe timing expectations).

[Answer]:A

### Question 3 — Availability and recovery

What should happen when FreeIPA or RustFS is unavailable or a reconciliation is interrupted?

A) Single-host best effort with no HA/RTO guarantee. Fail closed before mutation when preflight fails; if interrupted after mutation starts, mark `partial-failure`, preserve state, and require a safe rerun/review. **(Recommended)**

B) Specify recovery time, automatic retry/rollback, and service availability targets in `X`.

X) Other (describe availability and recovery).

[Answer]:A

### Question 4 — Concurrency and consistency

How should overlapping reconciler invocations be handled?

A) Permit only one active run for the RustFS target. A second invocation exits as `already-running` without mutation. Never claim cross-resource atomicity; re-read state and verify after each successful change group. **(Recommended)**

B) Allow concurrent runs with conflict resolution; define locking/version semantics in `X`.

X) Other (describe concurrency behavior).

[Answer]:A

### Question 5 — Credential and network security

What minimum security posture applies to reconciliation inputs and RustFS admin access?

A) Keep the RustFS endpoint internal to the Compose network; use SigV4 over the existing internal endpoint; mount admin secrets as protected read-only files; never place them in environment values/arguments/logs. Keep human credentials separately managed and out of the reconciler's output. **(Recommended)**

B) Require TLS on the internal RustFS endpoint and specify certificate provisioning/trust in `X`.

X) Other (describe transport, secret storage, and network boundary).

[Answer]:A

### Question 6 — Audit and status retention

What reconciliation evidence should be retained?

A) Emit sanitized start/end, desired-policy version, terminal state, safe resource/action counts, and failure category. No secrets, complete API bodies, access-key IDs, or object names. Keep only the current runtime status file plus container logs; no retention SLA. **(Recommended)**

B) Define an audit retention period, immutable location, and operator access controls in `X`.

X) Other (describe audit fields and retention).

[Answer]:A

### Question 7 — Pre-change state backup and rollback

Should policy reconciliation require a protected pre-change backup?

A) Before any approved replacement of existing IAM policy/bindings, create a protected operator-reviewed IAM-state export or equivalent backup and prove it can be inspected/restored in isolation. Do not automatically roll back unknown state. **(Recommended)**

B) Rely on version-controlled desired state and manual correction; no pre-change export requirement.

X) Other (describe backup/rollback expectations).

[Answer]:A

### Question 8 — Dependency and version policy

How should RustFS and reconciler dependencies be managed?

A) Keep the RustFS image and Python dependencies pinned; use the existing provisioner/container and HTTP/SigV4 stack. Any dependency or service addition requires compatibility evidence and review. **(Recommended)**

B) Permit additional unpinned dependencies/services for convenience.

X) Other (describe version and dependency requirements).

[Answer]:A

## Approval Gate

The user completed answers A/A/A/A/A/A/A/A on 2026-10-27. The NFR specification and tech-stack decisions are ready for review before Unit 2 NFR Design. Implementation and live policy mutation remain behind later gates.
