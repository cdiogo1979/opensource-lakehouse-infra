# Code Generation Plan — starrocks-integration

Unit: `starrocks-integration` (the single unit). Code lives at the workspace root and never in `aidlc-docs/`. Traceability refers to FR-1..FR-9, the SR rules, and P1..P8.

## Step 1 — Keycloak identities (FR-3, FR-7; C2)
- [x] `infra/keycloak/realm-contract.json`: add the clients `srv-starrocks` and `starrocks`, and `srv-starrocks` membership in `role-default-writer`.
  - `srv-starrocks`: confidential, service accounts only, Polaris role mapper.
  - `starrocks`: password grant only, audience mapper `aud=starrocks`.
- [x] `infra/keycloak/bootstrap-realm.py`: add `starrocks_service_client_configuration`, `starrocks_login_client_configuration`, and `ensure_service_account_group`, and call them from `main` (idempotent; refuse on conflict).

## Step 2 — Runtime credentials (FR-2, FR-3; C3)
- [x] `scripts/prepare-lakehouse-runtime.py`: create `starrocks-root-password` and `srv-starrocks-client-secret` once, at mode 0600. Stage a read-only `starrocks-root-password` copy for the scheduled reconciler.

## Step 3 — StarRocks runtime (FR-1; C1)
- [x] `docker-compose.starrocks.yml`:
  - `starrocks-fe` and `starrocks-be` with the upstream 4.1.7 digests
  - loopback ports `${STARROCKS_QUERY_PORT:-9030}` and `${STARROCKS_HTTP_PORT:-8030}`
  - networks `core`, `data-access`, and the internal `starrocks`
  - volumes `starrocks-fe-meta` and `starrocks-be-storage`
  - memory limits and health checks
- [x] `infra/starrocks/conf/fe.conf` and `be.conf`, mounted read-only, with no secrets.
- [x] `.env.example`: `STARROCKS_ENABLED=true`, `STARROCKS_QUERY_PORT`, `STARROCKS_HTTP_PORT`, `STARROCKS_FE_MEMORY_LIMIT`, `STARROCKS_BE_MEMORY_LIMIT`.
- [x] `docker-compose.deferred.yml`: change the StarRocks status to `implemented-in-docker-compose.starrocks.yml`.

## Step 4 — Shared SQL layer and StarRocks bootstrap (FR-2, FR-4..FR-6; C4)
- [x] `infra/starrocks/starrocks_common.py`, pure plus transports:
  - environments and the matrix
  - SQL identifier and literal quoting
  - `DockerExecRunner` and `NetworkRunner`, which use stdin and an option file and never echo
  - TSV parsing
  - an output allowlist
- [x] `infra/starrocks/bootstrap-starrocks.py`:
  - `--runtime-only`: root password (SR-21) and BE registration (SR-22)
  - the full run: catalogs (SR-19, SR-20 with `--recreate-catalogs`), MV databases, roles with exact grant enforcement (SR-1..SR-12), and a smoke check
  - opt-out and failure behavior (SR-23, SR-24), and `--dry-run`
  - pure functions: `catalog_definition`, `render_catalog_properties`, `parse_catalog_properties`, `plan_catalog`, `role_grants`, `plan_grants`

## Step 5 — User reconciler (FR-7; C5)
- [x] `infra/starrocks/reconcile-starrocks-users.py`:
  - read the Keycloak memberships (paged)
  - the pure functions `desired_users`, `plan_users`, `jwt_identity_clause`, `parse_jwt_identity`
  - read the JWT users and their grants
  - apply in order: create, grant, revoke, default roles, drop (SR-13..SR-18)
  - `--transport docker|network`, and `--dry-run`

## Step 6 — Scheduled reconciler (C6)
- [x] `infra/polaris/reconciler/Dockerfile`: add a pinned MariaDB/MySQL client package and copy the StarRocks modules.
- [x] `infra/polaris/reconciler/run.sh`: after the Polaris reconcile, run the StarRocks reconcile unless `STARROCKS_ENABLED=false`. If it fails, log it and retry next cycle (SR-24).
- [x] `docker-compose.yml` (`polaris-group-reconciler`): add the `STARROCKS_ENABLED` environment variable and the read-only root-password mount.

## Step 7 — Lifecycle, bootstrap, and reset (FR-2, FR-4; C8)
- [x] `scripts/lakehouse.sh`:
  - include the StarRocks Compose file when enabled
  - start the FE and BE, then run `bootstrap-starrocks.py --runtime-only`
  - `status` and `stop` cover StarRocks
  - new `reconcile-starrocks [--dry-run]`, and update the usage line
