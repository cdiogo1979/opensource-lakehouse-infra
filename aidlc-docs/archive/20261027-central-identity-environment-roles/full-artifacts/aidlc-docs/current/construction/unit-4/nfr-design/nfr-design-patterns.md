# NFR Design Patterns — FreeIPA JupyterHub Authentication and Per-User Spark Identity

## Design scope

This design translates `JH-NFR-01`–`JH-NFR-13` and the approved Unit 4 functional rules into quality patterns for the local Docker Compose JupyterHub deployment. It does not implement or change authentication, networking, credentials, KDC authority, or workspaces. Unit 3 Build and Test remains separately open.

## Identity and authorization pattern

JupyterHub uses two authorization decision points:

1. **Login**: authenticate the submitted human credentials against FreeIPA over LDAPS; resolve account enabled/locked state and allowed group membership.
2. **Spawn**: query FreeIPA again for current account and role membership before creating the user's container. Do not authorize spawn solely from serialized/cached auth state created at login.

The supported data roles are exact matches for `lakehouse-developers` or `lakehouse-analysts`; simultaneous membership in both is a deny. `lakehouse-writers`, `write-service-account`, and unknown role states are denied. The `admin` user is handled through an explicit administrator allowlist and its own identity registry entry; Hub administrator privilege does not result from membership in either data group.

If FreeIPA is unreachable, its response is malformed, the user is disabled, the group lookup is missing, or role resolution is ambiguous, login/spawn fails closed. Do not use a stale role, a default group, or a service identity. The exact Hub-side LDAP client/API and group filter must be selected and proven compatible with the pinned JupyterHub/LDAPAuthenticator/FreeIPA combination in later stages.

## Authentication-to-notebook identity pattern

The login password validates a FreeIPA account only. It is not persisted or reused for Kerberos. A provisioning-owned registry maps an admitted canonical username to exactly one expected role, Kerberos principal, per-user keytab, RustFS credential pair, and persistent workspace. It is the only source for host credential paths and volume names; usernames cannot construct arbitrary paths.

Before container creation, validate the registry entry and each credential file as present and safe. DockerSpawner mounts only that user's keytab and RustFS files read-only. The notebook entrypoint obtains a ticket with that keytab into the container's private tmpfs, verifies the expected principal, and aborts before the notebook starts on any mismatch. The S3 credentials and Kerberos principal must correspond to the same user. No writer, HMS, RustFS admin, or other user's credential is available to a human notebook.

During the transition, FreeIPA is the login directory and MIT remains the sole active KDC. An MIT keytab is accepted only when its principal exactly matches the authenticated canonical user. A FreeIPA keytab must not be introduced into this path until the coordinated Unit 6 authority cutover.

## Bounded dependency and fail-closed pattern

All LDAP bind/search, spawn authorization lookup, Docker API, and notebook startup operations have finite configured timeouts. Authentication/authorization lookups are not retried with another identity or stale result. Any retry for a known transient infrastructure operation is bounded and cannot repeat a credential bind indefinitely. Exact numeric values are selected in Infrastructure Design and verified against the local setup; no end-to-end latency SLA is implied.

| Failure | Required behavior |
|---|---|
| LDAPS unavailable, certificate invalid, bind/search timeout, or unexpected response | Deny login/spawn; expose generic user-facing error and sanitized operator category |
| Account disabled/locked, absent group, conflicting role, writer identity, or absent registry entry | Deny before Docker container creation |
| Credential file missing, unsafe, or mismatched | Deny before container creation; do not create partial mounts |
| Docker API/start timeout or notebook `kinit` failure | Report server start failure; stop/remove partial container; do not fall back to another identity |
| KDC unavailable or unexpected principal | Notebook startup fails before Jupyter/Spark becomes available |
| RustFS authorization failure | Spark data operation fails as the user; no writer/admin retry |

Timeouts, errors, and retries must be bounded. A timeout or ambiguous result is never interpreted as an allow or as evidence that a user/group is absent in a way that grants a fallback role.

