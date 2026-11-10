# Unit 4 Infrastructure Design Plan — FreeIPA JupyterHub Authentication and Per-User Spark Identity

## Approved Baseline

Unit 4 Functional Design and NFR Design are recorded in `construction/unit-4/functional-design/` and `construction/unit-4/nfr-design/`. FreeIPA authenticates human users over validated LDAPS. The Hub resolves only the developer/analyst data roles and the separately mapped `admin`; it excludes `lakehouse-writers` and rejects missing/conflicting roles. Login and every spawn require current account/group state. A provisioning-owned identity map selects each user's own keytab, RustFS credentials, and workspace. Notebooks use read-only credential mounts and a private tmpfs ticket cache.

The active MIT KDC remains the only Kerberos authority until Unit 6. FreeIPA keytabs, realm routing, KDC aliases, and production service principals must not be changed in Unit 4. Existing admin and legacy workspaces must remain intact. Unit 3 Build and Test remains incomplete and is not accepted or waived here.

Source inspection found the Hub currently uses `DummyAuthenticator`, DockerSpawner, a username-to-credential/workspace map, and only the `iceberg_net` network. The FreeIPA validation service is profile-gated on a separate `freeipa_validation_net`, publishes its Web UI only on localhost:8443, and is not currently reachable from the Hub container. Hub image requirements currently pin JupyterHub, DockerSpawner, and Docker client packages but do not include LDAPAuthenticator. The current FreeIPA bootstrap creates data-role groups and users but does not provision a separate JupyterHub human administrator account. These are design inputs, not authorization to change runtime state.

## Infrastructure Design Checklist

- [x] Review approved Unit 4 Functional Design, NFR Requirements, and NFR Design; identify implementation-level choices still open.
- [x] Inspect Hub/Spawner configuration, notebook startup, FreeIPA Compose profile/network, CA artifact references, existing identity files, and named workspace mappings without changing runtime state.
- [x] Select the internal LDAPS DNS endpoint and decide how only the Hub reaches FreeIPA without exposing LDAP to ordinary lakehouse containers or publishing a new host port.
- [x] Define CA certificate delivery, hostname verification, bind/search behavior, bounded LDAP timeouts, and FreeIPA readiness handling.
- [x] Choose the compatible group-aware authenticator package/version and specify its deployment in the Hub image; validate compatibility against the pinned Hub and FreeIPA schema before implementation.
- [x] Define login-time and pre-spawn role lookups, exact group DNs/filter, role-conflict rejection, FreeIPA built-in administrator exclusion, and separate human administrator account provisioning expectations. The prior suggestion to name a second account `admin` is invalid because FreeIPA reserves that identity; a distinct human username remains a clarification gate.
- [x] Specify protected JupyterHub auth-state crypt-key delivery and ensure submitted passwords are never persisted.
- [x] Define the strict identity registry location/schema, file ownership/modes, username allowlist, and validation of each expected principal and per-user credential pair.
- [x] Map developer/analyst/admin identities to separate read-only keytab/RustFS mounts and distinct named workspaces; preserve `admin`, `user_a`, and `user_b` workspaces and credentials, subject to resolving the admin identity mapping before implementation.
- [x] Define notebook tmpfs/cache startup and failure behavior while retaining the active MIT KDC as the only KDC.
- [x] Specify operator revocation steps for active servers, safe lifecycle logs, and evidence collection without a numeric SLA or new controller.
- [x] Define startup behavior when FreeIPA validation is profile-gated or unhealthy; no stale authorization or alternate authenticator fallback.
- [x] Generate `construction/unit-4/infrastructure-design/infrastructure-design.md` and `deployment-architecture.md` after plan approval.

## Infrastructure Questions

Complete each `[Answer]:` field. Recommended options retain the local PoC and least-privilege boundaries; choose `X` and describe a different choice if needed.

### Question 1 — Hub-to-FreeIPA network path

How should JupyterHub reach FreeIPA LDAPS?

A) Put only JupyterHub and the FreeIPA validation service on a dedicated internal Docker network for LDAPS; keep the Hub's existing lakehouse network for HMS/KDC/RustFS and preserve the localhost-only Web UI port. Do not publish LDAP ports. **(Recommended)**

B) Attach JupyterHub to the existing `freeipa_validation_net`; document the resulting dual-network exposure and prove ordinary lakehouse containers cannot reach FreeIPA in `X`.

X) Other (describe the exact network path and exposure).

[Answer]: A — dedicated internal network shared only by Hub and FreeIPA; no host LDAP port.

### Question 2 — FreeIPA endpoint, trust, and readiness

How should LDAPS trust and service readiness be configured?

A) Use a stable internal hostname covered by the FreeIPA certificate, mount the exported FreeIPA CA read-only into the Hub, require hostname/chain validation, use finite LDAP timeouts, and make Hub login/spawn fail closed while FreeIPA is unavailable. **(Recommended)**

B) Use an alternate certificate/endpoint arrangement with its validation and rotation plan in `X`.

X) Other (describe endpoint, trust, and failure behavior).

[Answer]: A — stable LDAPS hostname, read-only CA mount, certificate/hostname validation, bounded operations, fail closed.

