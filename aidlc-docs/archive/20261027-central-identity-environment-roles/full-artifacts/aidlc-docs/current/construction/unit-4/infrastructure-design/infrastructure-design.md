# Unit 4 Infrastructure Design — FreeIPA JupyterHub Authentication and Per-User Spark Identity

## Scope and approved baseline

This design translates the approved Unit 4 Functional Design and NFR Design into deployment decisions for the existing Compose JupyterHub and isolated FreeIPA validation service. It is design-only. It changes no Compose files, images, credentials, directory entries, KDC settings, or workspaces.

FreeIPA supplies interactive authentication and group membership over LDAPS. The supported data roles are `lakehouse-developers` and `lakehouse-analysts`; writer/service identities are not interactive. Each notebook receives only its own read-only keytab and RustFS pair, with its Kerberos cache in tmpfs. The active MIT KDC stays authoritative until the separately approved Unit 6 cutover. Unit 3's residual Build and Test checks remain open.

Source review found JupyterHub 5.3.0 and DockerSpawner 14.0.0 in the Hub image, `DummyAuthenticator` in the current config, no LDAP authenticator package in the Hub requirements, a JupyterHub service on `iceberg_net`, and an opt-in FreeIPA server on `freeipa_validation_net`. The FreeIPA server currently exposes HTTPS only on loopback port 8443; no LDAP port is host-published. The existing FreeIPA CA is already exported for the identity reconciler at `.runtime/freeipa/ca.crt`. The FreeIPA role bootstrap provides `developer-user`, `analyst-user`, and `write-service-account` in data groups but does not provision a distinct interactive platform administrator.

## Approved infrastructure decisions

### 1. Network boundary

- Add a dedicated Compose network, `jupyterhub_ipa_net`, marked `internal: true` and shared only by JupyterHub and FreeIPA.
- Keep JupyterHub on `iceberg_net` for its current Hub/KDC/HMS/object-store and Docker-spawner needs. Do not attach Spark notebook containers to `jupyterhub_ipa_net`; only Hub queries FreeIPA.
- Keep FreeIPA on its current `freeipa_validation_net` for the isolated identity-reconciliation profile, and add it to `jupyterhub_ipa_net` as a second interface. Do not place `identity-reconciler` or ordinary lakehouse services on `jupyterhub_ipa_net`.
- Use the internal DNS alias `ipa.lakehouse.local` on the dedicated network and LDAPS port 636. Preserve the existing localhost-only HTTPS mapping; publish no LDAP/LDAPS host port.
- FreeIPA validation remains opt-in. JupyterHub may start without it, but login and spawn authorization fail closed while LDAPS is unreachable. The Hub must never fall back to `DummyAuthenticator`.

### 2. LDAPS trust and query identities

- Use the FreeIPA endpoint hostname that is present in the FreeIPA LDAP server certificate SAN. Confirm that the installed validation server certificate covers `ipa.lakehouse.local` before enabling the Hub connection.
- Mount `.runtime/freeipa/ca.crt` into JupyterHub at a fixed read-only path such as `/run/freeipa/ca.crt`. Require CA-chain and hostname validation; never use `tls_strategy="insecure"` or disable certificate checks.
- Configure the authenticator for LDAPS port 636 and the on-connect TLS mode appropriate to LDAPS. Set finite connect and operation timeouts. Authentication failure, malformed responses, and timeouts deny access.
- Use the user's direct LDAP bind for password authentication. For lookup and fresh spawn-time role checks, provision a separate, least-privileged `jupyterhub-ldap-reader` directory account and a protected Compose secret file. Grant it only read/search access to the exact role group `cn`/`member` attributes and user `uid`/`nsAccountLock` attributes required by the check. It is not a data role, Kerberos service, or interactive user. Do not reuse the RustFS reconciler bind credential.
- The reader secret is mounted only in the Hub. Hub logs and config never print it. Directory permissions and the actual account's read-only behavior are Build and Test acceptance checks.

### 3. Authenticator and role check

- Replace `DummyAuthenticator` with the pinned `jupyterhub-ldapauthenticator` candidate only after checking a concrete release and its transitive dependencies against Hub 5.3.0 and the Hub Python runtime. The current official project documents full-DN `allowed_groups`, LDAPS/TLS settings, and group membership through group `member` values. Its compatibility notes describe OpenLDAP testing; FreeIPA behavior remains an explicit validation obligation.
- Use exact group DNs based on the configured FreeIPA suffix, currently expected to be `dc=lakehouse,dc=local`:
  - `cn=lakehouse-developers,cn=groups,cn=accounts,dc=lakehouse,dc=local`
  - `cn=lakehouse-analysts,cn=groups,cn=accounts,dc=lakehouse,dc=local`
- Use an explicit username allow rule for the separately mapped platform administrator only after the identity decision in `functional-design-clarification.md` is resolved. Set `allow_all = false`; do not enable user auto-creation as an authorization grant.
- Add a Hub-side directory adapter used after successful password bind and again from the DockerSpawner pre-spawn hook. It queries the read-only reader identity for exact current group membership and account lock state. It permits exactly one data role or the separately authorized platform administrator; both/neither/conflicting/writer membership denies before Docker create.
- Do not use cached `auth_state` as the spawn authorization decision. It may carry minimal canonical identity/group context only. Do not place passwords in auth state.
- Confirm that FreeIPA's group `member` attribute and `nsAccountLock` behavior match the query contract in Build and Test. If not, revise the query filter and verify the corrected ACI before implementation is considered complete.

### 4. JupyterHub auth-state key

