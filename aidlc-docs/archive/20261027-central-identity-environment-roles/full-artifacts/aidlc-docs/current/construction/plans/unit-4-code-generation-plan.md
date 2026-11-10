# Unit 4 Code Generation Plan — FreeIPA JupyterHub Authentication and Per-User Spark Identity

## Unit Context

- **Unit:** Unit 4 — FreeIPA-backed JupyterHub authentication and per-user Spark identity.
- **Stories:** Unit 4 identity, role enforcement, isolated notebook credential delivery, revocation, and workspace preservation stories in `inception/application-design/unit-of-work.md`.
- **Dependencies:** Approved Unit 4 functional, NFR requirements, NFR design, and infrastructure design artifacts; existing JupyterHub/DockerSpawner and FreeIPA validation configuration.
- **Implementation boundary:** Existing JupyterHub Hub image/configuration, authenticator, Hub-side directory lookup, provisioning-owned identity registry, DockerSpawner configuration, notebook startup, and related operator documentation only.
- **Authority boundary:** MIT KDC remains the only KDC through Unit 6. No FreeIPA Kerberos cutover, realm routing, service keytab change, or KDC alias change.

This plan was approved by the user on 2026-10-27. Its Unit 3 verification and platform administrator mapping gates have been resolved. Code Generation is complete within the listed file scope. It does not run tests or operate services; verification belongs to the separately approved Build and Test plan.

## Hard Gates Before Code Generation

