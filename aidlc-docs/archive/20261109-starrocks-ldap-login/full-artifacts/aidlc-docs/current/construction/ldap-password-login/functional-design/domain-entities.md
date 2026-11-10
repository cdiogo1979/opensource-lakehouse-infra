# Domain Entities — ldap-password-login

## LdapPerson (`uid=<username>,ou=people,dc=lakehouse,dc=local`)
| Attribute | Value | Rule |
|---|---|---|
| `objectClass` | `top`, `person`, `organizationalPerson`, `inetOrgPerson` | fixed |
| `uid` | username | `^[a-z0-9][a-z0-9._-]{0,62}$`; anything else is refused and reported |
| `cn` | first name, or the username when empty | Keycloak's default mapper reads `cn` as the first name |
| `sn` | last name, or the username when empty | Keycloak's default mapper reads `sn` as the last name |
| `mail` | email, when present | |
| `userPassword` | set only through the password-modify operation | stored `{ARGON2}` by the server, never written as an attribute |

LDIF values that are not "safe strings" (leading space, colon, or `<`; non-ASCII; control characters) are written base64 (`attr:: value`), so names in any script round-trip.

## LocalUser (from Keycloak, before migration)
`id` (the old `sub`), `username`, `enabled`, `emailVerified`, `firstName`, `lastName`, `email`, `groups` (names), `federationLink` (absent).

Service-account users (`service-account-*`) are never local users for the migration.

## PasswordSource
| Source | Applies to | Password |
|---|---|---|
| `bootstrap` | the five users in `infra/keycloak/bootstrap-users.json` | its `default_password` |
| `writer-file` | a product's `writer_user.username` | the first line of its `password_file` |
| `default` | every other local user | `ChangeM3!`, and the user is listed by name in the report |

## MigrationStep (planned per user, in order)
`write_entry` → `set_password` → `verify_bind` → `delete_local` → `import` → `restore` (groups, enabled, emailVerified, no required actions) → `copy_home` → `verify_home` → `delete_old_home` → `delete_old_hub_user`.

## HomeVolume
- Name: `lakehouse-jupyter-home-` + the first 32 hex characters of `sha256(sub)`, as in `lakehouse_policy.persistent_home_volume`.
- Old name from the old ID, new name from the new ID.

## StarRocksUserState (user sync)
- Name, auth plugin, and roles.
- Desired plugin: `AUTHENTICATION_LDAP_SIMPLE`. JWT users are **switched**. Native-password users with a desired name stay conflicts (unchanged).

## Settings (no secrets in tracked files)
| Item | Value |
|---|---|
| LDAP URL | `ldaps://ldap:636` (Keycloak, StarRocks, migration) |
| Keycloak bind | `cn=keycloak,ou=services,dc=lakehouse,dc=local`; password `.runtime/credentials/ldap-keycloak-password` |
| LDAP admin | `cn=admin,dc=lakehouse,dc=local`; password `.runtime/credentials/ldap-admin-password` (recovery only) |
| CA | `.runtime/container-mounts/ldap-ca.crt` |
| Hub maintenance token | `.runtime/credentials/jupyterhub-maintenance-token`, scoped to `admin:users` (FD-Q2) |