- [x] `scripts/bootstrap-default-product.sh`: after the Polaris reconcile, run `bootstrap-starrocks.py` and `reconcile-starrocks-users.py --transport docker`, with skip notices when StarRocks is disabled.
- [x] `scripts/reset-lakehouse.py`: add `lakehouse-local_starrocks-fe-meta`, `lakehouse-local_starrocks-be-storage`, and the network `lakehouse-local_starrocks`.

## Step 8 — Login helper (FR-7; C7)
- [x] `scripts/starrocks-login.sh <user> [mysql args]`:
  - a no-echo password prompt and a token from the `starrocks` client
  - a temporary token file at mode 0600, cleaned up on exit
  - a pinned MySQL 9.x client image (digest chosen at generation) with the OpenID Connect client plugin (SR-26)

## Step 9 — Legacy retirement (FR-8; C10)
- [x] Snapshot the legacy files into `aidlc-docs/current/construction/starrocks-integration/code/legacy-starrocks-snapshot/`. There is no git in this workspace, so this keeps a copy until the closure archive.
- [x] Then remove from the active tree:
  - `infra/starrocks/{fe,be,kerberos,ldap-access,sql-bootstrap,preflight}`
  - `infra/starrocks/conf/{core-site,hive-site}.xml`
  - `scripts/bootstrap-starrocks-sql.sh`
  - `__pycache__` folders
- [x] Confirm that no `write-service-account` reference remains under `infra/starrocks`.

## Step 10 — Tests (NFR; PBT-02/03/07/08/09)
- [x] `tests/starrocks/starrocks_strategies.py`: Hypothesis domain generators (PBT-07).
- [x] `tests/starrocks/test_starrocks_properties.py`: P1..P7, plus P8 as advisory, with `print_blob=True` (PBT-08).
- [x] `tests/starrocks/test_starrocks_compose_contract.py`:
  - digests and loopback ports
  - networks, volumes, no secrets in Compose
  - the `.env.example` keys and the deferred status
- [x] `tests/starrocks/test_starrocks_bootstrap_contract.py`:
  - opt-out and the safety abort (SR-17)
  - service-account exclusion, root and non-JWT users untouched
  - `--recreate-catalogs` gating
  - lifecycle, bootstrap, reset, and reconciler wiring
- [x] Update `tests/keycloak` (contract: the two clients), `tests/operations/test_reset_lakehouse.py` (new volumes and network), and any test asserting the old usage line or the reconciler Dockerfile.
- [x] Check that test basenames are unique, then run the full suite.

## Step 11 — README and code summary (FR-9)
- [x] README: a "StarRocks SQL" section covering:
  - start, stop, and opt-out
  - `starrocks-login.sh`
  - the catalogs and MV databases, the role matrix, and the platform-admin rights
  - reconcile, `--recreate-catalogs`, the MV-author caveat (SR-18), reset coverage, and resource limits
  - update the "Start the platform" and "Reset the platform" sections and the deferred-integrations text
- [x] `aidlc-docs/current/construction/starrocks-integration/code/code-summary.md`.

## Build and Test changes (2026-11-09, DOC-02)
- [x] `bootstrap-starrocks.py`: read the backend host from the 4.1.7 `IP` column, falling back to `Host` (backend wait timed out live).
- [x] `infra/polaris/bootstrap-product-authorization.py`: add `NAMESPACE_READ_PROPERTIES` to the read set. StarRocks needs `LOAD_NAMESPACE_METADATA`; approved by the user.
- [x] `reconcile-starrocks-users.py`: refuse to change anything while a managed role is missing (`SHOW ROLES`). The scheduled run had raced the product bootstrap.
- [x] SQL TLS, needed because the MySQL OpenID Connect plugin refuses plaintext (approved by the user):
  - `scripts/prepare-starrocks-certificates.py`: local CA, FE certificate (SAN `starrocks-fe`, `localhost`, `127.0.0.1`), PKCS12 keystore, protected password
  - `infra/starrocks/fe-entrypoint.sh`: adds the keystore settings to the tracked `fe.conf`
  - Compose: entrypoint and read-only keystore and password mounts
  - `lakehouse.sh` prepares the certificates before starting StarRocks
  - `starrocks-login.sh` uses `--ssl-mode=VERIFY_IDENTITY` with the CA
- [x] Tests: TLS contracts, the backend column, the Polaris read privilege, and the reconciler role guard.
- [x] README (user request during Build and Test): a "Keycloak sign-in" table that states which account signs in where, and that `platform-admin` cannot sign in to the `master` realm by design.
- [x] JDBC/DBeaver (user request during Build and Test):
  - Verified Connector/J 9.3.0 (SHA-1 checked) logs in with `idTokenFile`, with both `sslMode=REQUIRED` and `VERIFY_IDENTITY` plus a truststore.
  - Added `scripts/starrocks-token.sh` (one-shot or `--watch` refresh, file at mode 0600), a README "DBeaver and other JDBC clients" section, and a contract test.
