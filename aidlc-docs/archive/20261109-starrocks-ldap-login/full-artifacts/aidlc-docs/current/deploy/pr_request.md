# PR Request — StarRocks LDAP login

_Proposed PR description. No pull request has been created; this workspace has no git metadata._

## Problem
People and service users could reach StarRocks only with a Keycloak token. That meant token files for DBeaver and JDBC, and no option for BI tools that only take a username and password. StarRocks cannot check a Keycloak password, and Keycloak cannot export passwords.

## Solution
- **A lightweight LDAP directory** (`ldap`, OpenLDAP 2.6.8 from pinned Alpine packages) is the shared password store. It accepts LDAPS only, stores Argon2 hashes, and has no host port. Keycloak's bind identity may write only `ou=people`.
- **Keycloak keeps its users in LDAP** (the writable `lakehouse-ldap` provider). Groups, clients, and every OIDC service are unchanged. Creating users, resets, and password changes in Keycloak write to LDAP, so the existing user and product scripts are unchanged.
- **StarRocks checks passwords against LDAP**, binding as the user, so it holds no LDAP secret.
  - Every connection must use TLS (`ssl_force_secure_transport`).
  - The user sync creates users with LDAP login and switched the former JWT users in place, keeping grants and materialized views.
  - The bind pattern is a runtime setting: the runtime bootstrap sets it, and every sync re-applies it.
- **Clients**: `starrocks-login.sh` uses a password over verified TLS. `starrocks-token.sh` and the Keycloak `starrocks` token client are retired.
- **Migration**: `migrate-users-to-ldap.py` moves existing users with their known passwords, once and resumably:
  - it backs up the Keycloak database first
  - it verifies each user's password before deleting the local copy
  - it restores groups and profile
  - it copies the Jupyter home to the new ID, and deletes the old volume and Hub user after verification (through a Hub maintenance service limited to user management)
- **Decisions**: Q1 password only, Q2 writable federation, Q3 known passwords, Q4 own OpenLDAP image, C1 copy homes, C2 retire the token client, AD-Q1 force TLS, FD-Q1 migrate disabled users, FD-Q2 delete old homes after the copy. Extensions: PBT partial.

## Main changes
| Area | Paths |
|---|---|
| LDAP | `infra/ldap/{Dockerfile,ldap-entrypoint.sh,slapd.conf.template}`, `scripts/setup/prepare-ldap-certificates.py`, the `ldap` service and `ldap-data` volume in `compose.core.yml` |
| Keycloak | `infra/keycloak/{ldap_federation.py,ldap_people.py}` (new); `bootstrap-realm.py`, `realm-contract.json`; Keycloak CA mount and `truststore-paths` |
| StarRocks | `infra/starrocks/conf/fe.conf` (forced TLS, LDAP); `starrocks_common.py` (TLS runner, `ensure_ldap_login`); `bootstrap-starrocks.py`; `reconcile-starrocks-users.py`; `compose.starrocks.yml` (LDAP CA) |
| Clients | `scripts/clients/starrocks-login.sh`; `scripts/clients/starrocks-token.sh` removed |
| JupyterHub | `jupyterhub_config.py` (maintenance service), `compose.jupyter.yml` (token mount) |
| Migration | `scripts/operations/migrate-users-to-ldap.py` |
| Lifecycle | `scripts/setup/prepare-runtime.py`, `scripts/lakehouse.sh`, `scripts/operations/reset-lakehouse.py` |
| Docs and tests | `README.md`; `tests/ldap/` (generators, properties, contracts); updated StarRocks, Keycloak, JupyterHub, and operations tests |

## Verification
- **Suite**: `PYTHONPATH=infra/jupyter/hub python3 -m pytest -q tests` gives 354 passed, 1 skipped, 1 failed. The failure is the pre-existing Airflow developer-role drift.
- **Live** (Build and Test summary):
  - the start, and the migration of 5 users
  - Keycloak sign-ins and StarRocks password logins (people and a service user, with roles); wrong-password and plain-text refusals
  - password-change propagation; new user and product writer in LDAP
  - Connector/J with TLS required and verified, refused without TLS
  - writer token, role matrix, RustFS, Jenkins (known missing CI job), scheduled sync over TLS, bind-pattern self-heal
- **Fixed during Build and Test**: the `${USER}` expansion in `fe.conf`, and the bind pattern lost on an FE restart.
- **Not run**:
  - interactive JupyterHub, Airflow, and DBeaver sign-ins by migrated users
  - a destructive reset and fresh install
  - an Airflow DAG run

## Deployment
**Ordered steps are required** for existing stacks: see [`deploy_instructions.md`](deploy_instructions.md). The local stack used in Build and Test is already migrated.

## Risks and limitations
- **Password resets**: migrated users' passwords became their known values (bootstrap default or writer file); hand-changed passwords were reset. In this stack none were reset beyond those values.
- **Token login retired**: StarRocks token login is gone; clients need username and password over TLS.
- **LDAP outage**: Keycloak sign-ins and StarRocks password logins fail while `ldap` is down; client service accounts and open sessions keep working.
- **Bind-pattern window**: the bind pattern is runtime state. After an FE restart outside `lakehouse.sh start`, password logins fail until the next sync (at most five minutes).
- **Staged mounts**: the existing staged-mount behavior applies; running containers see refreshed secret files only after a restart.
- **No automatic rollback** after the migration: users would be recreated locally from the backup.
- **Follow-ups**: the Airflow developer-role drift, the Jenkins CI job, and the BI follow-up, which can now use password login.
