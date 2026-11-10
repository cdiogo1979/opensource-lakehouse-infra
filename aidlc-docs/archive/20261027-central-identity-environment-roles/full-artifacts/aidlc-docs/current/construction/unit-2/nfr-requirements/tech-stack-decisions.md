# Tech-Stack Decisions — RustFS Role Policies and Reconciliation

## Approved Constraints

| Area | Decision | Rationale / boundary |
|---|---|---|
| Object store | Retain the existing `rustfs/rustfs:1.0.0-glibc` image pinned by digest in Compose. | No version upgrade is included in Unit 2. IAM APIs and evaluation semantics must be verified against this exact image. |
| Reconciler runtime | Extend the existing `infra/identity-provisioner` Python container and operator invocation path. | The current provisioner already owns SigV4 RustFS administration and protected credential mounts; no new controller, scheduler, or service is approved. |
| RustFS API client | Retain the current SigV4 request stack (`botocore` signing plus Python HTTP client) and RustFS `/rustfs/admin/v3` endpoints, subject to pinned-image compatibility tests. | Avoids a new admin SDK/API version migration; use bounded timeouts and redact all response payloads. |
| Directory integration | Use an authenticated read-only LDAP query contract for FreeIPA users/groups. Keep this credential separate from FreeIPA `admin` and the scoped group-membership mutator. | The Unit 2 functional design requires directory state as the source of truth. Concrete bind identity, TLS trust, and mount are Infrastructure Design decisions. |
| Policy source | Store exact role policy JSON in version-controlled project configuration, separate from secret files. | Makes reviewed desired permissions reproducible; secrets and access keys never belong in policy files. |
| Policy representation | Three project-owned role policies attached to native RustFS IAM groups matching FreeIPA role group names; full-bucket resources for the approved bucket matrix. | RustFS documents native IAM groups and group policy inheritance. Exact API and behavior on the pinned image remain Build and Test gates. |
| Locking/status | Use a single-host protected runtime lock/status path under ignored `.runtime/identity-provisioning`; serialize runs and report sanitized terminal state. | Matches the approved one-run-at-a-time and local Compose boundary. Stale-lock recovery must require operator inspection. |
| IAM backup | Use the pinned RustFS IAM export API or equivalent protected snapshot before changing an existing managed policy/binding; keep mode restrictive and restore only in an isolated instance. | Supports the approved pre-change recovery answer. The export may contain credential material and is handled as a secret-bearing backup. |
| Secret delivery | Continue file-backed Compose secrets/credential mounts. RustFS admin credentials are read-only to the reconciler; human credentials are delivered by Unit 4. | Keeps secret values out of command arguments, environment literals, and logs. |
| Dependencies | Keep versions deterministic. Current provisioner base image is digest-pinned, but several Debian package dependencies are not individually version-pinned; implementation must add a reproducible package/dependency lock or document a pinned repository snapshot before Unit 2 acceptance. | Satisfies the approved dependency answer without introducing a new service. Resolve the current gap during Infrastructure Design/Code Generation. |
| Testing | Use isolated RustFS and FreeIPA test identities for failure, concurrency, idempotency, backup/restore, and role probes; never use root credentials for S3 authorization probes. | Prevents verification from mutating production buckets or producing false-positive access results. |

## Deferred Decisions

- Exact single-run lock mechanism and safe stale-lock procedure.
- Read-only FreeIPA bind identity, TLS CA distribution, and secret mount paths.
- Exact package lock/repository snapshot strategy for the existing Debian provisioner image.
- IAM export response sensitivity, backup location/mode, and isolated restore fixture.
- Exact timeout values and retry classification for each RustFS/LDAP operation.
- The supported subset of RustFS admin v3 APIs on the pinned image and its exact not-found/error response mapping.

These decisions belong in Unit 2 NFR Design and Infrastructure Design. They must preserve the NFR requirements and functional fail-closed behavior.

## Change Control

Any floating image/dependency, new always-on service, host-published admin endpoint, automatic rollback over unknown state, policy scope expansion, or writer S3-key rotation requires review against the approved scope before implementation.
