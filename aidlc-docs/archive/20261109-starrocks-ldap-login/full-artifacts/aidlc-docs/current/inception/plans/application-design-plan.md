# Application Design Plan — StarRocks LDAP Login

## Plan
- [x] Read requirements, the execution plan, reverse engineering, and the canonical designs
- [x] Probes (throwaway objects only; all removed, live settings restored)
- [x] Collect answers (AD-Q1)
- [x] Generate components.md, component-methods.md, services.md, component-dependency.md, application-design.md
- [x] Validate against FR-1..FR-7

## Probe results (2026-11-09)
| # | Question | Result |
|---|---|---|
| 1 | Alpine OpenLDAP packages | Alpine 3.22.8 ships OpenLDAP 2.6.8-r0 with `back-mdb`, `clients`, and the `argon2` password module. A static `slapd.conf` with ACLs and the seeded tree works |
| 2 | Keycloak 26.8 writable federation (throwaway realm) | Admin-API user creation writes an `inetOrgPerson` entry (`uid`, `cn` = first name, `sn` = last name, `mail`). Passwords go through the password-modify operation and are stored `{ARGON2}`. A reset changes the LDAP password, and the old password then fails in LDAP and Keycloak. Keycloak groups on federated users appear in the `groups` claim. Deleting a federated user deletes its LDAP entry. Local users created before the provider stay local and keep working. Users without names are accepted with the default mappers; a hard-coded `sn` mapper overrode real last names and is rejected. Creating a Keycloak user whose `uid` already exists in LDAP fails (409), and deleting a realm leaves its LDAP entries |
| 3 | StarRocks TLS enforcement (live FE, reverted) | `ssl_force_secure_transport = true` (static, `fe.conf`) refuses plain-text connections ("insecure transport prohibited"). TLS logins, root through `docker exec` (client default TLS), and token login keep working. The scheduled sync's MariaDB client with `--skip-ssl` is refused, but works with `--ssl` |

## Design question

### AD-Q1 Protecting password logins
A) Force TLS for all StarRocks connections (`ssl_force_secure_transport`); the scheduled sync uses TLS with CA verification (Recommended)
B) Do not force; document
X) Other

[Answer]: A
