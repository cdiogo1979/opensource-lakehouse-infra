# Unit 4 NFR Design Plan — FreeIPA JupyterHub Authentication and Per-User Spark Identity

## Approved Baseline

Unit 4 NFR Requirements and technology decisions are recorded in `construction/unit-4/nfr-requirements/`. They select fixed local PoC scale, bounded operations without latency SLA, single-host best-effort availability, measured active-session revocation without a numeric SLA, LDAPS validation, protected auth state, per-user read-only credential mounts, sanitized current logs, preserved named workspaces, and pinned component versions.

The approved Functional Design keeps FreeIPA login separate from Kerberos ticket acquisition. MIT remains the only active KDC through Unit 6. The Hub admits the developer/analyst groups and explicitly mapped admin, excludes the writer, rejects conflicting roles, and requires a provisioning-owned identity registry. Unit 3 Build and Test has residual verification items and remains a separate open gate.

## Design Checklist

- [x] Trace quality patterns to `JH-NFR-01` through `JH-NFR-13` and the approved Unit 4 functional rules.
- [x] Define the logical authentication and group-authorization pattern across FreeIPA, JupyterHub, DockerSpawner, and notebook startup.
- [x] Define bounded LDAP/Docker operations, retry behavior, fail-closed outcomes, and sanitized diagnostics.
- [x] Ensure role membership is fresh at both login and spawn; specify how spawn revalidation avoids relying on stale login auth state.
- [x] Define identity-registry validation and the invariant that only the matched user's read-only keytab and RustFS credentials are mounted.
- [x] Define ticket-cache confidentiality/lifecycle and separation from persistent workspaces.
- [x] Define operational revocation steps for future starts and already-running containers, plus timing evidence without inventing an SLA.
- [x] Define TLS trust, protected auth-state key handling, and secret-safe logs without committing to unapproved runtime changes.
- [x] Define workspace preservation and pre/post evidence for future implementation.
- [x] Record exact version/network/dependency constraints and deferred decisions for Infrastructure Design or Build and Test.
- [x] Generate `construction/unit-4/nfr-design/nfr-design-patterns.md` and `logical-components.md` after this plan is approved.
- [x] Present the NFR Design artifacts for review before Unit 4 Infrastructure Design.

## Design Boundaries

- Planning and design only. Do not install LDAPAuthenticator, rebuild images, modify Compose/networks, change FreeIPA users/groups, rotate or create credentials/keytabs, start/stop services, or modify workspaces.
- Do not change KDC aliases, realm routing, HMS principals, service keytabs, or the active MIT authority. Unit 6 owns the coordinated cutover.
- Do not mount `write-service-account`, HMS, RustFS admin, or another user's credentials into a human notebook.
- Do not add an active-session controller, audit service, secret store, HA service, or other component without compatibility evidence and explicit architecture approval.
- Keep existing named workspace volumes and admin mapping. No data migration, workspace deletion, or automatic cross-user transfer.
- Unit 3's residual Build and Test gaps remain open. Unit 4 design does not close or waive them; resolve or explicitly waive the Unit 3 gate before Unit 4 implementation/integrated acceptance.
- Unit 4 Build and Test must use isolated identities and disposable data, verify the FreeIPA schema and TLS behavior, inspect per-user mounts, exercise failures and revocation, and record observed timings. No test is authorized by this design plan.

## Design Questions

1. **Fresh role validation:** Use an internal Hub-side FreeIPA membership lookup before each spawn, in addition to login authentication, so saved auth state cannot authorize a stale role. Confirm the lookup identity and bounded failure behavior in Infrastructure Design.
2. **Provisioning registry:** Keep an explicit provisioning-owned mapping of canonical username to role, expected principal, credential files, and workspace. Reject missing/incomplete mappings; do not derive arbitrary host paths from usernames.
3. **Credential and ticket boundary:** Mount the user's own keytab/S3 files read-only, validate the expected principal before notebook launch, and store TGT only in private tmpfs. Never pass passwords or fall back to writer credentials.
4. **Revocation:** Use an explicit operator-triggered server stop for an active user's role/account revocation; document request and completion times and verify container/cache destruction. No automatic controller or maximum-time SLA is selected.
5. **Secret-safe diagnostics:** Use bounded failure categories and sanitized lifecycle records in existing Hub/container logs; no new audit backend or retention SLA.
6. **Compatibility and network:** Preserve pinned services and keep FreeIPA reachable only over its approved internal LDAPS path with CA and hostname validation. Exact endpoint, CA mount, dependency version, and network attachment remain for Infrastructure Design and require approval if they alter architecture.

## Approval Gate

The user approved this NFR Design Plan and requested continuation. Review `construction/unit-4/nfr-design/nfr-design-patterns.md` and `logical-components.md` before Unit 4 Infrastructure Design. Approval authorizes design documentation only, not runtime changes, tests, provisioning, package installation, network changes, credential changes, or workspace operations.

## Design outcome

Fresh role validation is required both at login and before every spawn; saved auth state alone is insufficient. Per-user credential mapping and read-only mounts are enforced as a precondition to Docker create. Kerberos ticket state remains in private tmpfs and active revocation uses an explicit measured server-stop workflow. Exact LDAPS endpoint, CA mount, network attachment, crypt-key source, timeout values, registry format, and authenticator compatibility remain Infrastructure Design/Build and Test obligations. No new service, package, or runtime behavior is asserted as already implemented.
