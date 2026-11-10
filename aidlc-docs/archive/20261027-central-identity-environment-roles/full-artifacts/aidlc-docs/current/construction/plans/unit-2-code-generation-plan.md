# Unit 2 Code Generation Plan — RustFS Role Policies and Reconciliation

## Unit Context

- **Unit:** Unit 2 — Declarative RustFS Role Policies and Reconciliation.
- **Stories:** US-02, US-03, US-04, US-05, US-06, and US-07.
- **Workspace:** `/Users/carlosdiogo/code_repo/opensource-lakehouse-infra` (brownfield Docker Compose platform).
- **Dependencies:** Approved Unit 1 FreeIPA directory/group contract; existing RustFS pinned image, IAM provisioner, buckets, role mappings, and protected credential files.
- **Completion boundary:** Add reviewed policy/configuration and an explicit RustFS-only reconciliation path. Do not execute it against the current RustFS or mutate FreeIPA, MIT KDC, production objects, buckets, credentials, identities, policies, or bindings during Code Generation.

This plan is the single source of truth for Unit 2 Code Generation. Do not add or run tests during Code Generation. Runtime checks, API compatibility verification, and isolated reconciliation belong to Build and Test.

## Approved Contracts

- Roles and scopes are fixed by `construction/unit-2/functional-design/business-rules.md`: developers read all buckets and write only `lake-dev`; analysts read only `lake` and cannot write; writers read/write all three; `admin` mapping remains unchanged.
- FreeIPA is the source of canonical identities and role-group membership. A dedicated read-only LDAP identity is used; it is separate from FreeIPA admin and the group-mutation principal.
- RustFS remains pinned to the Compose digest and reachable through the internal endpoint only. Existing urllib/botocore SigV4 client code is retained; no RustFS SDK or proxy is added.
- The one-shot reconciliation container connects only to the dedicated internal `identity_test_net` and `freeipa_validation_net`. It must not join `iceberg_net`; test RustFS is addressed only through `rustfs-iam-test:9000`. FreeIPA remains off the general workload network. MIT remains the active KDC; no KDC alias/cutover or client attachment is performed.
- Build a separate one-shot Compose reconciliation service from the existing provisioner image/codebase, with a distinct entrypoint, least-required mounts, and explicit operator invocation. Do not execute aggregate Kerberos/PostgreSQL provisioning from this path. No always-on service is added.
- Use a test-scoped `.runtime/identity-provisioning/test-status` mount for the advisory lock, sanitized current status, and protected IAM snapshots. An interrupted nonterminal status blocks a new mutation until an operator reviews it. Test RustFS root and role secrets must come only from `.runtime/identity-provisioning/test-credentials`; do not mount existing lakehouse RustFS credentials into this service.
- Keep the writer S3 credential, existing `admin` mapping, all `lake` objects, and `user_a`/`user_b` unchanged. Only absent `lake-dev`/`lake-uat` may be created. No key rotation or legacy-user retirement is included.
- Pin dependencies through an immutable Debian snapshot and exact package versions, including the reviewed `python3-ldap` package needed for the live read-only LDAP contract. Preserve the base image digest and record the package inventory.

## Sequential Generation Steps

### Step 1 — Add version-controlled desired policy and validation

- [x] Add a versioned non-secret policy/configuration file representing the exact role/bucket/action matrix; include schema/version validation and reject unknown roles, buckets, actions, duplicate identifiers, and broad resources.
- [x] Keep policy documents separate from all credential material. Provide stable names and canonical normalization for complete drift comparisons.
- [x] Implement policy validation without making any RustFS or FreeIPA calls.

### Step 2 — Make the provisioner image reproducible and add LDAP read support

- [x] Keep the digest-pinned Debian Bookworm base and change apt sources to the approved immutable snapshot; pin the direct runtime package versions, including existing packages and `python3-ldap`, in `apt-packages.lock`. Transitive packages resolve only from the immutable Debian and Debian Security snapshot indexes.
- [x] Record the snapshot timestamp, direct package versions, and complete installed package inventory; do not leave floating package indexes or introduce a service.
- [x] Implement a read-only FreeIPA LDAP adapter with CA and hostname validation, finite connection/search timeouts, narrow approved user/group queries, safe error classification, and no write operations.
- [x] Add an operator-controlled isolated FreeIPA provisioning helper for a dedicated read-only query principal; do not run the helper or create/modify FreeIPA identities during Code Generation.

### Step 3 — Implement the isolated RustFS-only Compose path

