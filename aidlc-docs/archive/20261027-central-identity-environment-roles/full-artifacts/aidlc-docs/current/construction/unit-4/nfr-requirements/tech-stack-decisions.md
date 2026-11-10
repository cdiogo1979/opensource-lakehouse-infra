# Unit 4 NFR Requirements — Technology Decisions

## Decisions

| Area | Decision | Rationale and constraint |
|---|---|---|
| Interactive identity source | FreeIPA over LDAPS, as required by the approved Functional Design | Require certificate-chain and hostname verification. Select the internal endpoint, CA mount, and network path during Infrastructure Design. |
| Authenticator implementation | LDAPAuthenticator is the documented candidate for group-aware JupyterHub login | Confirm the pinned Hub API and FreeIPA schema compatibility before selecting/pinning a package version. The current Hub config uses `DummyAuthenticator`; no package or runtime change is made by this decision record. |
| Authorization state | Exact FreeIPA group DNs plus an explicit separate `admin` mapping; reject missing/conflicting roles and writer identities | A stable protected Hub crypt key is required if group state is persisted. Never retain the submitted password in auth state. |
| Notebook lifecycle | Existing DockerSpawner model with one notebook container per user and one named workspace per canonical username | Preserve current workspace mappings; do not add a controller or automatically transfer/delete workspaces in this unit. |
| Kerberos ticket | User-specific keytab and `kinit` into private container tmpfs; MIT remains sole active KDC until Unit 6 | FreeIPA login is not ticket issuance. No service keytab, password forwarding, or writer fallback is allowed. |
| RustFS access | Per-user access/secret pair mounted read-only into that user's notebook | RustFS remains the object authorization authority. Missing or unprovisioned pair denies spawn/query. Never mount writer/admin material into human sessions. |
| Credential registry | Provisioning-owned explicit mapping from canonical username to role, credential files, expected principal, and workspace | Concrete format and future-member onboarding remain for Infrastructure/Code Generation Design; arbitrary path construction from LDAP username is prohibited. |
| Audit | Existing Hub/container logs with sanitized identity/decision/lifecycle fields | No new audit service, retention SLA, or immutable event platform is approved. Never log credential contents or submitted passwords. |
| Availability | Single-host best effort, finite dependency timeouts/retries, fail closed, operator-led recovery | No HA service or RTO/RPO commitment is selected. |
| Version policy | Retain currently pinned component versions | Any required authenticator package update, image rebuild, network attachment, secret mechanism, or session controller needs compatibility evidence and explicit architecture approval. |

## Explicitly not selected

- No production FreeIPA/KDC cutover; Unit 6 owns coordinated authority migration.
- No shared role keytab or shared human RustFS credential.
- No automatic active-server termination from LDAP group changes without an explicit revocation workflow.
- No new audit platform, high-availability deployment, workspace backup service, or numeric performance/revocation SLA.
- No tests, service operations, Compose/image changes, package installation, credential provisioning, or workspace operations in this NFR Requirements stage.

## Compatibility evidence required later

1. Confirm the selected LDAPAuthenticator version supports the current Hub release and FreeIPA's user/group schema, TLS trust, and group lookup behavior.
2. Confirm the crypt-key setup keeps auth state encrypted and excludes password fields.
3. Confirm DockerSpawner behavior preserves existing named workspaces while removing stopped containers and their tmpfs ticket caches.
4. Confirm the internal LDAPS route and CA trust can be added without exposing FreeIPA or changing the active KDC path.
5. Confirm the notebook entrypoint checks the acquired Kerberos principal and fails before Jupyter starts if it does not match the authenticated identity.

These are later design and verification obligations; no compatibility result is implied here.
