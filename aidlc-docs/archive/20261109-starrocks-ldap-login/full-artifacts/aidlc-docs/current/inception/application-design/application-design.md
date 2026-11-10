# Application Design — StarRocks LDAP Login

Consolidates [components.md](components.md), [component-methods.md](component-methods.md), [services.md](services.md), and [component-dependency.md](component-dependency.md). The decision and probe results are in [application-design-plan.md](../plans/application-design-plan.md).

## Summary
- **LDAP directory**: a new core service, `ldap`. It runs OpenLDAP 2.6.8 from pinned Alpine 3.22 packages, LDAPS only, with no host port, Argon2 password hashes, and one `ou=people` tree.
- **Keycloak** keeps users there through a writable LDAP provider. Groups, clients, and every OIDC service are unchanged, and the user scripts keep calling Keycloak, which writes to LDAP (probed).
- **StarRocks** checks passwords by binding to LDAP as the user, and forces TLS on every connection (AD-Q1, probed). The user sync switches users from JWT to LDAP login in place. `starrocks-login.sh` uses a password, and the token script and client are removed.
- **Migration**: a one-time, verified migration moves the current users with their known passwords and copies their Jupyter homes. Fresh installs create users in LDAP from the start.

## Decisions
| ID | Decision |
|---|---|
| Q1 | Password-only StarRocks login (one login method per user, probed) |
| Q2 | Writable federation; groups stay in Keycloak |
| Q3, C1 | Migration with known passwords; Jupyter homes copied to the new IDs |
| Q4 | Own OpenLDAP image from pinned Alpine packages |
| C2 | Remove the `starrocks` client and `starrocks-token.sh` |
| AD-Q1 | `ssl_force_secure_transport` for all StarRocks connections; the sync's network client verifies the StarRocks CA |
| Design | **Keycloak's default LDAP mappers** (`uid`, `cn` = first name, `sn` = last name, `mail`): they handle users without names, unlike a hard-coded `sn`, which overrode real names |
| Design | **StarRocks direct bind** by DN pattern, so StarRocks holds no LDAP secret |
| Design | **The migration writes LDAP entries itself before deleting the local Keycloak user**. Keycloak refuses to create a user whose `uid` already exists in LDAP, and deleting a federated user deletes the LDAP entry, so the order matters |

## Risks
| Risk | Mitigation |
|---|---|
| A migrated user is locked out | Verify the LDAP bind before deleting the local copy; back up the Keycloak database first; the migration is resumable and reports per user |
| A Jupyter home is lost on the ID change | Copy the volume, keep the old one, and refuse while that user's server runs |
| TLS enforcement breaks an internal client | Probed: only the scheduled sync's `--skip-ssl` needed changing; Build and Test checks every path |
| An LDAP outage blocks sign-ins | Documented. Service accounts and sessions keep working; LDAP is a local single node |
| Old StarRocks token users | Switched in place by the sync, so grants and MV ownership are kept |

## Canonical knowledge impact
As in the execution plan: update application design, product access, and StarRocks access; keep Jenkins unchanged.
