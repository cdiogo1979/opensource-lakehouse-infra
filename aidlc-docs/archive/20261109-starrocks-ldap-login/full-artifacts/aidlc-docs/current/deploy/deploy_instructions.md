# Deployment Instructions — StarRocks LDAP login

**Applies to**: an existing stack running the previous version, on one machine. It is already done on the stack used in Build and Test.

**Manual or automated**: every step is run by hand, in this order.

**Required inputs**:
- a maintenance window: Keycloak, JupyterHub, and the StarRocks FE are recreated, and users are migrated
- users told that StarRocks now takes their password over TLS, and that hand-changed passwords are reset

## 1. Baseline
- **Prerequisites**: the stack is running; nobody has a Jupyter server running (stop them from the Hub admin page).
- **Execution**:
  - `python3 scripts/verify/role-matrix.py > role-matrix-before.txt`
  - `python3 scripts/operations/migrate-users-to-ldap.py --dry-run`, then review the users and password sources
- **Validation**: the role matrix passes; the dry run lists the expected users.
- **Failure handling**: stop if the baseline fails.

## 2. Start with LDAP
- **Execution**: `scripts/lakehouse.sh start`. It prepares the secrets and certificates, starts `ldap`, recreates Keycloak (the federation is created and tested), JupyterHub, and the StarRocks FE (forced TLS, bind pattern set).
- **Validation**:
  - the realm bootstrap prints `ldap-federation=created` (or `unchanged`)
  - StarRocks prints `LDAP password login: set`
  - `scripts/lakehouse.sh status` shows every service healthy
- **Failure handling**:
  - **FE fails to start**: copy `/opt/starrocks/fe/log/fe.out` out of the container (`docker cp`).
  - **Federation test fails**: check the `ldap` health, the CA mount, and `ldap-keycloak-password`.
  - **Before the migration, rollback is easy**: delete the `lakehouse-ldap` provider in Keycloak and return to the previous code.

## 3. Rebuild the scheduled sync
- **Execution**: `docker compose -f compose.core.yml --profile scheduled-reconciliation up -d --build polaris-group-reconciler`.
- **Validation**: its log shows both syncs succeeding.

## 4. Migrate the users
- **Execution**: `python3 scripts/operations/migrate-users-to-ldap.py --yes`.
- **Validation**:
  - every user is reported migrated
  - the StarRocks sync reports the users switched to LDAP
  - a second `--dry-run` reports nothing to migrate
- **Failure handling**: rerun the same command; it finishes interrupted users first. The Keycloak database dump is in `.runtime/backups/<time>-pre-ldap/`. There is **no automatic rollback**: restoring means stopping Keycloak, restoring that dump into `keycloak-db`, and returning to the previous code.

## 5. Verify
- **Execution**:
  - `scripts/clients/starrocks-login.sh <user>` for a person and for `srv-default-writer` (`--password-file .runtime/credentials/srv-default-writer-password`)
  - `python3 scripts/verify/role-matrix.py`, compared with the baseline
  - `python3 scripts/verify/polaris-keycloak-auth.py`
- **Validation**: logins show the expected roles; plain-text connections are refused; the role matrix matches.

## 6. Inform users
- **StarRocks clients**: DBeaver, JDBC, and BI use username and password with `sslMode=REQUIRED` (README, StarRocks section).
- **Passwords**: migrated users have the documented default or their file password; they can change it on the Keycloak account page.
