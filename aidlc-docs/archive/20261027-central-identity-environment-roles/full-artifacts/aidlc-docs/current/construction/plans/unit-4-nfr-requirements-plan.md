# Unit 4 NFR Requirements Plan — FreeIPA JupyterHub Authentication and Per-User Spark Identity

## Unit and Approved Functional Baseline

Unit 4 connects FreeIPA human authentication and role membership to JupyterHub notebook sessions. The approved functional design is in `construction/unit-4/functional-design/`. `lakehouse-developers` and `lakehouse-analysts` may receive notebooks only after exact role and per-user credential mapping; `lakehouse-writers` and `write-service-account` are excluded. The separately allowlisted `admin` retains its Hub administrator mapping. Each notebook receives only its own read-only Kerberos keytab and RustFS credentials, with a private tmpfs ticket cache and a distinct persistent workspace.

Until Unit 6, FreeIPA authenticates users while the active MIT KDC remains the sole ticket authority. The authenticated username must map to that same user's active-KDC principal and keytab. No runtime, account, credential, network, KDC, or workspace changes are in scope for this NFR Requirements stage.

Unit 3 Build and Test remains incomplete with documented residual checks. These NFRs cover the quality constraints for future Unit 4 implementation and acceptance; they do not close Unit 3 or authorize Unit 4 runtime changes.

## NFR Assessment Checklist

- [x] Review the approved Unit 4 functional design and record the authentication, authorization, credential, ticket-cache, revocation, and workspace boundaries.
- [x] Inspect the current Hub/spawner/session startup and FreeIPA topology through source/configuration review; do not change runtime state.
- [x] Confirm supported account count and concurrent notebook server assumptions: A.
- [x] Confirm LDAP authentication, group lookup, and spawn response-time behavior and timeout/retry bounds: A.
- [x] Confirm availability and fail-closed behavior for FreeIPA, Hub, KDC, registry/credential mounts, and Docker API failures: A.
- [x] Confirm group-change and account-disable propagation, auth-state/session cache handling, and active-server revocation expectations: A.
- [x] Confirm LDAPS trust, auth-state encryption key, per-user credential file protection, and ticket-cache isolation: A.
- [x] Confirm sanitized authentication/spawn/revocation audit evidence and retention expectations: A.
- [x] Confirm workspace persistence and preservation/rollback evidence; no automatic workspace deletion or transfer: A.
- [x] Confirm authenticator/Hub/Spawner compatibility policy and whether dependencies or network attachments may be added: A.
- [x] Record answers and generate `construction/unit-4/nfr-requirements/nfr-requirements.md` and `tech-stack-decisions.md` for review before Unit 4 NFR Design.

## Assessment Boundaries

- **Scale/performance**: Existing local proof of concept with three named interactive identities and per-user notebook containers. No concurrency or latency SLA is currently approved.
- **Availability/recovery**: FreeIPA, JupyterHub, Docker, KDC, and credential mounts are required dependencies. Authentication or spawn failure must not authorize a stale/default role or use another identity.
- **Revocation/consistency**: FreeIPA group removal prevents future authorization after a fresh check. An active notebook requires a separate stop action; the expected maximum completion time needs a user decision and verification plan.
- **Security**: LDAPS certificate validation, protected auth state, exact user-to-credential mapping, read-only per-user mounts, private tmpfs ticket caches, and no writer fallback are baseline functional rules. No secret enters ordinary environment values or logs.
- **Auditability**: Record safe identity references, role, result, stage, and timing without passwords, keytabs, tickets, access keys, or submitted authentication data.
- **Preservation/recovery**: Preserve the current `admin` mapping/workspace and existing user workspaces. Workspace retention and recovery requirements must not imply deletion or automatic cross-user transfer.
- **Compatibility**: Keep currently pinned JupyterHub, LDAPAuthenticator, DockerSpawner, FreeIPA, and notebook image versions unless a documented compatibility failure and explicit approval justify a change.
- **Verification**: NFRs add boundedness, fail-closed behavior, revocation timing, confidentiality, evidence, and preservation criteria. Functional allow/deny behavior remains defined in Unit 4 Functional Design.

## Questions

Choose one option for each question. Option A is recommended for the local proof of concept. Choose `X` and describe the requirement if none fits.

