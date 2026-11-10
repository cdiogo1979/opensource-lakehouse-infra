# Infrastructure Design — RustFS Role Policies and Reconciliation

## 1. Scope and decisions

The implementation remains an explicit, operator-run action in the existing `infra/identity-provisioner` image and Compose project. It must not execute the aggregate Kerberos-keytab or PostgreSQL provisioning path. The RustFS reconciler receives only the credentials and trust material required for directory reads, RustFS IAM administration, and isolated role probes.

The only network bridge to the isolated FreeIPA validation server is the one-shot reconciler container: it joins `iceberg_net` for RustFS and `freeipa_validation_net` for LDAP reads. FreeIPA remains off the general workload network; no host LDAP/Kerberos/DNS port is published, the active MIT KDC remains authoritative, and no `kdc` alias or client configuration changes. The reconciler is not configured to forward packets between its Docker interfaces.

Decisions below record the approved recommended options A/A/A/A/A/A/A/A. No runtime implementation or state mutation is part of this document.

## 2. Operator invocation and Compose boundary

- Add a distinct explicit RustFS reconciliation executable/command to the existing provisioner codebase and image. It is invoked through the identity-provisioning Compose profile with an explicit entrypoint/command override.
- Do not invoke `/usr/local/bin/provision-kerberos-identities` for a RustFS-only run. Do not run the aggregate identity provisioning steps, `kadmin`, Hive/PostgreSQL role provisioning, or writer-secret rotation.
- Run as a one-shot container with `--rm`; do not introduce an always-on reconciler, scheduler, host-published API, or new service stack.
- The reconciler command gets only the required RustFS root access/secret files, dedicated LDAP bind password, public FreeIPA CA certificate, and non-root probe credentials required by the acceptance run. Remove unrelated secrets and keytab mounts from its effective service configuration.
- Keep `ROTATE_RUSTFS_WRITER_SECRET` disabled and do not call any writer secret update path.

Infrastructure change is confined to Compose service settings, the existing identity-provisioner image, provisioner scripts/configuration, and operator documentation. Existing service definitions and runtime state are preserved except for the explicitly approved network and mount wiring when implemented.

## 3. Network topology and directory access

The one-shot reconciler attaches to both existing Docker user-defined networks:

- `iceberg_net`: access to `object-store:9000` and required probe traffic.
- `freeipa_validation_net`: access to the isolated FreeIPA LDAP-over-TLS endpoint.

The FreeIPA validation service remains on its isolated network only. Add an explicit network alias `ipa.lakehouse.local` on that network if necessary to make certificate hostname validation resolve to the same service address; confirm with a container-side DNS and TLS probe before accepting the wiring. Do not use `host.docker.internal`, host-published LDAP, or the active MIT KDC.

Provision a distinct FreeIPA read-only query principal for the approved account and role-group attributes. The principal receives directory read access only, not user/group mutation, service administration, or broad `FreeIPA admin` rights. Deliver its password through a read-only file-backed secret. Mount only the public CA certificate read-only; require LDAP TLS certificate-chain and hostname validation. Do not silently fall back to plaintext LDAP or an unverified TLS mode. Credential creation itself is a later, explicitly controlled implementation step on the isolated FreeIPA validation instance.

No other application or general workload container is attached to the FreeIPA validation network by Unit 2.

## 4. Lock and status

Reuse the ignored `.runtime/identity-provisioning` directory already mounted by the one-shot provisioner. In the RustFS-only command:

- Set restrictive runtime directory/file permissions and use an OS advisory lock (`flock`) on a dedicated lock file before reading or writing run status.
- A second process that cannot acquire the lock exits `already-running` before any RustFS mutation.
- The kernel releases the advisory lock when the process exits. Persisted status in `applying`, `verifying`, or `partial-failure` is evidence of an interrupted or incomplete run; require operator inspection before allowing a new mutating run. Never unlink a lock file to steal a live lock.
- Write status atomically using a temporary file and rename; store only opaque run ID, desired-policy version, timestamps/duration, safe action counts, verification categories, terminal state, and sanitized failure class.
- Never include secrets, access-key IDs, raw API bodies, object keys, or object contents.

The status directory remains ignored by Git and host-local. No new named volume or status service is required.

## 5. Pre-change IAM snapshot

Before replacing an existing managed policy document or binding, capture the pinned-image-supported IAM export or a reviewed equivalent containing only the state required for recovery. The implementation must fail closed before that replacement if capture, validation, or protected write fails.

- Store snapshots under `.runtime/identity-provisioning/iam-snapshots/`, outside Git.
- Create with restrictive umask and owner-only permissions, write via a temporary file, verify non-empty/parseable structure without printing content, then atomically rename.
- Treat snapshot data as sensitive; never include it in logs, ordinary status, artifacts, or support output.
- Operator owns retention and cleanup; do not delete prior snapshots automatically during reconciliation.
- Restore tests run only in a separately isolated RustFS instance. No automatic restore to the active RustFS service is permitted.

