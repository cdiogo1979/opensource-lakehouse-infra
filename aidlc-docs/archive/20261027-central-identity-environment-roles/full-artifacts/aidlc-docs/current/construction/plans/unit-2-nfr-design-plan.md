# Unit 2 NFR Design Plan — RustFS Role Policies and Reconciliation

## Approved Baseline

The approved Unit 2 NFR requirements cover the fixed three-bucket PoC, operator-triggered reconciliation, bounded network calls, fail-closed preflight, serialized and idempotent changes, explicit partial-failure reporting, protected IAM snapshots, secret-safe logs, data preservation, deterministic dependencies, and readback plus positive/negative S3 verification. The approved functional design defines exact developer, analyst, writer, and admin policy scopes and preserves existing production data, writer S3 credentials, admin mapping, and legacy users until a verified cutover.

## Design Checklist

- [x] Trace each design pattern to approved `RFS-NFR-01` through `RFS-NFR-15` and the Unit 2 functional rules.
- [x] Define logical responsibilities for operator invocation, configuration/policy loading, FreeIPA read-only lookup, RustFS administration, preflight, reconciliation, evidence probes, and status/audit output.
- [x] Specify the run lifecycle: validate inputs, acquire single-run coordination, preflight dependencies and drift, protect a pre-change IAM snapshot when required, reconcile, read back, probe, and report a terminal state.
- [x] Define fail-closed boundaries, bounded-call behavior, conflict handling, and partial-failure recovery without automatic rollback over unknown state.
- [x] Define idempotency, concurrency outcomes, stale-lock review, and safe rerun behavior.
- [x] Define protected handling for credentials, IAM snapshots, runtime status, and sanitized logs.
- [x] Define preservation invariants for `lake`, its objects, legacy users, admin mapping, and writer S3 credentials; ensure only missing `lake-dev` and `lake-uat` may be created.
- [x] Define verification evidence required before reporting `complete` or `no-change`, including policy/binding readback and non-root allow/deny probes.
- [x] Record compatibility, package determinism, endpoint, timeout, and restore decisions that must be resolved during Infrastructure Design or Build and Test.
- [x] Generate `construction/unit-2/nfr-design/nfr-design-patterns.md` and `logical-components.md` after this plan is approved.
- [x] Present the NFR Design artifacts for explicit review before Unit 2 Infrastructure Design.

## Design Boundaries

- Planning and design only. Do not start or modify FreeIPA, RustFS, Compose services, identities, role memberships, credentials, buckets, policies, bindings, or objects.
- Do not create `lake-dev` or `lake-uat`, rotate the writer S3 key, alter the `admin` mapping, or remove `user_a`/`user_b` in this stage.
- Do not add a service, scheduled controller, host-published admin endpoint, or new API/dependency stack.
- Keep RustFS IAM root credentials limited to administration and use non-root role credentials for S3 authorization probes.
- Do not claim cross-resource atomicity. Any future implementation must expose partial progress and preserve data on error.
- Infrastructure Design will resolve concrete lock/status storage, read-only LDAP bind identity and TLS trust, secret mounts, dependency lock or repository snapshot, export storage and restore fixture, endpoint/timeout values, and pinned-image API response mapping.
- Build and Test will verify behavior against the pinned RustFS image in isolated state, including conflict and failure cases, serialization, idempotency, snapshot inspection/restore, and the complete role-by-bucket/action matrix.

## Approval Gate

This plan was approved by the user on 2026-10-27. Review `construction/unit-2/nfr-design/nfr-design-patterns.md` and `logical-components.md` before Unit 2 Infrastructure Design.
