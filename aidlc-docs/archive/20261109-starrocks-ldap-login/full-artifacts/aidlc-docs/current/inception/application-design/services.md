# Services (Orchestration) — StarRocks LDAP Login

## S1 Start (`lakehouse.sh start`)
1. `prepare-runtime.py`: secrets, plus `prepare-ldap-certificates.py`.
2. Start the databases, RustFS, **`ldap`** (wait healthy), then Keycloak and Polaris.
3. Realm bootstrap: ensure the LDAP federation **before** creating any missing bootstrap user, so fresh installs create users in LDAP.
4. Modules. StarRocks starts with `ssl_force_secure_transport` and the LDAP settings.

## S2 Product bootstrap and syncs
Unchanged order. The StarRocks user sync now creates LDAP-login users and switches JWT users.

## S3 Migration (existing stacks, once)
`migrate-users-to-ldap.py --dry-run`, then `--yes`.
1. **Preflight**: federation present and its connection test passing; LDAP and Keycloak healthy; no Jupyter server running for any user to migrate.
2. **Backup**: `pg_dump` of the Keycloak database to `.runtime/backups/<time>-pre-ldap/` (mode 0600), plus the user inventory (no passwords).
3. **Per user, in order**:
   1. write the entry
   2. set the password
   3. verify the bind
   4. delete the local copy
   5. import
   6. restore groups
   7. copy the home

   Any failure stops before the user's local copy is deleted, or reports the exact user and step.
4. Remove the Keycloak `starrocks` client.
5. Run the Polaris and StarRocks syncs: JWT StarRocks users switch to LDAP login.
6. Print a summary: users migrated, password sources (users reset to the default listed by name), homes copied.

## S4 Reset and rebuild
The reset deletes `ldap-data` and the LDAP certificates with `.runtime/credentials`. A rebuild creates the empty tree, the federation, and then users in LDAP.
