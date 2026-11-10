# Unit 4 Functional Design — Business Rules

## Authentication and role rules

| ID | Rule |
|---|---|
| U4-R1 | JupyterHub authenticates human users against FreeIPA over LDAPS with certificate validation enabled. A failed bind, user lookup, group lookup, TLS check, or directory timeout denies login. |
| U4-R2 | `developer-user` is admitted only as a member of `lakehouse-developers`; `analyst-user` is admitted only as a member of `lakehouse-analysts`. Role comes from FreeIPA group membership, never from a submitted username, notebook setting, or user-controlled environment value. |
| U4-R3 | `write-service-account` and members of `lakehouse-writers` are not interactive JupyterHub users. |
| U4-R4 | The platform `admin` login is explicitly allowlisted and configured as a JupyterHub administrator. It authenticates against FreeIPA but receives no data role by virtue of being a Hub administrator. Its existing admin workspace and credential mapping are preserved. The admin identity must not be inferred from either data-role group. |
| U4-R5 | A user in both developer and analyst groups, in neither group, or in an unrecognized group combination is denied before a server starts. There is no default role. |
| U4-R6 | LDAP authentication does not create a Kerberos ticket. Each notebook starts only after the server-side session bootstrap obtains a ticket for the same canonical username using that user's own keytab. A ticket for another user or the writer service is never a fallback. |
| U4-R7 | Until Unit 6 cutover, FreeIPA is the login directory while the active MIT KDC remains the sole Kerberos authority for the running HMS/Spark environment. The authenticated FreeIPA username must match the MIT principal name and approved per-user keytab. This is a transitional split of directory authentication and ticket issuance, not two co-authoritative KDCs. A failed or missing mapping denies spawn. |
| U4-R8 | After the separately approved Unit 6 cutover, each user's keytab must be reissued under the now-authoritative FreeIPA KDC and the notebook Kerberos realm/configuration updated as part of the coordinated migration. Do not mix a new FreeIPA keytab with the active MIT KDC or change the KDC alias in Unit 4. |

## Identity and credential rules

| ID | Rule |
|---|---|
| U4-R9 | The Hub resolves a canonical username through a provisioning-owned explicit identity registry. The registry maps each admitted identity to one workspace, one keytab, and one RustFS access/secret pair. It does not construct host paths from arbitrary LDAP usernames. |
| U4-R10 | Before spawn, the Hub verifies that every mapped credential file exists, is a regular readable file, and belongs to the expected identity entry. Missing, duplicate, malformed, or incomplete mappings fail closed. |
| U4-R11 | A notebook receives only its own keytab and RustFS credentials as read-only mounts. The ticket cache is created inside a per-container memory-backed `/run/krb5` filesystem with restrictive ownership and mode. It is never persisted in the workspace volume. |
| U4-R12 | The notebook environment contains credential file locations and non-secret configuration only. Passwords, LDAP bind secrets, RustFS keys, keytab bytes, and ticket contents are not placed in ordinary environment values, logs, notebooks, bundles, or generated documentation. |
| U4-R13 | The broad `write-service-account`, HMS, RustFS administrator, and other-user credentials are never mounted into human notebook containers. The writer remains ETL-only. |
| U4-R14 | FreeIPA group membership is the role source, but it does not itself provision RustFS identities or per-user credentials. A new group member is denied notebook spawn until the approved provisioning workflow has created that user's matching RustFS identity, keytab, and registry entry and those assets have been verified. |

## Spawn, workspace, and revocation rules

| ID | Rule |
|---|---|
| U4-R15 | Each admitted username maps to a distinct named persistent workspace. Normal stop/restart preserves that workspace. A username rename does not implicitly transfer or delete data. |
| U4-R16 | Existing `admin` workspace and privilege mapping are retained. Legacy `user_a` and `user_b` workspaces and credentials remain untouched during design and migration until their separately approved cutover and retention decisions. Replacement users do not inherit legacy workspaces automatically. |
| U4-R17 | Login and every server spawn require a fresh successful directory/group authorization decision. Cached Hub authentication or saved auth state alone cannot authorize a new spawn. |
| U4-R18 | Removing a user from an allowed group or disabling the account prevents the next login and spawn. Revocation of an already-running server requires the revocation workflow to stop that server and destroy its in-memory ticket cache; role changes do not magically terminate an existing container. The acceptance test must measure and record revocation completion. |
| U4-R19 | If directory, credential registry, KDC, or required credential files are unavailable, fail closed. Existing running workloads may fail when their ticket expires; they must not silently switch identity. |
| U4-R20 | User-facing failures disclose only that authentication, authorization, or server startup failed. Detailed directory topology and all credential material remain in secret-safe operator diagnostics. |

## Acceptance rules

Use the Unit 4 Build and Test plan to verify valid and invalid FreeIPA login, both role groups, role conflict, writer exclusion, explicit admin handling, per-user mounts, absence of other identities' credentials, `klist` principal, successful/denied RustFS data access from notebook Spark, ticket isolation, revocation/stop behavior, and workspace persistence. Use disposable data only. Unit 3 residual verification gaps remain separately visible and are not closed by Unit 4 design.
