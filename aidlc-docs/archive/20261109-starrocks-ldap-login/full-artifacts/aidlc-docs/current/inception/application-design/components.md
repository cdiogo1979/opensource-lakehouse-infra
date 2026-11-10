# Components — StarRocks LDAP Login

| # | Component | Location | New or changed | Responsibility |
|---|---|---|---|---|
| C1 | **LDAP directory** | `infra/ldap/{Dockerfile,ldap-entrypoint.sh,slapd.conf.template}`; service `ldap` in `compose.core.yml`; volume `ldap-data` | New | OpenLDAP 2.6.8 from pinned Alpine 3.22 packages. One tree, `dc=lakehouse,dc=local`, with `ou=people` (users) and `ou=services` (`cn=keycloak`). LDAPS only (636), plus a local `ldapi` socket for the healthcheck. Argon2 password hashing. Seeds the tree on an empty volume. No host port |
| C2 | **LDAP certificates and secrets** | `scripts/setup/prepare-ldap-certificates.py` (new); `prepare-runtime.py` | New | A local LDAP CA and a server certificate (SAN `ldap`) in `.runtime/credentials/`. The CA is staged in `.runtime/container-mounts/` for Keycloak, StarRocks, and the migration. Admin and Keycloak bind passwords are created once |
| C3 | **Keycloak federation** | `infra/keycloak/ldap_federation.py` (new); `bootstrap-realm.py`; `compose.core.yml` (Keycloak trust store) | Changed | Ensures the `lakehouse-ldap` user-storage provider (writable, import on, password-modify operation, LDAPS) and its default mappers, before any user is created. Keycloak trusts the LDAP CA (`truststore-paths`) |
| C4 | **StarRocks password login** | `infra/starrocks/conf/fe.conf`; `compose.starrocks.yml` (LDAP CA mount); `reconcile-starrocks-users.py`; `starrocks_common.py` | Changed | `ssl_force_secure_transport`; LDAP over LDAPS with the CA and direct bind by `uid`. The user sync creates `authentication_ldap_simple` users and switches JWT users in place. The network runner uses TLS with CA verification |
| C5 | **Clients** | `scripts/clients/starrocks-login.sh`; README | Changed | Username and password over verified TLS (cleartext plugin). `starrocks-token.sh` is removed |
| C6 | **User migration** | `scripts/operations/migrate-users-to-ldap.py` (new) | New | One-time, idempotent, dry-runnable: back up, inventory local users, write the LDAP entry and password, verify, delete the local copy, import, restore groups, copy the Jupyter home, remove the `starrocks` client, run the syncs |
| C7 | **Lifecycle** | `scripts/lakehouse.sh`; `scripts/operations/reset-lakehouse.py`; `bootstrap-default-product.sh` | Changed | `ldap` starts with core before the realm bootstrap; the reset deletes `ldap-data`. A fresh install needs no migration |

## Unchanged (verified by the probes or the design)
- Groups stay in Keycloak, so the data product scripts, the Polaris sync, and every OIDC service are unchanged.
- `create-user.py`, the product writer-user creation, and `bootstrap-users.py` call the Keycloak admin API, which writes to LDAP once the provider exists.
- The Airflow writer broker's password grant is checked by Keycloak against LDAP.
- `service-account-*` users and the `master` realm stay local.