- [x] Add a one-shot `identity-reconciler` Compose service using the existing provisioner build/image and an explicit RustFS-only executable. Do not route through `provision-kerberos-identities` or its aggregate path.
- [x] Attach only this one-shot service to `identity_test_net` and `freeipa_validation_net`; keep it off `iceberg_net`, and keep FreeIPA and all other workload services on their current network memberships and host-port exposure.
- [x] Add explicit FreeIPA network aliasing for the existing certificate FQDN; preserve hostname validation and avoid host routes/ports.
- [x] Mount only test RustFS root, non-root probe, LDAP bind, public CA, policy, and test runtime-state files. Use read-only secret/trust mounts and avoid environment/argument secret values.
- [x] Keep `ROTATE_RUSTFS_WRITER_SECRET` out of the reconciliation path and make invocation explicit and operator-triggered.

### Step 4 — Implement safe coordination, snapshots, and sanitized status

- [x] Implement `flock`-based single-run serialization under `.runtime/identity-provisioning`, returning `already-running` before mutation when held.
- [x] Atomically persist allowlisted status fields. Detect stale nonterminal status and require operator review before mutating reruns; never steal a live lock or silently treat interrupted work as complete.
- [x] Implement protected pre-change IAM snapshot capture before replacing existing managed policy/binding state; use restrictive permissions, atomic write, and no output of snapshot contents.
- [x] Stop before replacement if snapshot export is unavailable, invalid, or cannot be safely written. Document operator-owned retention and isolated-only restore. Completeness/restore compatibility remains a Build and Test gate for the pinned RustFS image.
- [x] Ensure all exceptions and logs map to sanitized categories and omit secret values, access-key IDs, full bodies, object names, and object contents.

### Step 5 — Implement reconciliation and evidence contracts

- [x] Reuse the current SigV4 urllib adapter with finite timeouts, explicit known-response classification, bounded read-only retries, and no mutation retries. Uncertain mutation responses become `partial-failure`; a reviewed rerun rereads live state before planning further deltas.
- [x] Preflight FreeIPA, RustFS, managed identity/group state, direct and bucket-level policy grants, and bucket state; fail closed on ambiguity or non-absence errors.
- [x] Build a redacted in-memory plan and apply only allowlisted idempotent deltas. Preserve unmanaged state, writer secret, admin mapping, legacy identities, `lake`, and all object data.
- [x] Ensure only missing `lake-dev` and `lake-uat`; never delete, empty, rename, or migrate buckets/objects.
- [x] Read back normalized policies and bindings; implement non-root S3 allow/deny probes, including multipart actions, and cleanup only of probe-created keys/uploads.
- [x] Emit `complete` or `no-change` only after readback and required probes pass; use `blocked`, `already-running`, or `partial-failure` for other outcomes. No automatic live rollback.

### Step 6 — Operator documentation and conformance review

- [x] Document safe FreeIPA reader provisioning, credential/trust file locations, isolation boundaries, status/snapshot handling, and the Build and Test invocation gate.
- [x] Record changed files, package locks, interfaces, no-live-mutation boundaries, and all Build and Test gates in `construction/unit-2/code/code-summary.md`.
- [x] Review file scope against approved Functional, NFR, and Infrastructure designs. No credentials/runtime state were created, no services were started, no tests were added or run, and no active RustFS/FreeIPA/MIT state was touched.
- [x] Update plan checkboxes and `aidlc-state.md` as generation steps complete. No tests are added or run during Code Generation.

## Build and Test Gates

Build and Test will validate the reproducible image and package inventory; Compose network isolation; LDAP CA/hostname/read-only behavior; preflight error classification; concurrency and stale-status handling; sanitized logs/status; protected snapshots and isolated restore; pinned-image RustFS IAM API semantics; idempotency and partial failure; and complete non-root positive/negative role probes. All policy and bucket mutations run only against isolated test state. Live reconciliation, FreeIPA authority cutover, writer-key rotation, and `user_a`/`user_b` retirement remain outside the gate.

## Scope Exclusions

- Do not run the reconciler against the active RustFS service during Code Generation or Build and Test.
- Do not create live buckets, role memberships, RustFS users/policies/bindings, or FreeIPA query credentials during Code Generation.
- Do not change MIT KDC state, Kerberos client configuration, existing keytabs, writer/admin credentials, `admin` mapping, or legacy-user state.
- Do not implement notebook credential delivery/session revocation (Unit 4), Ranger/StarRocks authorization (Unit 5), or integrated cutover (Unit 6).
- Do not add a new RustFS SDK, always-on controller, scheduler, TLS proxy, host admin port, or unreviewed package/service.

## Approval Gate

## Approval Record

The user approved this Code Generation Plan and requested continuation on 2026-10-27. Code Generation is complete; proceed to the Unit 2 Build and Test Plan review. Runtime checks and any execution against live services remain prohibited in this stage.
