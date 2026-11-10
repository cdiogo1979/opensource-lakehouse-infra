# NFR Requirements — RustFS Role Policies and Reconciliation

## Scope and assumptions

These requirements apply to the Unit 2 operator-triggered reconciler that projects FreeIPA identities and role-group membership into RustFS IAM and ensures the three approved buckets. The target is the existing single-host Docker Compose proof of concept. The approved functional policy and access matrix remain authoritative; these NFRs add quality, reliability, security, and verification constraints without changing role permissions.

The workload is small: the named developer, analyst, writer, admin, necessary component identities, three buckets, and a small manually managed extension. There is no growth, throughput, availability, or end-to-end latency SLA. FreeIPA and RustFS remain dependencies; failure must not create broader permissions. A reconciliation run is explicitly invoked by an operator and only one run may mutate the target at a time.

## Requirements

| ID | Quality attribute | Requirement | Verification |
|---|---|---|---|
| RFS-NFR-01 | Scale | Support the approved fixed local PoC identity set, three buckets, and a small operator-managed extension. No horizontal scale or growth commitment is implied. | Run reconciliation against all approved roles and component identities; record the input counts without identity secrets. |
| RFS-NFR-02 | Performance | Correctness is the service objective; there is no end-to-end latency SLA. Every network call must have a finite timeout, and elapsed duration must be available in sanitized run status. | Simulate a nonresponsive RustFS/LDAP endpoint and verify the run exits within configured per-call bounds; inspect the safe duration field. |
| RFS-NFR-03 | Availability | Provide single-host best-effort operation without HA or RTO guarantees. A failed FreeIPA or RustFS preflight must stop before mutation. | Deny or interrupt each dependency before preflight and verify no bucket, identity, membership, or policy mutation occurs. |
| RFS-NFR-04 | Partial failure and recovery | RustFS multi-resource updates are not treated as atomic. If interruption or an error occurs after mutation begins, report `partial-failure`, preserve existing data, identify the sanitized resource/action category, and require review or a safe rerun. Do not automatically roll back unknown state. | Inject failure after a successful mutation, confirm incomplete status and unchanged bucket objects, correct the cause, rerun, and verify convergence. |
| RFS-NFR-05 | Concurrency | At most one run may mutate the configured RustFS target. A concurrent invocation must exit with `already-running` before any mutation. A stale lock requires operator inspection before removal or takeover. | Start two invocations concurrently and verify one acquires the lock while the other exits without changing state. Test abandoned-lock handling without removing a live lock. |
| RFS-NFR-06 | Idempotency | Repeating reconciliation with unchanged directory and policy inputs must produce `no-change` and no extra identities, policies, bindings, memberships, or bucket operations. | Run twice with identical inputs and compare sanitized operation summaries and read-back state. |
| RFS-NFR-07 | Secret protection | Mount FreeIPA read-only query credentials and RustFS administrator credentials as protected read-only files. Do not put secrets in source, ordinary environment values, command arguments, policy documents, run summaries, or logs. Human IAM secret delivery remains Unit 4 scope. | Inspect Compose mounts, process arguments, log/status outputs, generated policy documents, and filesystem modes using non-secret diagnostics. |
| RFS-NFR-08 | Network security | Use the existing RustFS internal Compose endpoint and SigV4 authentication; do not publish a new host port for the reconciler or RustFS admin API. The approved design does not add TLS termination on the internal endpoint. | Render Compose and inspect bound ports/networks; verify the reconciler reaches RustFS through the internal service endpoint only. |
| RFS-NFR-09 | Least privilege | Use RustFS root credentials only for the administrative reconciliation API. Use non-root role credentials for access probes. Use a distinct authenticated read-only FreeIPA query identity, separate from FreeIPA `admin` and the group-membership mutation identity. | Verify mounted identities by safe identity checks; demonstrate root is not used in S3 probes and read-only LDAP identity cannot mutate directory state. |
| RFS-NFR-10 | Log and audit safety | Emit sanitized start/end status, desired-policy version, terminal state, elapsed time, safe action/resource counts, and failure category. Never emit passwords, keys, access-key IDs, complete request/response bodies, object names, or object contents. Retain only the current runtime status plus normal container logs; no retention SLA. | Scan logs/status and induced error output for seeded secret markers and object names; verify useful state/category remains. |
| RFS-NFR-11 | Pre-change recovery | Before replacing an existing managed policy or policy binding, create a protected operator-reviewed RustFS IAM export or equivalent snapshot. Keep it outside Git with restrictive permissions. Prove inspection and restore in an isolated RustFS instance; do not automatically restore over live state. Treat the export as sensitive because it may contain credential material. | Export current IAM state, verify file mode/location without displaying contents, restore only into a separate isolated test instance, and compare sanitized identity/policy counts. |
| RFS-NFR-12 | Data preservation | Never delete, empty, rename, or migrate buckets or their objects. Create only missing `lake-dev` and `lake-uat` after an explicit absence response; preserve existing `lake`. | Record bucket/object counts or stable inventory evidence before and after bucket ensure; test not-found versus 403/timeout handling. |
| RFS-NFR-13 | Versioning and compatibility | Keep RustFS image `rustfs/rustfs:1.0.0-glibc` pinned to its Compose digest and keep reconciler dependencies deterministic/pinned. Verify administrative API and IAM behavior against that exact image before acceptance. No floating `latest` or unreviewed service/dependency additions. | Check rendered Compose image digest and dependency lock/version inventory; execute API compatibility and access tests against the pinned image in Build and Test. |
| RFS-NFR-14 | Change safety | Exact policy/binding drift, conflicting role membership, broader bucket-level grants, unexpected direct policy, unknown API responses, or failed verification must block or mark the run incomplete; never silently widen permissions. | Seed each conflict in an isolated test instance and prove it is reported before mutation or as partial failure with no false success. |
| RFS-NFR-15 | Verification | Acceptance requires policy/binding readback and positive/negative S3 probes using non-root role credentials. API success alone is insufficient. Probe keys are unique and cleanup is limited to keys created by the probe. | Execute the role-by-bucket/action matrix and assert every allow/deny result; inspect cleanup evidence and confirm unrelated objects remain. |

## Operational status contract

The reconciler reports one of `complete`, `no-change`, `blocked`, `already-running`, or `partial-failure`. A successful terminal state is allowed only after exact managed policy/binding readback and the approved S3 probes pass. Any status artifact is protected runtime state, excluded from source control, and contains no secret-bearing data.

## Traceability

- RFS-NFR-01–02: Unit 2 local PoC scale and operator-triggered reconciliation.
- RFS-NFR-03–06: fail-closed, partial failure, serialization, and idempotent convergence.
- RFS-NFR-07–10: secret protection, network boundary, least privilege, and sanitized audit.
- RFS-NFR-11–12: approved pre-change backup and bucket/object preservation.
- RFS-NFR-13–15: pinned compatibility, drift handling, and evidence-based verification.

## Approval Gate

Answers A/A/A/A/A/A/A/A are recorded from the completed Unit 2 NFR Requirements Plan. Review this specification and `tech-stack-decisions.md` before Unit 2 NFR Design.
