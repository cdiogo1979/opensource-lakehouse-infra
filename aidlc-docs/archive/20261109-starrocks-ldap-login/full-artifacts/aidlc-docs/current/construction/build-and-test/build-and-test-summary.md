# Build and Test Summary — StarRocks LDAP Login

## Outcome: passed, with known items
| Check | Result |
|---|---|
| Contract and property suite | 354 passed, 1 skipped, 1 known failure (Airflow developer-role drift) |
| LDAP image (standalone) | Seed, LDAPS bind with CA verification, plain LDAP refused, anonymous people read denied, restart path |
| Start | `ldap` healthy; Keycloak federation created and its bind test passing; StarRocks with forced TLS and the bind pattern set |
| Migration (5 users) | Keycloak database backed up; every user recreated in LDAP with its known password (Argon2), verified, imported, and restored (groups, names, enabled); `joe-developer`'s Jupyter home copied, verified, old volume and old Hub user deleted; `starrocks` client removed; all StarRocks users switched from JWT to LDAP in place; a rerun has nothing to do |
| Keycloak sign-in | All 5 users, same password |
| StarRocks password login | People and the service user `srv-default-writer`, with exact roles; wrong password and plain text refused |
| Password change in Keycloak | Reaches StarRocks at once; `bootstrap-users.sh` restores the default |
| New users | `create-user.sh` user and a product writer created in LDAP; both log in to StarRocks after the sync |
| JDBC (Connector/J 9.3.0) | `REQUIRED` and `VERIFY_IDENTITY` connect; `DISABLED` refused |
| Unchanged services | Writer token (Polaris), role matrix identical, RustFS OIDC; Jenkins all but the known missing CI job; scheduled sync over TLS |

## Findings fixed during Build and Test
| Finding | Fix |
|---|---|
| The FE refused to start: `fe.conf` expands `${USER}` in the LDAP bind pattern ("no such env variable: USER") | The pattern is a runtime setting, set by the StarRocks runtime bootstrap at every start |
| An FE restart outside `lakehouse.sh start` would lose that runtime setting | The user reconcile re-applies it after its safety checks (every five minutes in the scheduled sync); live self-heal verified |
| The LDAP container exited at once: the `ldapi` socket directory was missing | Created in the image and at start (found in the standalone test, during Code Generation) |

Each has a regression test.

## Not run
- An interactive JupyterHub, Airflow, or DBeaver sign-in by a migrated user. The Keycloak sign-ins, the Hub admission groups, and JDBC were verified instead.
- A full reset and fresh install (destructive). The bootstrap order puts the federation before user creation (contract test), and new users created through Keycloak landed in LDAP (live).
- A run of the Airflow DAG. The writer's token through the federated user was verified.

## Behavior to note
- **Staged mounts**: `lakehouse.sh start` replaces the staged files in `.runtime/container-mounts/` atomically, so a running container's single-file mounts point at the previous file until the container restarts. This existing behavior also applies to `ldap`. It reads its secrets at start, and a restart re-reads them.
- **Backups**:
  - The pre-migration Keycloak database dump and user inventory are in `.runtime/backups/20261109T203416Z-pre-ldap/` (mode 0600).
  - The removed `starrocks-token.sh` is in the session scratchpad.
