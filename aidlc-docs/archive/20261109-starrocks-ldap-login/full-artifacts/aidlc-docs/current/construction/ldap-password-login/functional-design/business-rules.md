# Business Rules — ldap-password-login

## BR-1 LDAP directory
1. **Listener**: `ldaps:///` only, plus the local `ldapi:///` socket for the healthcheck. No plain `ldap:///` listener and no host port.
2. **Password hashing**: `password-hash {ARGON2}`. Passwords enter only through the password-modify operation or a hashed seed.
3. **Access control**:
   - `cn=keycloak` writes `ou=people` and passwords there, and reads the base entry.
   - Users read their own entry and change their own password.
   - Anonymous may only authenticate.
   - Everything else is denied.
4. **Seeding**: only an empty volume is seeded. An existing tree is never re-seeded or overwritten.
5. **Secrets**: the admin and bind passwords never appear in `slapd.conf` as plain text (hashes only), in logs, or in arguments.

## BR-2 Keycloak federation (`lakehouse-ldap`)
- **Provider settings**:
  - `editMode=WRITABLE`, `vendor=other`, `connectionUrl=ldaps://ldap:636`, `authType=simple`, `bindDn=cn=keycloak,…`
  - `usersDn=ou=people,…`, `searchScope=one level`
  - `usernameLDAPAttribute=uid`, `rdnLDAPAttribute=uid`, `uuidLDAPAttribute=entryUUID`, `userObjectClasses=inetOrgPerson, organizationalPerson`
  - `importEnabled=true`, `syncRegistrations=true`, `usePasswordModifyExtendedOp=true`
  - `trustEmail=true`, `pagination=false`, `useTruststoreSpi=always`
- **Mappers**: Keycloak's default mappers, unchanged.
- **Bootstrap**:
  - The provider is created if missing, and its connection and bind settings are updated on drift.
  - A provider with another `usersDn` or `editMode` is a conflict, refused without change.
  - It is ensured **before** bootstrap users are created.
- **Groups**: no LDAP group mapper.

## BR-3 StarRocks
1. **TLS**: `ssl_force_secure_transport = true`; every MySQL-protocol connection must use TLS.
2. **LDAP settings**: LDAPS to `ldap:636` with `ssl_conn_allow_insecure = false` and the CA trust store. Direct bind with `uid=${USER},ou=people,dc=lakehouse,dc=local`; StarRocks holds no LDAP credential.
3. **User sync**:
   - New users are created `IDENTIFIED WITH authentication_ldap_simple`.
   - JWT users are switched in place: `ALTER USER '<u>'@'%' IDENTIFIED WITH authentication_ldap_simple`, keeping roles and objects.
   - All other rules are unchanged: native-password conflicts left alone, `root` never managed, users who left every group dropped, the safety checks.
4. **Network runner**: `--ssl --ssl-ca=/run/certs/starrocks-ca.crt --ssl-verify-server-cert`.

## BR-4 Migration
1. **Preflight**, refusing with no change unless all hold:
   - Keycloak and LDAP are healthy, and the `lakehouse-ldap` provider exists and passes its connection and authentication test.
   - No Jupyter server is running that mounts the old home of a user to migrate (checked through `docker ps --filter volume=`).
   - `--yes`, or a typed `migrate`, unless `--dry-run`.
2. **Backup**: a `pg_dump` of the Keycloak database and the inventory (usernames, IDs, groups; no passwords) go to `.runtime/backups/<time>-pre-ldap/` (directory 0700, files 0600). The dump is never printed.
3. **Inventory**:
   - **Included**: local users (no `federationLink`), not `service-account-*`.
   - **Disabled users** are migrated and stay disabled (FD-Q1).
   - **Invalid `uid`**: a username that is not a valid `uid` is refused and reported, and that user stays local.
4. **Password**: from the PasswordSource precedence `bootstrap`, then `writer-file`, then `default`. A missing or empty writer file falls back to `default` and is reported.
5. **Order per user**: the MigrationStep order. **The local copy is deleted only after `verify_bind` succeeds.**
   - If an entry already exists in LDAP (a resumed run), its password is set again and verified.
   - After the import, the new user must have `federationLink` set and the same username; otherwise the run stops with that user named.
6. **Restore**:
   - groups exactly as before (Keycloak groups)
   - `enabled` and `emailVerified` as before
   - first name, last name, and email as before
   - required actions empty
   - no temporary password
7. **Jupyter home** (FD-Q2):
   - If the old volume exists, create the new one, copy with ownership and permissions (`cp -a`), and verify: the same file count and total bytes.
   - Then delete the old volume, and delete the old Hub user through the Hub REST API with the maintenance token. A missing old Hub user counts as deleted.
   - If verification fails, keep both volumes and stop, naming the user.
8. **After all users**: delete the Keycloak `starrocks` client if present, then run the Polaris and StarRocks syncs.
9. **Idempotency**: an already federated user is skipped. A rerun after any failure continues from the first incomplete step for each user.
10. **Output**: per user, its steps and password source. Never a password, token, or dump content. Exit codes: 0 success, 1 failure, 2 refusal or usage.

## BR-5 Clients
- `starrocks-login.sh`: the password from a prompt (no echo) or `--password-file`, sent through `MYSQL_PWD`. Flags: `--enable-cleartext-plugin`, `--ssl-mode=VERIFY_IDENTITY`, and the StarRocks CA.
- `starrocks-token.sh` is deleted; the README documents username and password over TLS.

## BR-6 Fresh install and reset
- A fresh realm gets the provider first, then the bootstrap users, which therefore land in LDAP.
- The reset deletes `ldap-data`; the certificates and passwords go with `.runtime/credentials`.
- No migration is needed after a reset.