### Question 3 — Authenticator dependency

How should group-aware FreeIPA login be implemented?

A) Use a pinned LDAPAuthenticator release compatible with JupyterHub 5.3.0 after compatibility evidence; add it to the Hub image only after version/schema validation. No new auth service. **(Recommended)**

B) Implement a project-owned authenticator/LDAP adapter; document security review and maintenance ownership in `X`.

X) Other (describe authenticator and compatibility constraints).

[Answer]: A — LDAPAuthenticator candidate, with concrete release pin and FreeIPA compatibility proof required before implementation.

### Question 4 — Role lookup and admin mapping

How should roles and platform admin be determined?

A) Match exact FreeIPA group DNs for `lakehouse-developers` or `lakehouse-analysts` at login and re-query before spawn; reject both/neither/writer. Exclude FreeIPA's built-in directory administrator. The platform administrator must use a distinct, nonprivileged FreeIPA human username; exact username and principal mappings remain a clarification gate. **(Recommended, corrected for FreeIPA's reserved `admin` identity)**

B) Use different group/administrator names and document the exact mapping and separation in `X`.

X) Other (describe role and administrator mapping).

[Answer]: A, with the correction above. The distinct platform-admin username, MIT principal, RustFS identity, and workspace mapping must be resolved before code generation.

### Question 5 — Auth state and secret files

How should Hub state and identity files be protected?

A) Deliver the stable JupyterHub crypt key as a protected secret file; encrypt required auth state; never retain submitted passwords. Keep CA, keytabs, and RustFS credential files as read-only mounts with restrictive host/container permissions. **(Recommended)**

B) Use a named secret manager or external key service; describe its network/lifecycle in `X`.

X) Other (describe secret source and state handling).

[Answer]: A — protected Compose secret for the stable auth-state crypt key; encrypted minimal state and no submitted-password persistence.

### Question 6 — Username registry and workspaces

How should authorized usernames map to notebook credentials and data?

A) Use a Hub-owned, provisioning-maintained explicit allowlist/registry for canonical username, one role, expected MIT principal, credential file names, and named workspace. Validate files before spawn; no username-derived host paths. Preserve admin and legacy volumes without transfer/deletion. **(Recommended)**

B) Resolve arbitrary role-group members dynamically from a credential broker; define broker and lifecycle in `X`.

X) Other (describe mapping and persistence).

[Answer]: A — explicit provisioning-owned registry with strict path/ownership/mode/principal validation and preserved distinct workspaces.

### Question 7 — Ticket cache and active revocation

How should notebook ticket state and already-running sessions be handled?

A) Keep the user's keytab read-only, acquire/verify the expected principal in the existing private tmpfs cache, and use an operator-triggered Hub stop for active revocation. Record stop/cache-destruction time; do not add a controller or claim a numeric SLA. **(Recommended)**

B) Add a bounded automated session controller with a specified revocation target and compatibility/security review in `X`.

X) Other (describe ticket and revocation behavior).

[Answer]: A — read-only per-user keytab, private tmpfs cache, and operator stop for active-session revocation.

### Question 8 — Startup, compatibility, and preservation

How should deployment proceed while FreeIPA is profile-gated and Unit 3 has open checks?

A) Keep FreeIPA validation opt-in; JupyterHub must fail closed if it is not reachable and must not fall back to DummyAuthenticator. Preserve pinned data services, MIT KDC, credentials, and workspaces. Runtime rollout/integrated acceptance waits for the Unit 3 gate or explicit waiver. **(Recommended)**

B) Make FreeIPA a default required service and change startup/health dependencies; define the impact and approval in `X`.

X) Other (describe rollout and gate behavior).

[Answer]: A — FreeIPA remains opt-in, authentication fails closed without fallback, and integrated rollout stays gated on Unit 3 closure or waiver.

## Design Constraints

- This plan authorizes infrastructure design only. Do not alter Compose, image builds, networks, FreeIPA configuration, identity state, credentials, keytabs, workspaces, or services.
- Do not connect the Hub to the FreeIPA KDC for Spark ticket issuance or change the active MIT KDC. The intended Unit 4 directory connection is LDAPS only; Unit 6 owns Kerberos cutover.
- Never use FreeIPA's built-in `admin` account as the interactive JupyterHub platform account; keep directory administration separate from the human Hub admin.
- Do not mount `write-service-account`, HMS, RustFS admin, or another user's credentials into a notebook.
- Preserve existing named volumes and all production state. Do not migrate `user_a`/`user_b` workspace data into the new users.
- Any chosen authenticator package/version or network topology must have compatibility/security evidence. Changes beyond the approved design return for explicit review.
- Unit 3 verification gaps remain open; Unit 4 implementation and integrated Build and Test remain gated.

## Approval Gate

The user approved this Unit 4 Infrastructure Design Plan and requested continuation on 2026-10-27. Detailed design artifacts have been generated. Approval authorizes documentation only, not runtime configuration, dependency installation, network changes, credential provisioning, service operations, tests, or workspace changes. The exact distinct FreeIPA human username and its administrator/MIT/RustFS/workspace mappings remain unresolved and block Unit 4 implementation until clarified.
