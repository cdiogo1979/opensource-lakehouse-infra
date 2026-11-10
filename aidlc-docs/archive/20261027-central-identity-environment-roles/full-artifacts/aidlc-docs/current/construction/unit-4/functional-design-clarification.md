# Unit 4 Functional Design — Clarifications and Verification Items

The approved functional design makes the decisions below where requirements and current source are sufficient. The remaining items require concrete validation or configuration selection during later design/Build and Test; they do not authorize runtime changes now.

## Decisions recorded

1. FreeIPA is the JupyterHub login directory. Until Unit 6 cutover, the active MIT KDC remains the sole Kerberos ticket authority for the current HMS/Spark services. A FreeIPA login is not treated as a Kerberos ticket.
2. The interactive data roles are exactly `lakehouse-developers` and `lakehouse-analysts`. `lakehouse-writers` and `write-service-account` are excluded from JupyterHub.
3. The platform `admin` identity remains separately allowlisted and retains its existing Hub administrator mapping and workspace. Admin status does not derive from either data group.
4. Multiple/conflicting data-role memberships, missing membership, disabled users, unresolved LDAP state, missing identity-registry entries, and missing per-user keytab/S3 files deny login or spawn.
5. Each notebook receives only its own read-only keytab and RustFS credentials. The ticket cache is per-container tmpfs; workspaces remain persistent and contain no credential or ticket-cache state.
6. Active group removal blocks subsequent login/spawn after fresh directory validation. An explicit revocation action must stop an already-running server and prove ticket-cache destruction; an LDAP edit alone is not considered completed revocation.
7. The current RustFS reconciler and credential inventory cover named users. A new FreeIPA group member is not automatically notebook-ready: role membership must be accompanied by a matching RustFS identity, keytab, credential registry entry, and verification.

## Deferred validation and design inputs

| Item | Required evidence or decision | Gate |
|---|---|---|
| FreeIPA LDAPS endpoint | Stable internal DNS name, reachable from Hub on the intended internal network, matching certificate SAN, and trusted read-only CA bundle. Do not use a browser localhost redirect or disable verification. | Unit 4 Infrastructure Design / Build and Test |
| LDAPAuthenticator compatibility | Confirm pinned authenticator supports the FreeIPA user/group schema and exact role-group lookup. Verify valid login, invalid password, disabled/locked user, absent membership, conflicting membership, and LDAP timeout against the isolated instance. | Unit 4 Build and Test |
| Auth-state protection | Select a protected stable JupyterHub crypt key and ensure stored auth state contains only required identity/group attributes, never submitted passwords. | Unit 4 NFR/Infrastructure Design |
| Admin account | Confirm a corresponding `admin` human account exists in FreeIPA and its keytab/RustFS mapping is deliberately provisioned; do not make a service account or either data group a Hub admin. | Unit 4 Infrastructure Design / Build and Test |
| Identity registry/onboarding | Choose a provisioning-owned data format and ensure an added role member cannot spawn until exact per-user credentials, role, and workspace mapping are present. Future group members must not gain filesystem path control. | Unit 4 Infrastructure/Code Generation |
| Revocation trigger and bound | Select an operator or directory-event workflow to stop active notebook containers, then measure request-to-stop and verify cache destruction. Define an operational completion target before acceptance. | Unit 4 NFR Design / Build and Test |
| Unit 3 residual checks | Close or explicitly waive the separately listed Unit 3 gaps before Unit 4 runtime implementation and integrated Build and Test. | Unit 3 gate |

## Sources inspected

- Current `infra/jupyter/hub/jupyterhub_config.py`, `infra/jupyter/singleuser/start-session.sh`, FreeIPA bootstrap scripts, `docker-compose.yml`, Unit 1 identity rules, Unit 3 functional rules, and approved requirements.
- JupyterHub [LDAPAuthenticator](https://github.com/jupyterhub/ldapauthenticator), [authenticator documentation](https://jupyterhub.readthedocs.io/en/stable/reference/authenticators.html), [DockerSpawner API](https://jupyterhub-dockerspawner.readthedocs.io/en/latest/api/index.html), FreeIPA [LDAP documentation](https://www.freeipa.org/page/HowTo/LDAP.html), and MIT Kerberos [`kinit` documentation](https://web.mit.edu/kerberos/krb5-latest/doc/user/user_commands/kinit.html).
