# NFR Design Patterns — RustFS Role Policies and Reconciliation

## Design scope

This design translates `RFS-NFR-01`–`RFS-NFR-15` and the approved Unit 2 functional rules into patterns for the existing operator-invoked identity provisioner. It covers a fixed local Compose installation with `lake`, `lake-dev`, and `lake-uat`. It does not change the approved role matrix or implement reconciliation.

## Quality and reliability patterns

### Bounded, fail-closed run lifecycle

Each run follows explicit phases: `validate → coordinate → preflight → plan → protect-state → apply → read-back → probe → report`. Configuration and desired policies are validated before network mutation. FreeIPA and RustFS readiness, authentication, expected identities, buckets, existing managed bindings, and potentially broad grants are checked before the apply phase. Only explicit not-found responses permit ensure-only creation of `lake-dev` or `lake-uat`; `lake` is observed and preserved. Timeouts, authorization failures, unexpected status codes, and malformed responses stop the run without treating uncertain state as absence. Every dependency call has a finite timeout; actual values and retry classification are Infrastructure Design decisions.

### Serialized and idempotent reconciliation

The operator entry point obtains a single-host coordination token before any mutation. If another run owns it, the new run returns `already-running` without changing state. A stale token is not automatically stolen: an operator must establish that its owner is no longer active before recovery. Desired state is compared to complete normalized observed state, and only allowlisted differences are applied. Repeating the same inputs after successful convergence returns `no-change` and makes no additional IAM or bucket changes.

### Partial failure and safe recovery

RustFS calls across buckets, users, groups, policies, and bindings are not treated as a transaction. Any error after the first successful mutation yields `partial-failure`, records a sanitized action/resource category, and stops further changes. The run never claims rollback or success based only on API responses. It preserves all bucket data and leaves successful prior changes visible for review. Recovery is operator-reviewed: correct the cause, inspect current state and the protected snapshot where needed, then rerun the idempotent reconciler. Automatic restoration over unknown live state is prohibited.

### Exact drift and additive-grant control

Before applying, the reconciler classifies managed role identities, role groups, policies, group bindings, direct attachments, and relevant bucket policies. An unknown or broader direct, inherited, or bucket-level grant blocks the run; the reconciler does not delete unrelated IAM state to force convergence. Managed policy documents and bindings are compared exactly after normalization. Unknown roles, buckets, actions, identifiers, duplicate/conflicting role memberships, or unreadable state fail before mutation. These checks implement `BR-RFS-08`, `BR-RFS-11`–`BR-RFS-12a`, and `BR-RFS-17`–`BR-RFS-23`.

## Security and preservation patterns

### Credential separation and least privilege

Use a dedicated authenticated read-only FreeIPA lookup identity for directory reads. Keep it separate from FreeIPA `admin` and the scoped membership-change identity. RustFS administrative credentials are supplied as protected files and used only by IAM administration. Non-root role credentials perform S3 probes; root is never used to infer role permissions. Human secret delivery remains Unit 4 scope. The actual FreeIPA bind identity, TLS trust mount, secret paths, and file ownership/modes are Infrastructure Design decisions.

### Secret-safe observability

Logs and the current runtime status expose only run identifier, desired-policy version, timestamps and elapsed duration, terminal state, bounded action/resource counts, verification outcome, and sanitized failure category. They exclude passwords, access-key IDs, secret keys, full request/response bodies, object names, object contents, and raw policy export contents. Error mapping is allowlisted rather than copying dependency exception text. Runtime status and snapshots remain outside version control with restrictive access. Exact runtime path, persistence, and logging configuration are resolved in Infrastructure Design.

### Protected pre-change state

Before replacing an existing managed policy or binding, capture an IAM export or equivalent snapshot to a protected operator-controlled location. Treat the snapshot as secret-bearing even if it appears to contain only IAM metadata. Do not print its contents, commit it, or automatically apply it to the live instance. Prove inspection and restore only against a separate isolated RustFS instance. Export format, capture mechanism, file permissions, and isolated restore fixture remain implementation decisions.

### Data and identity preservation

The existing production `lake` bucket, all objects, existing `admin` mapping, writer S3 credential, and legacy `user_a`/`user_b` identities remain unchanged by normal reconciliation. The reconciler may create `lake-dev` or `lake-uat` only after a definitive absence response. It does not delete, empty, rename, or migrate buckets or objects, remove unmanaged IAM resources, or rotate credentials. This is an invariant across success, failure, and rerun paths.

## Completion evidence and status contract

| Terminal status | Meaning |
|---|---|
| `complete` | Desired managed state was applied, exact policy/binding readback passed, and all required non-root positive and negative S3 probes passed. |
| `no-change` | Desired state already matched; exact readback and required role probes passed. |
| `blocked` | A preflight conflict, unavailable dependency, invalid input, or ambiguous state prevented mutation. |
| `already-running` | Another active run owns the single-run token; this run made no changes. |
| `partial-failure` | Mutation began, but at least one operation or post-apply verification failed; no success is claimed. |

Only `complete` and `no-change` are successful. For both, API readback and effective S3 authorization evidence are required. Probes use disposable non-root test credentials and unique keys; cleanup is limited to keys created by that probe. The full role-by-bucket/action matrix remains the Build and Test acceptance evidence.

## Requirement traceability

| Requirement | Design pattern |
|---|---|
| `RFS-NFR-01`–`02` | Fixed-scope operator run; bounded dependency calls; safe elapsed duration. |
| `RFS-NFR-03` | Dependency and state preflight completes before mutation; uncertainty blocks. |
| `RFS-NFR-04` | Explicit `partial-failure`; preserve state and data; operator-reviewed recovery and safe rerun. |
| `RFS-NFR-05`–`06` | Single-host coordination token, no stale takeover, exact desired/observed comparison and idempotent no-op. |
| `RFS-NFR-07`–`09` | File-backed secrets, isolated identities, internal endpoint, admin-only IAM calls, non-root S3 probes. |
| `RFS-NFR-10` | Sanitized allowlisted status/log fields and sensitive export handling. |
| `RFS-NFR-11` | Protected pre-change export and isolated restore; no automatic live restore. |
| `RFS-NFR-12` | Ensure-only creation for missing dev/UAT buckets; no bucket/object destructive operations. |
| `RFS-NFR-13` | Pinned-image compatibility gate and deterministic dependency resolution gate. |
| `RFS-NFR-14` | Exact drift inspection; block broader or ambiguous access and unknown API behavior. |
| `RFS-NFR-15` | Exact post-apply readback plus full non-root positive/negative role probes before success. |

## Deferred implementation decisions

Infrastructure Design must specify the lock/status location and coordination primitive, FreeIPA read-only identity and TLS distribution, credential mounts and permissions, package/dependency lock or pinned repository snapshot, IAM export storage and isolated restore procedure, internal endpoint and per-call timeouts/retry classification, and pinned-image API response classification. Build and Test must establish the actual RustFS API and policy semantics on the pinned digest; this design does not assume unverified endpoint behavior.
