# Unit 2 Build and Test Plan — RustFS Role Reconciliation

## Purpose and boundaries

Validate the generated reconciler against the exact pinned RustFS image and an isolated FreeIPA validation directory before accepting or using the role policy. All RustFS mutation, account provisioning, buckets, probe objects, snapshots, and test credentials must be isolated test state. Do not use the existing `object-store`, its root secret pair, or production object data. Do not touch the active MIT KDC, FreeIPA authority state except for the dedicated validation query identity, legacy users, or existing `lake` bucket.

The reconciler is compiled/configured to accept only `http://rustfs-iam-test:9000` in this stage. Its runtime endpoint guard must remain in force throughout these tests. No live role reconciliation, writer-key rotation, user retirement, or authority cutover is in scope.

Do not add or run tests until this plan is approved. Once approved, create the test-only stack and test credential files under `.runtime/identity-provisioning/test-*`; never display secret contents.

## Test environment

1. Build `local/identity-provisioner:bookworm-snapshot` from the digest-pinned Debian base and frozen `20261026T000000Z` apt indexes. Inspect the installed package inventory and confirm exact direct package versions from `infra/identity-provisioner/apt-packages.lock`.
2. Start one RustFS container from the exact `rustfs/rustfs:1.0.0-glibc` digest under a test-only Compose project. Give it a new named volume, no host-published ports, and alias `rustfs-iam-test` on a dedicated internal `identity_test_net`.
3. Generate distinct test root and role credentials in an ignored, mode-`0700` `.runtime/identity-provisioning/test-credentials` directory. Do not reuse or mount the existing RustFS root credential files. Use test-only RustFS users for `developer-user`, `analyst-user`, and `write-service-account`.
4. Start the approved isolated FreeIPA validation server only if it is not already healthy. Create only the `rustfs-reconciler` read identity through the interactive helper, with no role-group membership or write privileges. Export and mount its public CA. Confirm the directory account can read only the required groups and account attributes; if the image's default LDAP ACLs do not allow this, stop and design the narrow read ACL before proceeding.
5. Run a test-only reconciler container attached to `identity_test_net` and the existing `freeipa_validation_net`; do not attach it to `iceberg_net`. Mount the test RustFS credentials, query credential, public CA, policy, and a fresh protected status/snapshot directory.

## Verification sequence

### 1. Build and static checks

- Build the local identity-provisioner image from the pinned base and immutable apt snapshot.
- Inspect `package-inventory.txt`; verify the direct locks, `python3-ldap`, `python3-botocore`, and Kerberos tools are present.
- Validate Compose rendering without starting the normal stack; inspect the effective networks, entrypoint, read-only mounts, secret mounts, and host port list.
- Check Python and shell syntax without invoking reconciliation.
- Verify the target guard accepts `rustfs-iam-test:9000` and rejects `object-store`, host-published endpoints, HTTPS aliases, alternate ports, path/query URLs, and malformed URLs.

### 2. Directory and preflight behavior

- Verify TLS hostname and CA validation, bounded LDAP connect/search timeouts, and successful reads for the three role groups and user state.
- Confirm invalid credentials, missing groups/users, locked accounts, extra role members, and conflicting memberships return sanitized pre-mutation failures.
- Attempt directory writes as `rustfs-reconciler`; verify them denied. Inspect logs/status for usernames, credentials, LDAP response bodies, and attribute values.
- Verify RustFS auth failure, service unavailability, malformed responses, unknown error codes, missing production bucket, bucket policy, user direct grant, group policy conflict, and disabled users/groups block before mutation.
- Verify all absence cases require a specific known not-found response; empty/unknown 404 responses must block.

### 3. First reconciliation and policy behavior

- Run once against the disposable RustFS instance. Confirm only `lake-dev` and `lake-uat` are created when absent; `lake` is preserved.
- Verify exact group memberships and policy documents:
  - `developer-user`: read all three buckets, write only `lake-dev`.
  - `analyst-user`: read `lake`, write nowhere.
  - `write-service-account`: read/write all three buckets.
- Confirm `admin` remains bound only to `consoleAdmin`, existing writer secret is unchanged, and no policy/group for unmanaged users is changed.
- Confirm IAM snapshot content is a complete pinned-image export, mode `0600`, stored under the ignored test runtime directory, and not printed. Restore only into a separate disposable RustFS container and compare sanitized object counts.

### 4. Effective S3 probes

- As each role, test listing, reading, and `GetBucketLocation` on every allowed/disallowed bucket with expected success or `AccessDenied`.
- Verify developer put/delete succeeds only in `lake-dev`; analyst put/delete is denied in all buckets; writer put/delete succeeds in all buckets.
- Verify `ListBucketMultipartUploads`, multipart initiation, part upload/listing, and abort permissions for every role.
- Confirm all nonce-scoped probe objects and incomplete uploads are removed even after injected probe failures. No unrelated object may be touched.

### 5. Reliability, recovery, and audit

