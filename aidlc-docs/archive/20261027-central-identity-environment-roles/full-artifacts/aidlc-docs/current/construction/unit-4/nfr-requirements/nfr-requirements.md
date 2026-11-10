# NFR Requirements — FreeIPA JupyterHub Authentication and Per-User Spark Identity

## Scope and assumptions

These requirements apply to the local Docker Compose proof of concept's JupyterHub authentication, role authorization, notebook creation, credential isolation, ticket lifecycle, and workspace persistence. The approved Functional Design remains authoritative. The selected NFR answers are A/A/A/A/A/A/A/A: fixed PoC scale, correctness-first bounded operations, single-host best effort, measured but non-SLA revocation, LDAPS and per-user secret isolation, sanitized current logs without a retention SLA, preserved named workspaces without a backup commitment, and pinned versions with explicit review for architecture additions.

FreeIPA authenticates users and provides role memberships. Until Unit 6, the existing MIT KDC remains the only active KDC. Notebook Spark sessions use the matching user's own provisioned MIT keytab and RustFS identity. The writer identity remains ETL-only. Unit 3 Build and Test remains incomplete; these requirements do not accept its remaining checks and do not authorize Unit 4 implementation.

## Requirements

| ID | Quality attribute | Requirement | Verification |
|---|---|---|---|
| JH-NFR-01 | Scale | Support the three named interactive identities `developer-user`, `analyst-user`, and `admin`, plus a small manually provisioned extension. No concurrent-server, throughput, or growth commitment is made. | Verify identity behavior for the named accounts and record active server count; no load target is implied. |
| JH-NFR-02 | Performance | No end-to-end login or spawn latency SLA is set. LDAP connect/search, Docker operations, and retries must be finite and bounded. Record sanitized elapsed times for diagnosis. | Simulate a nonresponsive directory and Docker failure; confirm bounded completion and safe elapsed-time evidence. |
| JH-NFR-03 | Availability | Provide single-host best-effort operation with no HA, RTO, or RPO commitment. FreeIPA, Hub, Docker, KDC, or required credential-mount failure denies a new login/spawn. Recovery is operator-led. | Interrupt each dependency separately and verify login/spawn fails closed without another role or identity. |
| JH-NFR-04 | Authentication correctness | Login requires a successful FreeIPA LDAPS authentication and a fresh account/group authorization result. Invalid credentials, disabled/locked users, unresolved membership, unknown roles, and LDAP errors deny access. | Exercise valid/invalid credentials, disabled/locked account, absent/conflicting group, and lookup-failure cases against the isolated directory. |
| JH-NFR-05 | Role consistency | A new notebook spawn requires a fresh group decision and exactly one supported data role, or the separate explicit admin mapping. Cached auth state alone must not authorize a new spawn. Writer/service identities are excluded. | Change role membership between login and spawn; verify stale state does not authorize spawn. Verify writer and conflict cases are denied. |
| JH-NFR-06 | Revocation | No numeric revocation SLA is approved. A role removal/account disable must block subsequent login and spawn after a fresh directory check. An active server requires an explicit stop/revocation action; measure request-to-stop and ticket-cache destruction time and document observed behavior. | Remove a disposable membership/disable a test identity, invoke the approved stop workflow, and capture request/completion timestamps plus evidence that the server and tmpfs cache are gone. |
| JH-NFR-07 | Credential protection | Require LDAPS hostname and CA validation. Protect JupyterHub auth state with a stable protected crypt key and store only required identity/group attributes, never submitted passwords. Mount only each user's own keytab and RustFS credential files read-only. Keep ticket caches in restrictive per-container tmpfs. | Inspect certificate validation, auth-state contents/configuration, mounts, permissions, and process environment without printing secret values; confirm no writer/admin/other-user credential is available in human containers. |
| JH-NFR-08 | Identity isolation | A notebook's Kerberos principal and RustFS identity must both match the authenticated user. Missing, expired, or mismatched credentials fail closed; there is no service-account fallback. | Inspect `klist` principal and sanitized effective identity, then verify RustFS allow/deny behavior using disposable data as each role. |
| JH-NFR-09 | Audit safety | Current Hub/container logs record safe principal reference, role, decision, failure category, lifecycle stage, correlation ID, and elapsed/revocation timing where available. Exclude passwords/form data, keys, keytabs, ticket contents, full LDAP responses, S3 request bodies, and user data. No retention SLA is set. | Trigger allow, deny, spawn failure, and revocation cases; inspect logs for required safe fields and scan using secret markers without displaying actual secrets. |
| JH-NFR-10 | Workspace preservation | Named workspaces persist across normal server stop/restart. Do not automatically rename, transfer, or delete workspaces for disabled/renamed users. Preserve the current admin workspace and all legacy workspaces during this unit. No backup or recovery-point commitment is set. | Write a disposable marker in each test workspace, stop/restart the server, verify persistence and per-user isolation; inspect that no workspace volume was removed or reassigned. |
| JH-NFR-11 | Failure handling | Directory, registry, credential-file, KDC, or Docker errors must not cause default role selection, stale-role authorization, or credential fallback. User-facing errors are generic; operator diagnostics are bounded and secret-safe. | Inject each dependency/mapping failure in an isolated test and confirm denial, bounded response, sanitized error classification, and no container created with broader credentials. |
| JH-NFR-12 | Compatibility | Keep currently pinned JupyterHub, DockerSpawner, notebook, FreeIPA, and Kerberos versions unless compatibility evidence identifies a blocker and the user approves the change. Do not add an authenticator package, controller, secret mechanism, or network attachment without compatibility evidence and explicit architecture approval. | Record the effective version/image inventory and review proposed dependency/network changes before implementation. |
| JH-NFR-13 | Verification and preservation | Use isolated FreeIPA/test identities and disposable notebook data for acceptance. Capture the pre-change Hub account/workspace/credential mapping and compare after implementation. Never use production data or delete workspaces as test fixtures. | Review before/after sanitized mapping and volume inventory; run auth and notebook tests only after a separately approved implementation and Build and Test plan. |

## Acceptance constraints

- FreeIPA authentication and group authorization are distinct from Kerberos ticket acquisition and RustFS S3 authorization.
- A group grant alone does not provision a RustFS identity, keytab, or identity-registry record; absent provisioning denies spawn.
- Unit 3's incomplete direct Spark checks remain a separate gate. Unit 4 acceptance must not be reported as closing those checks.
- Active-session revocation has no approved numeric SLA; record the measured result and do not claim immediate revocation from an LDAP group edit alone.
- Admin privileges are separate from data roles. Neither developer nor analyst receives Hub administration.

## Traceability

- JH-NFR-01–03: fixed PoC scope, bounded response, single-host dependency behavior.
- JH-NFR-04–06: authentication/group correctness and measured revocation.
- JH-NFR-07–08: TLS, credential confidentiality, per-user identity alignment.
- JH-NFR-09–11: safe audit, workspace preservation, fail-closed recovery.
- JH-NFR-12–13: compatibility and isolated verification/preservation evidence.

## Approval Gate

The Unit 4 NFR Requirements Plan was completed with A/A/A/A/A/A/A/A. Review and approve this specification and `tech-stack-decisions.md` before Unit 4 NFR Design. This document makes no claim that its verification items have passed and authorizes no runtime changes or tests.
