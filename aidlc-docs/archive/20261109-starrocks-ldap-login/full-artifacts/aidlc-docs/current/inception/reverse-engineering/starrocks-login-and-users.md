# StarRocks Login and User Paths — Focused Reverse Engineering

## How StarRocks login works today
- **One StarRocks user per Keycloak user**: `infra/starrocks/reconcile-starrocks-users.py` creates a user for every member of a product group with `IDENTIFIED WITH authentication_jwt`. The JWKS comes from Keycloak, the principal field is `preferred_username`, and the audience is `starrocks`. Roles follow the groups. The sync runs in the product bootstrap, on demand, and every five minutes.
- **Clients**:
  - `scripts/clients/starrocks-login.sh` gets a password-grant token from the `starrocks` client and logs in with the MySQL 9.x OpenID Connect plugin.
  - DBeaver and JDBC use a token file kept fresh by `scripts/clients/starrocks-token.sh --watch`.
- **TLS**: the FE serves TLS from a local CA. The OIDC client plugin refuses plain text; password logins are not forced onto TLS.
- **Root**: the only native-password user.

## Where users and passwords are created today (all in Keycloak's own database)
| Path | What it does |
|---|---|
| `infra/keycloak/bootstrap-realm.py` | Creates the five bootstrap users if missing, with the default password |
| `scripts/bootstrap/bootstrap-users.sh` (`bootstrap-users.py`) | Resets the five users' password, profile, and groups |
| `scripts/operations/create-user.sh` (`create-user.py`) | Creates one user with no groups |
| `infra/keycloak/keycloak_products.py` | Creates each product's writer user, `srv-<p>-writer`, with a password file |
| `scripts/setup/prepare-runtime.py` | Writes `srv-default-writer-password` from `bootstrap-users.json` |
| `scripts/verify/role-matrix.py` | Temporary client service accounts (not users with passwords) |

- **Password consumers outside the browser**:
  - the Airflow writer broker (password grant on `lakehouse-writer` as `srv-default-writer`)
  - `starrocks-login.sh` and `starrocks-token.sh` (password grant on `starrocks`)
- **Not a person**: `service-account-srv-starrocks` is a client-credentials account. It is unaffected by any LDAP change.

## Feasibility probe (2026-11-09, throwaway OpenLDAP 2.6 on the StarRocks network; all objects removed)
StarRocks 4.1.7 settings: per-user `authentication_ldap_simple`, with the `authentication_ldap_simple_*` frontend settings, all mutable at runtime. There is also a login chain, `authentication_chain` (default `[native]`), with `CREATE SECURITY INTEGRATION ... type authentication_ldap_simple`, and group providers.

| Test | Result |
|---|---|
| A. User created `IDENTIFIED WITH authentication_ldap_simple`, granted a product role | **Works.** Login with the LDAP password over TLS gives the user and its role, and the user reads production data. A wrong password is refused with LDAP "Invalid Credentials" |
| A'. The same login without TLS | **Also accepted.** StarRocks does not force TLS for plain-text LDAP passwords, so the design must enforce it |
| B. Existing token user `joe-developer` with LDAP in the login chain | **Not possible.** StarRocks uses the user's own method (JWT) and asks the client for a token; password login never reaches the chain. Token login still works. **One StarRocks user has exactly one login method** |
| C. A user who exists only in LDAP, through the chain | Logs in as a temporary user with **no role** (`NONE`). Roles would need groups from LDAP (a group provider); this platform's groups live in Keycloak |
| Syntax | `DROP SECURITY INTEGRATION IF EXISTS` is not supported |

## What this means
1. **StarRocks users switch method.** To log in with username and password, the synced StarRocks users must be created with `authentication_ldap_simple` instead of `authentication_jwt`. Token login for those users ends: `starrocks-login.sh` and DBeaver move to username and password, and `starrocks-token.sh` becomes unnecessary. Keeping both would need two StarRocks user names per person, or groups in LDAP with chain-only users.
2. **Keycloak and StarRocks must share the password**, so the users must live in LDAP and Keycloak must read them from there through user federation.
   - In **writable** mode, Keycloak's admin API creates users and sets passwords in LDAP. `create-user.py`, the writer-user creation, `bootstrap-users.py` resets, and the account console's password change would then keep working, writing to LDAP.
   - Groups can stay in Keycloak, so the data product scripts, the reconcilers, and every OIDC service are unchanged.
3. **Existing users need migrating.** Users already in Keycloak's own database cannot be moved with their passwords, because Keycloak stores one-way hashes. They must be recreated in LDAP with a new or default password. For this local stack the bootstrap users' default is documented.
4. **TLS**: password logins must be forced onto TLS (A'). StarRocks should reach LDAP over TLS (LDAPS or StartTLS), with the CA in its trust store.
5. **Image**: the bitnami OpenLDAP image used in the probe is a no-longer-maintained "legacy" build. The real choice (OpenLDAP image, or lldap) is a design question.
