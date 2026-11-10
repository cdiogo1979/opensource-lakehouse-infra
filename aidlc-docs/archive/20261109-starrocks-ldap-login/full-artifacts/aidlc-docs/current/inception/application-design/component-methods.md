# Component Methods — StarRocks LDAP Login

## C1 LDAP directory (`infra/ldap/ldap-entrypoint.sh`)
- `render_config`: `slapd.conf` from the template, with the admin hash from `/run/secrets/ldap_admin_password` (made by `slappasswd -h {ARGON2}`). Writes nothing secret to logs.
- `seed_if_empty`: `slapadd` of the base tree, `ou=people`, `ou=services`, and `cn=keycloak` (hashed bind password), only when the MDB is absent.
- `exec slapd -h "ldaps:/// ldapi:///"` with TLS from `/run/certs`.
- **ACLs**:
  - `userPassword`: write by `cn=keycloak`, write by self, auth by anonymous
  - `ou=people`: write by `cn=keycloak`, read by self
  - base entry: read by `cn=keycloak`
  - nothing else

## C2 Certificates (`scripts/setup/prepare-ldap-certificates.py [--rotate]`)
- `ensure_ca()`, `ensure_server_cert(san=["ldap"])`; `stage_ca()` to `.runtime/container-mounts/ldap-ca.crt`. Idempotent; it refuses symlinks.

## C3 Keycloak federation (`infra/keycloak/ldap_federation.py`)
- `desired_component(realm_id, bind_password) -> dict`: the provider settings (fixed in Functional Design).
- `ensure_ldap_federation(api, realm_id, bind_password) -> str`: create, update the bind credential and connection settings on drift, or accept as equal. It reports the outcome and never the credential.
- `test_connection(api, component)`: Keycloak's `testLDAPConnection` (connection and authentication), used by the bootstrap and the migration preflight.

## C4 StarRocks
- **`fe.conf`**:
  - `ssl_force_secure_transport = true`
  - `authentication_ldap_simple_server_host = ldap`, `authentication_ldap_simple_server_port = 636`
  - `authentication_ldap_simple_ssl_conn_allow_insecure = false`
  - `authentication_ldap_simple_ssl_conn_trust_store_path = /run/certs/ldap-ca.crt`
  - `authentication_ldap_simple_bind_dn_pattern = uid=${USER},ou=people,dc=lakehouse,dc=local`
- **`reconcile-starrocks-users.py`**:
  - `ldap_identity_clause()` gives `IDENTIFIED WITH authentication_ldap_simple`.
  - `plan_users()` adds `switch` for users whose plugin is JWT (or any non-LDAP plugin except native-password conflicts, which stay as today).
  - `render_plan()` emits `ALTER USER … IDENTIFIED WITH authentication_ldap_simple`.
- **`NetworkRunner._command()`**: `--ssl --ssl-ca=/run/certs/starrocks-ca.crt --ssl-verify-server-cert`.

## C5 `starrocks-login.sh [--password-file FILE] <user> [mysql args]`
The password goes through `MYSQL_PWD`, passed to the container through the environment. Flags: `--enable-cleartext-plugin`, `--ssl-mode=VERIFY_IDENTITY`, `--ssl-ca`.

## C6 Migration (`migrate-users-to-ldap.py [--dry-run] [--yes]`)
| Method | Purpose |
|---|---|
| `inventory(api) -> list[LocalUser]` | Local, non-service-account users with groups, profile, and old ID |
| `password_source(user) -> (source, password)` | Bootstrap file, writer password file, or the default (reported) |
| `ldap_entry(user) -> str` | LDIF for `uid=<user>,ou=people,…` (render and parse are a property-tested pair) |
| `write_entry(user, password)` | Add the entry if absent, then set the password through password-modify, as `cn=keycloak` |
| `verify_bind(user, password) -> bool` | LDAP bind check |
| `replace_local_user(api, user) -> new_id` | Delete local, import through lookup, restore groups and flags |
| `copy_home(old_id, new_id)` | Copy the Jupyter home volume, refusing while that user's server runs |
| `plan(users, state) -> list[Step]` | Pure plan; the dry run prints it |