- Run two invocations concurrently; one must exit `already-running` without mutation.
- Interrupt after each successful mutation class in the disposable stack; verify `partial-failure`, sanitized status, preserved snapshot, no automatic rollback, and reviewed rerun convergence.
- Inject preflight transport, auth, timeout, unknown-status, policy drift, and snapshot-write failures; confirm no mutation occurs before all preflight and snapshot gates pass.
- Verify second healthy invocation returns `no-change` while still completing readback/probes.
- Inspect all logs/status, process arguments, mounts, and runtime file modes for secret leakage. Ensure no writer key rotation, `user_a`/`user_b` change, MIT KDC change, or production data access.

## Completion criteria

All checks above pass on the pinned RustFS release and isolated FreeIPA validation instance. Any endpoint response, export schema, ACL, or authorization mismatch blocks acceptance until corrected and retested. Preserve sanitized evidence only; do not retain secret-bearing API traces or snapshot exports in Git. Remove only explicitly named test containers, network, and test data volume after approval; keep protected test credentials and snapshots until their retention decision is recorded.

## Approval gate

Review and approve this Build and Test Plan before building/running the tests or creating test-only identities, credentials, networks, buckets, users, policies, bindings, objects, or snapshots.

## Execution record — 2026-10-27

- **Passed:** pinned image build; direct package inventory; Python and shell syntax; isolated FreeIPA TLS/query; test RustFS readiness and admin/writer baseline; policy validation; snapshot creation with mode `0600`; bucket creation for `lake-dev`/`lake-uat`; exact role user/group/policy/binding readback; admin and legacy writer preservation; S3 list/read/location allow and deny checks; role write/delete allow and deny checks; multipart initiate/part/list/abort checks; probe cleanup; complete reconciliation; subsequent `no-change` with readback and probes; isolated snapshot restore into a second RustFS instance with all seven archive entries semantically matching; endpoint guard accepted one test alias and rejected seven alternate targets; lock contention returned `already-running` before reconciliation; invalid LDAP hostname/password returned `directory-unavailable`/`directory-authentication-failed`; invalid RustFS root secret returned `rustfs-authentication-failed`; stopped RustFS returned `rustfs-transport-failed`; injected managed-policy drift returned `rustfs-policy-drift-requires-review`. These preflight failures had empty mutation counts. Restoring test credentials/service/policy was confirmed by another `no-change` run with probes passed.
- **Corrections from observed pinned-image behavior:** RustFS rejects underscores in bucket names, so the approved names are `lake-dev` and `lake-uat`. The pinned admin API requires `groupStatus: "enabled"` in the membership update payload. An initial attempt with the invalid names and a subsequent attempt with the incomplete payload both stopped with sanitized `partial-failure` statuses. The reviewed rerun converged; status and every captured IAM export remain protected at mode `0600`.
- **Additional failure injection passed:** a network-isolated harness against the pinned provisioner image rejected malformed bucket inventory, user JSON, and policy-mapping responses with sanitized categories. Snapshot export validation followed by a write denial stopped before RustFS mutation. Twelve injected preflight cases for missing/locked/extra/conflicting directory state and missing production bucket, bucket policy, unknown 404s, direct grants, and disabled users/groups all persisted `blocked` with zero mutation counts. The isolated validation FreeIPA reader was actually denied a group write. Full-run injected failures at user creation, policy creation, and group binding persisted `partial-failure` with expected planned counts; reviewed reruns converged (`no-change` after user and policy failure, `complete` after binding failure) with readback and role probes passed. Another full run removed an extra test-group member successfully, then injected policy failure; status recorded `membership_remove: 1` and `policy_create: 1`, and reviewed recovery returned to `no-change`. The snapshot-write gate persisted `blocked` before mutation and its reviewed rerun restored the binding. Injected role-probe and multipart-part failures cleaned all temporary objects/uploads. Current test status is protected `no-change`/`readback-and-role-probes-passed`, mode `0600`; production was not involved.
- **Additional parser and recovery checks passed:** network-isolated synthetic LDAP response fixtures exercised `DirectoryReader.memberships()` parsing for exact membership, empty/missing groups, missing users, locked accounts, extra members, and cross-role conflicts. The extra member is preserved in the parsed set so the reconciler's exact-set gate can reject it. On the disposable RustFS service, injected failures immediately after successful user creation, policy creation, and group-policy binding each persisted `partial-failure` with the expected planned mutation counts. Reviewed recovery runs restored the user/membership, policy/binding, and binding respectively. A final run returned `no-change` with `readback-and-role-probes-passed`, status mode `0600`.
- **Still open:** synthetic LDAP fixtures validate parser behavior but not reads against corresponding actual FreeIPA entry variants; no extra validation users/groups were created. Unit 2 Build and Test remains in progress pending actual LDAP-entry verification or an explicit verification waiver.
- **Preservation:** only the disposable RustFS test service and isolated validation FreeIPA reader identity were used. The normal `object-store`, production `lake`, existing production IAM, active MIT KDC, and data were not targeted.