## Revocation and cache pattern

Fresh FreeIPA account/group validation occurs on login and immediately before every spawn. This prevents stale Hub auth state from authorizing a new notebook. No numeric revocation SLA is approved.

For an already-running notebook, directory changes do not themselves stop the container. The approved revocation operation is explicit and operator-triggered: disable/remove role membership in FreeIPA, stop the user's notebook through the Hub/DockerSpawner lifecycle, confirm container termination and tmpfs ticket-cache destruction, then verify a new spawn is denied. Record request and completion times. Do not claim that changing LDAP membership alone revokes an existing TGT or RustFS key.

## Secret protection and observability pattern

- LDAPS validates both the CA chain and endpoint hostname. FreeIPA is reachable only over the approved internal path; no public listener or TLS bypass is introduced.
- JupyterHub auth state is encrypted with a stable protected crypt key and contains only the identity/group attributes needed for authorization. Submitted passwords are not persisted.
- Per-user keytab and RustFS files are read-only mounts; the ticket cache is private tmpfs with restrictive ownership/mode and is destroyed with its container.
- Existing Hub and container logs record sanitized principal reference, role resolution, event/stage, decision/failure category, correlation identifier, and elapsed/revocation time where available.
- Exclude passwords or submitted form data, access/secret keys, keytab bytes, tickets, raw LDAP responses, full dependency payloads, and notebook data. No separate audit service or retention SLA is selected.

## Workspace preservation pattern

Keep one named persistent volume mapped to each canonical username. Container removal and tmpfs destruction must not remove the mounted workspace. Preserve the current admin mapping/workspace and all legacy user volumes during this unit. New role users get separate volumes; there is no automatic legacy-volume rename, transfer, or cleanup. Before implementation, capture a sanitized username-to-volume inventory; after implementation, compare it and verify persistence with disposable marker files.

## Compatibility and version pattern

Keep component versions pinned. The current Hub uses `DummyAuthenticator`, while the approved target needs FreeIPA group-aware authentication. LDAPAuthenticator is the documented candidate, but exact version compatibility, FreeIPA group lookup, spawn-time revalidation API, crypt-key behavior, and LDAPS network access remain verification requirements. Do not install dependencies, rebuild images, or attach networks as part of this design. Any required dependency/network architecture change needs evidence and explicit approval in the appropriate later gate.

## Verification pattern

The Unit 4 Build and Test plan must use isolated directory identities and disposable notebook data to test valid/invalid login, disabled/locked status, both role groups, role conflict, writer exclusion, explicit admin mapping, stale group state between login and spawn, directory failures, exact credential mounts, `klist` principal, RustFS role allow/deny, no fallback, server stop/cache destruction, and workspace persistence. Record observed timings without claiming an unapproved SLA. Unit 3 residual checks remain separate.

## Traceability

| Requirement | NFR pattern |
|---|---|
| `JH-NFR-01`–`02` | Fixed PoC scope; bounded calls and sanitized elapsed time |
| `JH-NFR-03`–`06` | Fail-closed dependency behavior; fresh login/spawn group checks; measured revocation |
| `JH-NFR-07`–`08` | LDAPS trust; encrypted minimal auth state; per-user credentials and ticket cache |
| `JH-NFR-09`–`11` | Sanitized lifecycle evidence; workspace preservation; safe failure handling |
| `JH-NFR-12`–`13` | Pinned versions; compatibility approval; isolated verification and inventory comparison |

## Deferred decisions

Infrastructure Design must select a stable internal LDAPS endpoint, CA-file mount, approved Hub-to-FreeIPA network path, protected crypt-key source, exact finite timeouts, and the concrete provisioning registry format. Compatibility verification must show how the selected authenticator obtains a fresh role decision before spawn. If this requires an unapproved dependency, network, or service change, stop for explicit architecture approval. Build and Test must prove the behavior; this NFR Design alone is not evidence of implementation.