- Enable persistent auth state only for the minimum identity/group fields needed by Hub.
- Store a stable 32-byte JupyterHub crypt key in a protected file under `.runtime/credentials/`, expose it to the Hub via a Compose secret, and have the Hub startup wrapper read it into `JUPYTERHUB_CRYPT_KEY` immediately before executing JupyterHub. Do not put the literal key in Compose YAML, `.env`, command arguments, or logs.
- Treat this key as persistent Hub state: back it up only under the existing protected credential backup process. Rotating it requires a planned auth-state re-encryption/logout operation; it must not silently invalidate persistent account/workspace mappings.

### 5. Identity registry and credential mounts

- Replace the old `user_a`/`user_b` spawn map with a provisioning-owned explicit registry. Each entry identifies the canonical Hub username, FreeIPA login mapping, expected active-MIT Kerberos principal, data role, exact keytab filename, RustFS access/secret filenames, and distinct workspace volume.
- Keep the registry as non-secret configuration mounted read-only to the Hub; keep actual keytab and S3 values in the existing protected `.runtime/credentials` files and Compose secrets/bind mounts. Store only filenames/references in the registry, never values.
- Validate usernames against an allowlist and resolve file paths under the configured credentials root. Reject symlinks, path traversal, missing files, unexpected ownership/mode, role mismatch, and principal mismatch before creating a notebook.
- Mount only that user's keytab and RustFS pair read-only into their notebook. Do not expose the FreeIPA reader secret, Hub crypt key, writer credentials, HMS credentials, RustFS admin credentials, or another user's files to notebook containers.
- Reuse the current read-only per-user runtime path and ticket-cache tmpfs behavior in `start-session.sh`; verify `klist` reports the registry's expected principal before Jupyter starts.
- Keep named workspaces: existing `iceberg-poc-jupyter-admin-work` stays assigned to the existing admin mapping; add unique developer/analyst volumes. Keep `user_a` and `user_b` volumes and credentials unchanged and unattached after their eventual cutover until separate retention approval. Never migrate or delete workspace data in this unit.

### 6. Separate platform-administrator identity decision

FreeIPA reserves the `admin` username for its directory administrator. Using that credential for JupyterHub would expand the exposure of a directory-superuser password and conflicts with the infrastructure plan's least-privilege direction. A second FreeIPA user cannot simply be provisioned with the same username. Therefore the approved role mapping is incomplete until the user selects a distinct, nonprivileged FreeIPA human login and the corresponding MIT Kerberos/RustFS principal mapping. A safe implementation must not use FreeIPA's built-in administrator as the interactive Hub account by default.

The future mapping must preserve Hub administrator permission and the existing admin workspace without silently mapping a different human's credentials to the `admin` Kerberos/S3 identity. Record the account name, group/allowlist rule, principal/keytab, RustFS identity, and workspace mapping together before implementation. See `functional-design-clarification.md`.

### 7. Failure, revocation, and evidence

- LDAP bind/search, pre-spawn lookup, Docker create/start, and notebook startup calls use finite timeouts. No auth retry occurs under another principal or stale membership. Exact values are set in runtime implementation after a bounded local test.
- FreeIPA outage, invalid CA, locked user, absent/conflicting role, reader-secret failure, incomplete registry entry, or identity mismatch denies before spawn. No local password or `DummyAuthenticator` fallback is allowed.
- An operator revocation operation removes/disables the FreeIPA membership/account and stops the user's server through Hub/DockerSpawner. Record request/completion times and confirm container termination destroys the tmpfs TGT. No numeric SLA or new controller is selected.
- Use existing Hub/container logs with safe principal, role, event, result, and bounded reason. Exclude passwords, secret/keytab/ticket values, raw LDAP responses, and notebook data.
- Preserve the current `jupyterhub-data` volume and record sanitized user-to-workspace mappings before and after rollout.

## Deployment sequence when implementation is separately authorized

1. Resolve the separate platform-admin identity mapping.
2. Confirm the FreeIPA certificate SAN, exported CA, role-group DNs, locked-user attribute, and read-only lookup permissions on isolated FreeIPA.
3. Select/pin a compatible LDAPAuthenticator and its dependencies; build and inspect the Hub image without changing runtime services.
4. Stage the internal Hub/FreeIPA network, CA, and dedicated reader secret in Compose. Keep the LDAP port unpublished and preserve the existing host-only FreeIPA Web UI.
5. Configure login authentication, fresh pre-spawn revalidation, explicit user registry, and per-user credential mounts. Keep MIT as the KDC.
6. Verify each user, failure, denial, revocation, `klist`, RustFS access, and workspace behavior with isolated identities and disposable data.
7. Only after the separate Unit 3 gate is closed or explicitly waived and the Unit 4 Build and Test plan is approved may integrated rollout be considered.

## Compatibility evidence and references

The official LDAPAuthenticator documentation describes full-DN group allow rules based on group `member` values, LDAPS/TLS settings, and username validation; it also notes that verification against LDAP products other than OpenLDAP is welcome. Its 2.0 changelog requires JupyterHub 4.1.6 or newer, which makes the installed Hub 5.3.0 a plausible candidate but is not proof of the selected package release or FreeIPA compatibility. JupyterHub auth-state documentation requires `enable_auth_state` and `JUPYTERHUB_CRYPT_KEY` for encrypted persistence.

- [LDAPAuthenticator documentation and configuration](https://github.com/jupyterhub/ldapauthenticator)
- [LDAPAuthenticator changelog](https://github.com/jupyterhub/ldapauthenticator/blob/main/CHANGELOG.md)
- [JupyterHub authenticator and auth-state documentation](https://jupyterhub.readthedocs.io/en/stable/reference/authenticators.html)
- [FreeIPA LDAP documentation](https://www.freeipa.org/page/HowTo/LDAP.html)

These sources establish configuration capabilities only; the pinned release, FreeIPA schema, TLS identity, group query behavior, and pre-spawn refresh must be verified locally.
