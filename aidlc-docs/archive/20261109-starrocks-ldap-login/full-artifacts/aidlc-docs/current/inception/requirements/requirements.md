# Requirements — StarRocks LDAP Login

## Intent Analysis
- **User request**: "the goal is just to enable users (including service users) being able to login starrocks with their credentials". It follows an evaluation of FreeIPA as LDAP behind Keycloak, which was not recommended, in favour of a lightweight LDAP directory.
- **Type**: change in an existing component (StarRocks login) plus a new supporting service (an LDAP directory). It also changes where users and passwords are stored.
- **Scope**: Keycloak user storage, StarRocks authentication and its user sync, the StarRocks clients and documentation, user migration, the reset, and tests. Unchanged:
  - groups and every OIDC service (Polaris, RustFS, JupyterHub, Airflow, Jenkins)
  - the data product scripts
- **Depth**: standard. The design must also settle how to force TLS for password logins.
- **Answers**: Q1 A, Q2 A, Q3 A, Q4 A, Q5 B, Q6 B (partial), Q7 B; C1 A, C2 A.

## Probe facts (reverse engineering, 2026-11-09)
- A StarRocks 4.1.7 user created `IDENTIFIED WITH authentication_ldap_simple` logs in with the LDAP password and keeps its granted roles.
- One StarRocks user has exactly one login method.
- StarRocks accepted the plain-text password without TLS.

## Functional Requirements

### FR-1 LDAP directory (Q4 A)
- A new core service `ldap`, built from pinned Alpine OpenLDAP packages, in `compose.core.yml`, with its data in a named volume.
- One tree: base `dc=lakehouse,dc=local`, people in `ou=people`, keyed by `uid` = username.
- **TLS only**: LDAPS with a certificate from a local CA, prepared like the other local certificates.
- **No published host port**: reached only by Keycloak and StarRocks on the internal networks.
- **Credentials**: an administrator and a dedicated Keycloak bind identity, with write access to `ou=people` only. Their passwords live in `.runtime/credentials/`.
- **Lifecycle**: started by `lakehouse.sh start`, deleted by the reset, documented for backup.

### FR-2 Keycloak user federation (Q2 A)
- The `lakehouse` realm reads and writes users in LDAP (writable LDAP federation), configured idempotently by `infra/keycloak/bootstrap-realm.py`.
- **Writable**: new users created through Keycloak, and password changes or resets through Keycloak (admin API, account console), are written to LDAP.
- **Mapped attributes**: username, first and last name, and email.
- **Groups stay in Keycloak** (no group mapping from LDAP).
- **Local users**: service-account users of Keycloak clients (for example `service-account-srv-starrocks`) and the `master` realm stay local.
- **No changes needed** to `create-user.sh`, the product writer-user creation, `bootstrap-users.sh`, or the realm bootstrap's user creation. The design confirms this.

### FR-3 StarRocks password login (Q1 A)
- The FE checks passwords against LDAP by direct bind as `uid=<user>,ou=people,dc=lakehouse,dc=local`.
- **Persistent settings**: in `fe.conf` or the FE entrypoint, not only runtime settings, which do not survive a restart.
- **TLS to LDAP**: LDAPS, with the local CA in the FE trust store.
- **TLS for clients**: password logins must use TLS. The design determines the StarRocks mechanism, or documents a fallback if 4.1.7 has none.
- **User sync**: `reconcile-starrocks-users.py` creates every desired user `IDENTIFIED WITH authentication_ldap_simple`, and switches existing JWT users in place (`ALTER USER`), keeping their grants and materialized views.
- **Unchanged**: who gets a StarRocks user (members of product groups) and their roles.
- **Root** stays a native-password user.

### FR-4 Clients and documentation (C2 A)
- `scripts/clients/starrocks-login.sh` logs in with the username and password: cleartext authentication over verified TLS, the password from a prompt or file, never an argument.
- `scripts/clients/starrocks-token.sh` and the Keycloak `starrocks` client (with its audience mapper) are removed.
- **README**: DBeaver, JDBC, BI tools, and the mysql CLI with username and password over TLS. The token-file instructions are removed.

### FR-5 Migration of existing users (Q3 A, C1 A)
A one-time, idempotent, dry-runnable migration:
1. **Inventory**: list the realm's local (non-service-account) users.
2. **Recreate in LDAP** with their known password:
   - bootstrap users from `bootstrap-users.json`
   - writer users from their `.runtime/credentials` password files
   - any other user from the default `ChangeM3!` (reported by name)
3. **Replace the Keycloak copy**: delete the local Keycloak user and keep their group memberships by re-adding them to the federated user. The local copy is deleted only after the LDAP entry is verified.
4. **JupyterHub homes**: copy each migrated user's home volume to the volume named for their new Keycloak ID, keeping the old volume.
5. **Sync**: run the Polaris and StarRocks syncs.

### FR-6 Fresh installs
On a new or reset stack, every user is created in LDAP from the start through Keycloak, and no migration is needed. The product bootstrap's order makes LDAP and the federation available before any user is created.

### FR-7 Tests (Q6 partial)
- **Contract tests**: the LDAP service and its Compose wiring, the federation configuration, the StarRocks settings and user plan, the migration plan, and the client script.
- **Property-based tests (Hypothesis)** for the pure parts:
  - round trip of the LDAP entry render and parse (PBT-02)
  - invariants of the user-sync and migration plans (PBT-03)

  These use domain generators (PBT-07), with shrinking and seeds kept (PBT-08) and Hypothesis as the framework (PBT-09).

## Non-Functional Requirements
- **Secrets**:
  - no passwords in arguments, output, Compose files, or `docker inspect`
  - LDAP passwords stored hashed (SSHA or stronger)
  - bind credentials in protected files
- **TLS**: Keycloak to LDAP, StarRocks to LDAP, and clients to StarRocks for password logins.
- **Least privilege**:
  - Keycloak's bind identity writes `ou=people` only
  - StarRocks binds only as the user logging in
  - LDAP is not published to the host
- **LDAP outage**:
  - Keycloak sign-ins of federated users fail, and so do StarRocks password logins
  - client service accounts and existing sessions keep working
  - the syncs keep their safety rules
- **Idempotency**: the bootstraps and the migration can be rerun.
- **Verified live**:
  - migration of the current users, keeping groups and Jupyter homes
  - Keycloak sign-in with the same passwords
  - StarRocks password login for a person and a service user, refused without TLS
  - roles unchanged
  - password change in Keycloak reaching StarRocks
  - new user and new product writer created in LDAP
  - the Airflow writer broker still working

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q5: B) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced; others advisory) | Requirements Analysis (Q6: B) |
| Resiliency Baseline | No | Requirements Analysis (Q7: B) |

## Out of scope
- Groups in LDAP.
- Long-lived BI tokens (the separate follow-up).
- FreeIPA and Kerberos.
- LDAP high availability.