The export endpoint, completeness, and whether it can contain credential material must be confirmed against the exact pinned RustFS image in Build and Test. If no supported safe export exists, stop and return for design review instead of inventing partial recovery claims.

## 6. Image and dependency determinism

Keep the current digest-pinned Debian Bookworm base for `infra/identity-provisioner/Dockerfile`. Pin all apt inputs against an immutable Debian snapshot timestamp, including the existing Kerberos, PostgreSQL, Python, and botocore packages. Record exact package versions and snapshot timestamp in the Dockerfile/build metadata; no floating repository state is permitted.

The live LDAP read contract needs an LDAP client, which is absent from the current image. Add only the Python `python3-ldap` package from the same immutable Debian snapshot, pin its exact package version, and record its transitive package versions. This is a narrow runtime dependency in the existing image, not a new service or API stack; it is surfaced here for explicit approval before implementation. Keep RustFS HTTP and SigV4 on the existing urllib/botocore stack; do not add a RustFS admin SDK.

Build and Test verifies a clean image rebuild from the declared snapshot and reports the resolved image digest and package inventory without logging credentials.

## 7. RustFS transport and request behavior

- Use only the existing internal Compose endpoint `http://object-store:9000` and existing SigV4 signing stack. Do not publish a new host port or introduce a proxy/TLS sidecar.
- Keep finite per-call timeouts; preserve the current 15-second RustFS request timeout unless Build and Test shows that a different finite value is needed and records the decision.
- Use bounded retries only for read-only operations and only for classified transient transport/5xx failures. Do not blindly retry mutation requests. After an uncertain mutation result, read back the affected resource and compare with desired state before deciding whether to continue.
- Distinguish explicit not-found from access denied, timeout, server error, malformed payload, and unknown responses. Unknown status/body shape blocks before mutation or produces `partial-failure` after mutation begins.
- Validate supported create/update/read/list/delete semantics for managed IAM resources and bucket ensure operations against the exact RustFS digest. Policy replacement and binding semantics must be read back and compared as complete normalized documents.
- S3 probes use non-root role credentials and finite request timeouts. Probe cleanup targets only keys created by the current probe.

## 8. Secret and diagnostic controls

Compose delivers secrets as read-only files; source files stay under ignored `.runtime/credentials` with restrictive host permissions. No secret values go in Compose environment values, CLI arguments, logs, status, policy JSON, or generated design artifacts. Public CA material is not secret but remains read-only.

The reconciler logs allowlisted error classes rather than dependency exception strings or HTTP response bodies. Host exposure remains unchanged: no LDAP, RustFS admin, or reconciler host port is added. The standard RustFS endpoint remains internal to Compose.

## 9. Failure and completion behavior

Preflight errors produce `blocked` and no mutation. A competing invocation produces `already-running`. An error after a successful mutation produces `partial-failure`, stops subsequent mutations, preserves data, and requires inspection plus an idempotent rerun after remediation. No automatic rollback is attempted against an uncertain current state.

`complete` and `no-change` require exact managed IAM readback, verified bucket-preservation invariants, and all required positive/negative probes using non-root credentials. Status reports safe counts and action categories only.

## 10. Decision-to-requirement trace

| Infrastructure decision | Requirements/design supported |
|---|---|
| Explicit RustFS-only command in existing image | `RFS-NFR-01`, `03`, `06`; prevents unrelated provisioning side effects. |
| Dual-homed one-shot reconciler, isolated FreeIPA otherwise | `RFS-NFR-07`–`09`; preserves MIT authority and Unit 1 isolation boundary. |
| Dedicated read-only LDAP identity and verified TLS | `RFS-NFR-07`, `09`; `BR-RFS-16`. |
| `flock`, atomic sanitized status, stale-status review | `RFS-NFR-04`–`06`, `10`. |
| Protected, operator-managed IAM snapshots and isolated restore | `RFS-NFR-11`. |
| Immutable apt snapshot and exact versions, narrowly pinned LDAP client | `RFS-NFR-13`; deterministic dependencies. |
| Internal endpoint, bounded calls, no blind mutation retry, exact readback | `RFS-NFR-02`–`04`, `13`–`15`. |
| No new host ports and file-backed secrets | `RFS-NFR-07`–`10`. |

## 11. Build and Test gates

1. Confirm Compose network membership: only the reconciler joins both networks; FreeIPA remains isolated from `iceberg_net` and host LDAP/Kerberos/DNS ports remain unpublished.
2. Verify LDAP hostname resolution, CA chain, hostname validation, read-only account search access, and denied directory writes.
3. Verify a second run exits `already-running`; simulate process interruption and prove stale `applying` state blocks until operator review.
4. Verify status and logs with seeded secret markers and object names; verify none leak.
5. Capture a protected IAM snapshot and prove restore only in a distinct isolated RustFS instance.
6. Verify clean deterministic image rebuild and exact package inventory.
7. Against the pinned RustFS digest, verify API response classification, idempotency, mutation-timeout readback, partial-failure handling, exact bindings, and the full non-root access matrix.
8. Prove `lake`, production objects, `admin` mapping, writer credential identity, and legacy users remain unchanged by the isolated test fixture.
