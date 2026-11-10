# Unit 2 Code Generation Summary — RustFS Role Reconciliation

## Generated changes

- Added `infra/identity-provisioner/rustfs-role-policy.json` with policy version `2026-10-27.1` and the approved developer, analyst, and writer scopes across `lake`, `lake-dev`, and `lake-uat`.
- Added `infra/identity-provisioner/reconcile-rustfs-roles.py`. It validates the fixed policy, queries FreeIPA over certificate-verified LDAP TLS, serializes runs with `flock`, rejects ambiguous state and unmanaged grants, snapshots IAM before the first mutation, applies only approved additions and exact role membership deltas, verifies readback, and runs S3 probes with the three non-root identities.
- Added transient probe checks for list/read/location, allowed and denied writes, multipart listing, initiation, part listing, and abort. Namespace-aware XML parsing and exact-key upload discovery clean up only nonce-scoped probe objects and uploads, including when an initiate response is lost.
- Added `infra/identity-provisioner/apt-packages.lock` and pinned the existing Bookworm base digest to immutable Debian and Debian Security snapshot indexes dated `20261026T000000Z`. Snapshot metadata remains signature-verified by apt; HTTP is used because the pinned minimal base has no CA bundle for the local build proxy. Direct runtime packages are versioned in the lock; the image records the complete resolved `dpkg` inventory at `/usr/share/identity-provisioner/package-inventory.txt`.
- Added a dedicated `identity-reconciler` Compose profile entrypoint. It connects only to the internal `identity_test_net` and `freeipa_validation_net`, never `iceberg_net`. It receives test-only RustFS root and role credentials, the FreeIPA read-only query credential, public CA, policy, and test-scoped protected runtime path as files. It does not call the aggregate identity provisioner.
- Added a FreeIPA helper that interactively creates `rustfs-reconciler` only after an administrator ticket is present. It does not accept passwords in arguments or mutate an existing account.
- Updated `scripts/bootstrap-local.sh` to create deployment credentials separately from isolated test root/role/LDAP credentials, without rotating existing values.
- Added operator notes in `README.md`; updated this plan and AI-DLC state/audit records.

## Safety and operational boundaries

- No bootstrap command was run. No credentials, FreeIPA users, RustFS users/groups/policies/bindings, buckets, or objects were created or changed.
- No services or containers were started. No tests were added or run.
- Do not run `identity-reconciler` against the existing `object-store`. Unit 2 Build and Test must first create/use a separate isolated RustFS target and verify the pinned image's API behavior.
- Existing RustFS API shapes, bucket-policy absence response, IAM export completeness, restoration compatibility, LDAP ACL coverage, and S3 action status codes are not yet verified against the pinned runtime. Any mismatch must block mutation and be addressed in Build and Test.
- FreeIPA's `rustfs-reconciler` user is created manually by the operator after bootstrap; Code Generation did not create or change it. Build and Test must verify its actual LDAP read scope and no-write behavior.
- The snapshot is stored mode `0600` under the test-scoped `.runtime/identity-provisioning/test-status/iam-snapshots/`; it is sensitive, must remain outside Git, and may only be restored to a separate isolated RustFS instance.

## Build and Test corrections

- RustFS rejects bucket names containing `_`; the approved environment names are `lake-dev` and `lake-uat`. These names are used in the desired policy and in the workload repository's `configs/dev.yml` and `configs/uat.yml` paths.
- The pinned RustFS admin API requires `groupStatus: "enabled"` in `update-group-members`; this is included after an observed `InvalidRequest` response identified the missing field.
- Runtime validation now passed once with `complete` and again with `no-change`. The reconciler verified exact membership and policy readback and completed the positive/negative S3 probes, including multipart checks. The production RustFS service was not targeted.
- Separate IAM export restore into a second disposable RustFS instance passed with all seven archive entries semantically matching after excluding regenerated record metadata. The endpoint guard accepted only the test target, lock contention returned `already-running`, LDAP/RustFS authentication and service failures were blocked before mutation, and managed-policy drift was detected before mutation. Restoring test credentials, service, and desired policy was confirmed by a subsequent passing `no-change` run. Compose secret/mount targets, file modes, status, and bounded diagnostics were reviewed with no secret values exposed. Failure injection for malformed responses, snapshot-write, and additional mutation interruption points remains open; see `plans/unit-2-build-and-test-plan.md`.

## Build and Test gates

Build and Test must cover image/package inventory reproducibility, Compose network isolation, FreeIPA CA/hostname validation and read-only scope, each pinned RustFS admin API response and error class, bucket and direct policy conflict blocking, snapshot structure and isolated restore, stale-run/concurrency behavior, no secret leakage, idempotent reconciliation, failure after a successful mutation, positive/negative S3 access including multipart, and probe cleanup. No live role reconciliation, FreeIPA authority cutover, key rotation, or legacy-user retirement is part of this gate.