### Question 1 — Scale and concurrency

What scale should interactive JupyterHub support?

A) Fixed local PoC: `developer-user`, `analyst-user`, and `admin`, with a small manually provisioned extension; no concurrency or throughput commitment. **(Recommended)**

B) Set maximum users, concurrent notebook servers, and expected growth in `X`.

X) Other (describe scale and concurrency).

[Answer]:A

### Question 2 — Authentication and spawn response time

What response-time objective should apply to login and notebook spawn dependencies?

A) Correctness first; no end-to-end latency SLA. LDAP connect/search, Docker operations, and retries must have finite configured timeouts; record sanitized elapsed time. **(Recommended)**

B) Specify maximum login/spawn duration and expected concurrency in `X`.

X) Other (describe timing requirements).

[Answer]:A

### Question 3 — Dependency failure and availability

What should happen when FreeIPA, JupyterHub, Docker, the active KDC, or the credential registry/mount is unavailable?

A) Single-host best effort with no HA/RTO guarantee. New login/spawn fails closed; no stale/default role, alternate account, or broader credential fallback. Recovery is operator-led. **(Recommended)**

B) Define availability, RTO/RPO, and recovery automation in `X`.

X) Other (describe availability/failure behavior).

[Answer]:A

### Question 4 — Role revocation and active notebook termination

What maximum delay should apply after disabling an account or removing its role membership?

A) No numerical SLA for this PoC. Revalidate before login and every spawn; active sessions require an explicit stop/revocation action, and observed request-to-stop/cache-destruction time must be measured and documented. **(Recommended)**

B) Require a maximum time for future login denial and active-server termination in `X`.

X) Other (describe propagation and termination expectations).

[Answer]:A

### Question 5 — Authentication and credential security

What security posture applies to the Hub and notebook credential boundary?

A) Require LDAPS with hostname/CA validation; protect JupyterHub auth state with a stable secret key; use per-user read-only keytab/S3 mounts, restrictive permissions, and a private tmpfs ticket cache. Never log/store passwords or mount writer/admin credentials into human notebooks. **(Recommended)**

B) Add TLS for all internal services and define certificate issuance/rotation requirements in `X`.

X) Other (describe credential and transport requirements).

[Answer]:A

### Question 6 — Audit evidence and retention

What evidence should be retained for login, role decision, spawn, and revocation?

A) Record a sanitized principal reference, role, decision, failure category, event/stage, correlation ID, and elapsed/completion time. Exclude passwords, submitted form data, secret values, keytabs, and tickets. Keep current runtime logs; no retention SLA. **(Recommended)**

B) Define an immutable audit destination, access model, and retention period in `X`.

X) Other (describe audit/retention requirements).

[Answer]:A

### Question 7 — Workspace persistence and recovery

What protection applies to notebook workspaces during identity changes and failures?

A) Preserve named volumes across normal stop/restart; do not automatically rename, transfer, or delete any workspace. No backup/RPO commitment; separately review any later migration or cleanup. **(Recommended)**

B) Require workspace backup/recovery with specified RPO/RTO and retention in `X`.

X) Other (describe workspace lifecycle/recovery).

[Answer]:A

### Question 8 — Version and architecture changes

How should compatibility findings be handled?

A) Keep current component versions pinned. Add an authenticator, dependency, network attachment, secret mechanism, or active-session controller only after compatibility evidence and explicit architecture approval. **(Recommended)**

B) Name allowed component/version/network changes and required compatibility evidence in `X`.

X) Other (describe change policy).

[Answer]:A

## Approval Gate

Complete the NFR answers and approve the generated requirements/technology decision artifacts before Unit 4 NFR Design. This plan authorizes documentation only. It does not authorize package installation, Docker image rebuilds, Compose/network changes, FreeIPA membership edits, credential/keytab changes, service operations, or workspace changes. Unit 3 residual verification gaps remain subject to their existing gate before Unit 4 implementation and integrated Build and Test.

## Answers and completion

The user completed the plan with the recommended answers A/A/A/A/A/A/A/A. The requirements and technology decisions are generated for review. No latency or revocation SLA, backup/RPO, HA, or retention commitment was added.
