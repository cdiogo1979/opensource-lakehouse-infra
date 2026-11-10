# Code Summary — ldap-password-login

Code Generation changed repository files only. `prepare-runtime.py` was run once and created the new runtime files: the LDAP secrets and certificates, the Hub maintenance token, and the Keycloak `truststore-paths` setting. No service was restarted or recreated. The live migration runs in Build and Test.

## Created
| Path | Purpose |
|---|---|
| `infra/ldap/Dockerfile` | OpenLDAP 2.6.8 from Alpine 3.22 pinned by digest; packages pinned at `2.6.8-r0` |
| `infra/ldap/slapd.conf.template` | Schemas, Argon2 hashing, TLS 1.2+, MDB, least-privilege ACLs |
| `infra/ldap/ldap-entrypoint.sh` | Renders the config, seeds an empty volume once, refreshes the Keycloak bind hash at each start (`slapmodify`), runs slapd on LDAPS and ldapi only |
| `scripts/setup/prepare-ldap-certificates.py` | Local LDAP CA and server certificate (SAN `ldap`), with `--rotate` |
| `infra/keycloak/ldap_federation.py` | The `lakehouse-ldap` writable provider: create, drift, or conflict, plus Keycloak's connection test |
| `infra/keycloak/ldap_people.py` | Pure model: LDAP entries and LDIF, password sources, migration plan |
| `scripts/operations/migrate-users-to-ldap.py` | One-time, resumable migration with a Keycloak database backup, verification before deletion, and the Jupyter home copy |
| `tests/ldap/ldap_strategies.py`, `test_ldap_people_properties.py`, `test_ldap_contract.py` | Generators, properties P1, P2, P3, P5, P6, and contracts |

## Modified
| Path | Change |
|---|---|
| `compose.core.yml` | The `ldap` service and volume; Keycloak mounts the LDAP CA and waits for LDAP; the scheduled sync mounts the StarRocks CA |
| `compose.starrocks.yml` | The FE mounts the LDAP CA |
| `compose.jupyter.yml`, `infra/jupyter/hub/jupyterhub_config.py` | The `lakehouse-maintenance` service, with a mounted token and an `admin:users`-only role |
| `scripts/setup/prepare-runtime.py` | LDAP and Hub secrets, both certificate scripts, Keycloak `truststore-paths` |
| `scripts/lakehouse.sh` | `ldap` starts with the first core group (and is built); included in status and stop |
| `scripts/operations/reset-lakehouse.py` | `ldap-data` volume |
| `infra/keycloak/bootstrap-realm.py`, `realm-contract.json` | Federation before groups and users; the `starrocks` token client and its audience mapper retired |
| `infra/starrocks/conf/fe.conf` | `ssl_force_secure_transport`, LDAP settings (LDAPS, CA, direct bind pattern) |
| `infra/starrocks/reconcile-starrocks-users.py` | LDAP-login users; JWT users switched in place (`ALTER USER`) |
| `infra/starrocks/starrocks_common.py` | The network runner uses TLS with CA verification |
| `scripts/clients/starrocks-login.sh` | Username and password through `MYSQL_PWD`, cleartext plugin, verified TLS |
| `README.md` | LDAP component, one password everywhere, migration, StarRocks password login (CLI, DBeaver, JDBC, BI), reset, backup, limitations |
| Tests | StarRocks (properties P2, P6, P8 for LDAP; TLS runner; login), operations (modules, reset), JupyterHub, Keycloak |

## Removed
- `scripts/clients/starrocks-token.sh`, moved to the session scratchpad, since the workspace has no git history.

## Test results
`PYTHONPATH=infra/jupyter/hub python3 -m pytest -q tests`: **352 passed, 1 skipped, 1 failed**. The failure is the known Airflow developer-role drift.

## To verify live (Build and Test)
- Whether `fe.conf` expands `${USER}` in `authentication_ldap_simple_bind_dn_pattern`. If it does, set it at runtime from the bootstrap.
- The value of the LDAP auth plugin name in `SHOW ALL AUTHENTICATION` (assumed `AUTHENTICATION_LDAP_SIMPLE`).
- Connector/J and DBeaver with username and password over TLS.

## Fixes made during Build and Test
| Finding | Fix |
|---|---|
| `fe.conf` expands `${USER}`; the FE refused to start | `authentication_ldap_simple_bind_dn_pattern` removed from `fe.conf`; set at runtime by `starrocks_common.ensure_ldap_login` from the runtime bootstrap |
| An FE restart loses the runtime setting | `reconcile-starrocks-users.py` re-applies it after its safety checks |

Suite after the fixes: **354 passed, 1 skipped, 1 failed** (the known Airflow drift).
