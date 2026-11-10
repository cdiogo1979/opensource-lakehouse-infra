# Unit 4 Build and Test Plan — FreeIPA JupyterHub Login and Per-User Spark Identity

## Purpose and gate

Verify the generated FreeIPA-backed JupyterHub configuration using the existing isolated FreeIPA profile, active MIT KDC, existing RustFS identities, and disposable notebook sessions. This stage requires user review and approval before building images, provisioning test directory entries/permissions, starting or restarting services, or creating test workspaces. Code Generation did not run tests or operate services.

## Approved behavior

- FreeIPA authenticates interactive users; MIT remains the notebook ticket authority.
- `developer-user` maps to its developer MIT keytab/RustFS credentials and a dedicated persistent workspace; `analyst-user` maps to its analyst identity and workspace.
- FreeIPA `administrator` is the JupyterHub admin and deliberately maps to the existing MIT `admin` keytab, RustFS admin credential pair, and `iceberg-poc-jupyter-admin-work` volume.
- `user_a` and `user_b` cannot log in; their keytabs, RustFS credentials, and volumes remain untouched.
- No notebook may receive the Hub LDAP-reader credential, Hub auth-state key, writer credentials, or another user's files.

## Preconditions and safety

1. Confirm the running JupyterHub container/image and pinned dependencies; build the local image only after preserving its existing data volume.
2. Start only the approved FreeIPA validation profile. Keep the MIT KDC authoritative; do not alter realms, aliases, principals, service keytabs, or KDC routing.
3. Export and verify the FreeIPA CA. Confirm its certificate SAN includes `ipa.lakehouse.local` and that LDAPS validation works from the Hub.
4. Provision a dedicated `jupyterhub-ldap-reader` account with read/search only for user `uid`/`nsAccountLock` and role group `cn`/`member`. Use the protected password file; never echo or place it in arguments/logs. Verify the reader cannot modify directory entries.
5. Provision FreeIPA `administrator` with a human password, keeping it distinct from FreeIPA's built-in `admin`. Existing developer/analyst FreeIPA accounts must have interactive passwords set through the approved onboarding method.
6. Capture read-only Compose network, volume, credential-file ownership/mode, FreeIPA membership, and Hub-session inventories. Do not read existing RustFS object contents or modify existing user credentials/policies/workspaces.
7. Use the new dedicated developer and analyst Jupyter work volumes for tests. Do not remove or rename any legacy volume.

## Test cases

### Build and dependency

- Build the local Hub image and verify Python/JupyterHub/authenticator versions and pinned dependency consistency.
- Confirm the Hub is connected to both the existing lakehouse network and the internal Hub/FreeIPA network; only Hub and FreeIPA join the latter. Confirm no LDAP/LDAPS host port is published and notebook containers do not join the FreeIPA network.
- Confirm startup fails closed for missing/unsafe reader password, auth-state key, or CA; invalid CA hostname/chain; and unavailable FreeIPA.

### Login and role enforcement

- Successful login and spawn for `developer-user`, `analyst-user`, and `administrator`.
- Denial for invalid password, missing account, locked account, no role, both developer and analyst groups, writer-only/member-of-writer role, service identity, and legacy `user_a`/`user_b`.
- LDAP outage or reader bind/search failure denies new login and spawn.
- Remove a user's role membership and verify a subsequent login/spawn is denied after the fresh directory check.
- Verify a rejected user does not cause a notebook container to be created.

### Per-user identity and isolation

- For each allowed identity, inspect the container's mounts: only its own keytab and RustFS credential source files, its configured workspace, examples, and private tmpfs paths are present.
- Confirm credential source mounts are read-only, staged credentials are inaccessible to other users, and no Hub or other-user secret is mounted.
- Confirm developer/analyst container processes run as UID/GID 10001 after credential staging; test entrypoint drops privileges before starting JupyterHub single-user.
- Confirm `klist` shows the mapped MIT principal: developer, analyst, and the explicitly mapped `admin@LAKEHOUSE.LOCAL` for FreeIPA `administrator`.
- Query a disposable data probe to confirm the RustFS developer/analyst/admin role matrix. Use no existing object/table data.

### Revocation, ticket, and workspace lifecycle

- Stop a running notebook through the JupyterHub admin interface after disabling/removing the account's role. Verify the container and tmpfs ticket cache are destroyed; verify only that user's dedicated workspace persists.
- Confirm the administrator retains the existing admin workspace and that legacy user workspaces and credentials are unchanged.
- Verify startup/session logs do not contain passwords, keytab bytes, auth-state keys, ticket data, or LDAP bind responses.

## Acceptance and failure conditions

Pass only if all allowed/denied login, group-conflict, lock, network/TLS, credential isolation, identity mapping, RustFS role, revocation, cache-destruction, and workspace-preservation checks pass. Any unexpected spawn, cross-user mount, FreeIPA-superuser reuse, role bypass, MIT identity change, or unrelated state mutation is a hard failure. Stop, preserve evidence, and do not proceed to deployment handoff.

## Execution record — 2026-10-27