1. **Unit 3 verification gate — satisfied:** Unit 3 Build and Test was completed on 2026-10-27 with documented limits in `construction/plans/unit-3-build-and-test-plan.md`. Its recorded outcome permits progression; it does not claim Hive metadata-DDL authorization, FreeIPA membership revocation timing, Hive catalog-cache behavior, or Airflow/JupyterHub integration.
2. **Platform administrator identity gate — mapping approved:** The user selected `administrator` and explicitly approved mapping it to JupyterHub admin permission, existing MIT `admin@LAKEHOUSE.LOCAL` keytab, RustFS admin credentials, and preserved `iceberg-poc-jupyter-admin-work` volume. FreeIPA account provisioning remains separate. Never use FreeIPA's directory-superuser credential.
3. **Compatibility gate — package minimums met; FreeIPA gate deferred to Build and Test:** Read-only inspection of the running Hub reports Python 3.10.12 and JupyterHub 5.3.0. LDAPAuthenticator 2.0.2 requires Python >=3.9, JupyterHub >=4.1.6, and ldap3 >=2.9.1; pinned dependencies are recorded in `infra/jupyter/hub/requirements.txt`. Actual FreeIPA schema/TLS/group/account-lock behavior remains unverified and is a hard Unit 4 Build and Test gate. Upstream states testing against OpenLDAP, not proof of FreeIPA compatibility. [PyPI release metadata](https://pypi.org/project/jupyterhub-ldapauthenticator/2.0.2/) · [upstream changelog](https://github.com/jupyterhub/ldapauthenticator/blob/main/CHANGELOG.md).

## Approved Contracts

- Authenticate human users with FreeIPA over certificate- and hostname-validated LDAPS. FreeIPA validation remains profile-gated; any login or spawn authorization check fails closed if directory access is unavailable. Never fall back to `DummyAuthenticator`.
- Allow only the exact `lakehouse-developers` or `lakehouse-analysts` role group for data users; reject neither/both/conflicting roles, locked accounts, writer/service membership, and incomplete mappings. Re-query current authorization before each notebook spawn.
- Keep the active MIT KDC as the notebook ticket authority. Each notebook receives only its own read-only keytab and RustFS credential pair, and a private tmpfs ticket cache.
- Maintain a strict provisioning-owned identity registry. Usernames do not construct filesystem paths. Validate the expected role, MIT principal, credential-file ownership/modes, and workspace mapping before Docker create.
- Preserve `jupyterhub-data`, the existing admin workspace once mapping is resolved, and legacy `user_a`/`user_b` credentials and workspaces. Do not transfer, delete, or reassign their data.
- Hub-only LDAP reader password and JupyterHub auth-state crypt key are protected secret files. Neither is exposed to notebook containers or logged. Submitted passwords are never stored.
- Do not change RustFS policies, FreeIPA authority, MIT principals/keytabs, service versions beyond the approved Hub dependency/image work, production data, or unrelated Compose services.

## Sequential Generation Steps

### Step 1 — Confirm gates and implementation baseline

- [x] Record user resolution of the Unit 3 verification gate and the distinct platform-admin identity mapping.
- [x] Capture the running Hub Python/JupyterHub versions, DockerSpawner settings, authenticator configuration, and current username/volume/credential mappings.
- [x] Identify LDAPAuthenticator 2.0.2 and pin its direct dependency set; its published minimum versions are met by the inspected Hub runtime.
- [ ] Confirm the FreeIPA certificate SAN, exported CA path, exact group DNs, user lock attribute, and proposed reader search permissions from the approved design; unresolved facts remain Build and Test gates.

### Step 2 — Implement Hub-to-FreeIPA LDAPS boundary

- [x] Add `jupyterhub_ipa_net` as an internal Compose network shared only by JupyterHub and FreeIPA validation; retain existing Hub and FreeIPA network attachments.
- [x] Keep LDAP/LDAPS unpublished on the host and retain the existing loopback-only FreeIPA Web UI mapping.
- [x] Mount the CA and dedicated `jupyterhub-ldap-reader` password read-only into the Hub only; do not reuse the RustFS reconciler identity.
- [x] Configure LDAPS hostname/chain verification and finite connection/search timeouts; missing CA, reader secret, DNS, or service must fail closed.

### Step 3 — Implement authentication and current role authorization

- [x] Replace `DummyAuthenticator` with the reviewed and pinned group-aware LDAP authenticator candidate; disable open user creation and unrestricted `allow_all` access.
- [x] Implement Hub-side directory checks for account status and exact role group membership at login and again in DockerSpawner pre-spawn.
- [x] Apply the resolved distinct platform-admin allowlist/group mapping without using FreeIPA's built-in `admin` credential.
- [x] Reject role conflicts, missing roles, locked accounts, writer/service identities, stale/failed lookups, and unmapped users before notebook container creation.
- [x] Keep passwords out of logs and persistent auth state. If minimal auth state is required, enable Hub encryption with the protected stable crypt-key secret.
- [x] Document the required JupyterHub cookie-secret rotation/logout procedure for authenticator cutover; no active session was invalidated during Code Generation.

### Step 4 — Implement explicit per-user identity and workspace mapping

- [x] Add a non-secret, read-only provisioning-owned identity registry with canonical username, FreeIPA login, role, expected MIT principal, credential filenames, and exact named workspace.
- [x] Resolve all credential references under the approved credentials directory; reject traversal, symlinks, missing files, incorrect permissions/ownership, role mismatch, or principal mismatch.
- [x] Configure DockerSpawner to mount only the selected user's keytab and RustFS pair read-only, their unique persistent workspace, and a private tmpfs ticket cache.
- [x] Ensure no Hub secret, LDAP bind secret, auth-state key, writer/admin service credential, or other user's credential is mounted into a notebook.
- [x] Keep notebook ticket acquisition pointed at the existing MIT KDC and preserve current safe `kinit`/`klist` startup behavior.

### Step 5 — Add lifecycle handling and safe diagnostics

- [x] Provide an operator procedure to remove/disable directory access and stop an active user's Hub server; no new controller or numeric revocation SLA.
- [ ] Confirm container termination destroys the tmpfs ticket cache while preserving its named workspace.
- [ ] Log only bounded event/result/reason, canonical principal, and role; exclude passwords, secret values, keytabs, ticket contents, raw LDAP responses, and notebook data.
- [x] Keep startup/profile instructions explicit and never select the previous dummy/local authenticator as an outage fallback.

### Step 6 — Review scope and prepare Build and Test handoff

- [x] Review generated code/configuration and documentation against Unit 4 approved artifacts; no test, build, account provisioning, service operation, or deployment was performed.
- [x] Document changed paths, dependency/version evidence, network and secret flows, admin mapping, role checks, workspace mapping, rollback, and compatibility limits in the generated configuration, README, and Build and Test Plan.
- [x] Update this plan and lifecycle records; do not add or run tests during Code Generation.
- [x] Prepare a separate Build and Test Plan for allowed/denied login, exact roles, role conflicts, account lock, FreeIPA outage, TLS failure, reader permissions, pre-spawn revocation, credential isolation, `klist` identity, RustFS access, tmpfs cleanup, and workspace preservation.
- [ ] If a mapping or security boundary cannot be implemented as specified, stop and request a design decision rather than adding fallback access.

## Build and Test Gates

The separately reviewed Build and Test stage must establish:

1. Only Hub and FreeIPA share the new internal LDAPS network; no LDAP host port is published and notebooks cannot reach the network.
2. The selected authenticator is pinned and works with the installed Hub/Python versions and FreeIPA TLS, group membership, and lock attributes.
3. Developer and analyst roles authenticate and spawn only with their exact approved role; neither/both/writer/locked/unmapped users fail closed.
4. Current membership is re-checked at spawn; FreeIPA outage, bad CA, reader failure, and stale auth state cannot create a server.
5. Each notebook sees only its mapped read-only keytab and RustFS pair, gets the expected MIT principal, and enforces the RustFS role matrix without writer fallback.
6. Revocation stops the active server and destroys tmpfs ticket state while retaining the correct workspace; admin and legacy workspaces/data remain unchanged.
7. Compose/network, mount, volume, and credential inventories before/after show no unauthorized or unrelated changes; logs contain no secret material.

Any cross-user credential exposure, unexpected spawn, role bypass, FreeIPA-superuser reuse, workspace reassignment, or MIT KDC change is a hard failure. Stop rollout and preserve state for review.

## Scope Exclusions

- No FreeIPA KDC/realm cutover, MIT KDC change, service principal/keytab rotation, or identity migration.
- No RustFS policy changes, bucket/database/object changes, StarRocks/Ranger changes, or broader IAM redesign.
- No production workspace/data deletion, migration, reassignment, or automatic `user_a`/`user_b` conversion.
- No LDAP host-port publication, notebook access to the Hub/FreeIPA internal network, or fallback authenticator.
- No tests or live service operations during Code Generation.

## Approval Gate

The user approved this Code Generation Plan and the later administrator mapping, legacy-login, and authenticator recommendations on 2026-10-27. The local Hub Python/JupyterHub versions meet the package's published minimums; local FreeIPA behavior remains unverified. Code Generation is complete. The separate Unit 4 Build and Test Plan is ready for review and requires explicit approval before building images, provisioning directory identities/permissions, starting or restarting services, creating workspaces, or executing its tests. No approval here authorizes those actions or any MIT KDC cutover.