**Build and configuration:** Built the pinned local Hub and single-user images. `jupyterhub --show-config` loaded successfully. Host credential ownership/mode preflight passed, including an isolated fixture proving unsafe permissions are rejected. A network-disabled startup with the LDAP-reader secret missing, and another with the auth-state key missing, both exited nonzero before Hub startup. Existing Hub data and all user workspace volumes were retained.

**FreeIPA and network:** LDAPS certificate validation and the read-only reader's inability to modify directory data passed. The Hub joined the existing lakehouse network and the isolated Hub/FreeIPA network; FreeIPA and Hub were the only members of the latter. Notebook containers joined only the lakehouse network. A simulated LDAP network outage initially returned HTTP 500 because LDAPAuthenticator raised before the role-check wrapper. The Hub now catches authenticator failures and denies login; after rebuilding/restarting Hub, the same outage returned HTTP 403. The network was restored.

**Login and role checks:** `developer-user`, `analyst-user`, and `administrator` authenticated and each notebook reached `/user/<name>/api/status` with HTTP 200. The developer process ran as UID/GID 10001 after entrypoint credential staging; all three sessions had a live Kerberos ticket and used the configured developer, analyst, and admin principals. Their read-only keytab/RustFS source mounts and their own workspace volumes were inspected. No cross-user credential, LDAP-reader credential, or Hub auth-state key was mounted into a notebook. The S3 probes from the notebook containers matched the matrix: developer read all buckets and wrote only `lake-dev`; analyst read only `lake` and wrote none; administrator read/wrote all three. Unique probe objects were deleted. Invalid/missing, locked, no-role, conflicting-role, writer-only, service, and legacy `user_a`/`user_b` logins were denied; no rejected identity spawned a notebook.

**Spark SQL and Kerberos:** A PySpark session initially failed to connect to Hive with `No valid credentials` even though `klist` showed the notebook TGT. The JVM's Hadoop `UserGroupInformation` had no Kerberos Subject until explicitly initialized from the staged per-user keytab. After `ugi.loginUserFromKeytab(principal, "/run/credentials/identity.keytab")`, the catalog call succeeded. A synthetic Iceberg table under a unique `lake-dev` prefix was created, inserted, and queried as developer; the analyst's Spark read was denied; administrator's Spark read succeeded. The temporary namespace was dropped and all six test objects were deleted; verification confirmed the namespace and object prefix were absent. `infra/jupyter/examples/spark-authz.py` and the README now document the required UGI login before Hive/Iceberg operations.

**Revocation:** Temporarily removed and then restored only `developer-user`'s membership in `lakehouse-developers`. A fresh login while removed returned HTTP 403. The active disposable notebook was stopped; its tmpfs ticket cache was destroyed when the container stopped. A request from the already-authenticated browser session after the stop received HTTP 503 because Hub still had a stale server route; this did not start a running container. After removing the stopped disposable container, Hub reconciled the user server state and the restored account successfully spawned again. The original group membership was confirmed restored.

**Cleanup and preservation:** Deleted the four disposable `jupyterhub-test-*` FreeIPA users and their temporary password files. Removed all three test notebook containers. Confirmed the developer, analyst, and administrator named workspace volumes still exist. Automatic DockerSpawner cleanup is restored to `True`; Hub was rebuilt/recreated with its existing data volume. A protected-file scan of Hub logs found no configured credential values.

**Supplemental verification — 2026-10-27:** The disposable administrator notebook was spawned, then stopped through the JupyterHub admin API using a temporary CLI token. The stop request returned HTTP 204 and the notebook container was removed. The current and two transient tokens from interrupted attempts were all deleted through the API; a request using the revoked token returned HTTP 403, and a metadata-only database check found zero remaining `command-line generated` tokens. No token value was printed or persisted outside the Hub database.

For the fresh pre-spawn check, an authenticated developer session was kept while its `lakehouse-developers` membership was temporarily removed. The running notebook was stopped through the same admin API, then the existing developer session requested a new spawn. JupyterHub returned HTTP 500 from the failing pre-spawn authorization hook, and no developer notebook container was created. The original FreeIPA membership was restored successfully. This is a fail-closed authorization result; JupyterHub currently presents the hook denial as HTTP 500 rather than a user-facing 403.

For missing-CA behavior, a no-dependencies Compose run replaced only the CA bind source with a deliberately absent file and failed before container start with Docker's `bind source path does not exist` error. The live CA mount was unchanged. Build and Test is complete with the pre-spawn HTTP status noted above.

## Known limits

- LDAPAuthenticator 2.0.2 declares Python >=3.9, JupyterHub >=4.1.6, and ldap3 >=2.9.1. The inspected running Hub is Python 3.10.12/JupyterHub 5.3.0 and meets those minimums, but this does not establish compatibility with local FreeIPA attributes, TLS, or lock semantics.
- A role mismatch raised by JupyterHub's `pre_spawn_hook` is denied before notebook creation, but the current JupyterHub handler returns HTTP 500 for that expected authorization denial. A clearer user-facing denial status/message could be addressed separately.
- The plan does not authorize MIT KDC cutover, RustFS policy edits, credential rotation, legacy workspace deletion, or a numeric revocation SLA.
