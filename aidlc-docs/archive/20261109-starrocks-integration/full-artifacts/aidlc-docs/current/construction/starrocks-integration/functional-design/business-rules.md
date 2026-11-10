# Business Rules — starrocks-integration

## Privileges per access level (FD-Q1: A, mirrors Polaris)
- **SR-1 read** on catalog `c`:
  - `USAGE ON CATALOG c`
  - `SELECT ON ALL TABLES IN ALL DATABASES` of `c`
  - Listing databases follows from USAGE.
- **SR-2 write** on `c`: read plus `CREATE DATABASE ON CATALOG c`, `CREATE TABLE ON ALL DATABASES` of `c`, and `INSERT ON ALL TABLES IN ALL DATABASES` of `c`. No `DROP`, `DELETE`, or `ALTER` on tables or databases.
- **SR-3 manage** on `c`: `ALL` on the catalog, all its databases, and all their tables.
- **SR-4 none**: no grant on `c`. The catalog is not usable, and `SHOW CATALOGS` hides it unless the user has USAGE.
- **SR-5** Exact SQL forms are confirmed against 4.1.7 in Code Generation and Build and Test. If 4.1.7 lacks a form, use the nearest equivalent that grants no more than the level, and record it as a deviation.

## MV databases (Q7: A)
- **SR-6 read**: `USAGE` (or the equivalent) on database `d`, and `SELECT ON ALL MATERIALIZED VIEWS IN DATABASE d`.
- **SR-7 author** (writer): read plus `CREATE MATERIALIZED VIEW ON DATABASE d`, and `ALTER`, `REFRESH`, and `DROP` on all materialized views in `d`.
- **SR-8 manage**: `ALL ON DATABASE d` and all privileges on its materialized views.
- **SR-9** Materialized views read their Iceberg sources with the author's privileges, so writer (write on all catalogs) can build materialized views over any environment.

## Role enforcement (FD-Q3: A)
- **SR-10** The bootstrap creates missing managed roles. For each one it grants missing privileges and revokes privileges the matrix does not cover. A privilege is covered when the matrix grants it, or grants `ALL` on the same object (clarified in Code Generation; StarRocks may report `ALL` as individual privileges). A grant form the bootstrap cannot parse is reported for manual review, never revoked. It reports each revoke by role and privilege, never by data.
- **SR-11** Roles and users that are not managed are never changed.
- **SR-12** `role_platform_admin` has the owner level everywhere. Users in `role-platform-admin` also receive the built-in `user_admin`, `db_admin`, and `cluster_admin` roles (Q6: A). Manual changes those users make to managed roles or users are reverted by the next bootstrap or reconcile.

## Users (FR-7, C1: A, FD-Q2: A)
- **SR-13** The desired users are every Keycloak user in at least one of the five product groups, excluding `service-account-*` users.
- **SR-14** A user's roles are the union of the managed roles for their groups, plus the built-ins under SR-12. Default roles are set to exactly that set, so roles are active at login.
- **SR-15** New users are created `IDENTIFIED WITH authentication_jwt` with these settings:
  - `jwks_url` = `http://keycloak:8080/realms/lakehouse/protocol/openid-connect/certs`
  - `principal_field` = `preferred_username`
  - `required_issuer` = `http://keycloak.localhost:8080/realms/lakehouse`
  - `required_audience` = `starrocks`
- **SR-16** Managed users are JWT users only. A JWT user that is not desired is dropped with `DROP USER`. A non-JWT user with the same name as a desired user is a conflict: it is reported and not changed.
- **SR-17 Safety**: if reading Keycloak memberships fails, or returns no product-group members at all, the reconciler applies nothing and exits non-zero. It never mass-drops users.
- **SR-18** Dropping a user does not drop the materialized views they created. A materialized view whose author was dropped may stop refreshing. Owner or platform admin must re-author it. This is documented in the README.

## Catalogs (FR-4, FD-Q4: A)
- **SR-19** For each environment, if the catalog is absent it is created. If present, its properties from `SHOW CREATE CATALOG` are compared with the desired ones, excluding the credential (masked).
  - Equal: no change.
  - Different: conflict. The bootstrap stops naming only the catalog, and nothing else is changed in that run.
- **SR-20** `--recreate-catalogs` drops and recreates all three catalogs with the current secret. It is used for secret rotation and repair, and loses no data. Role grants on the catalogs are reapplied in the same run.

## Runtime (FR-2)
- **SR-21 Root password**: generated once into `.runtime/credentials/starrocks-root-password`. On a runtime bootstrap:
  - If root logs in with the file password: no change.
  - Else, if root logs in with an empty password (a fresh FE): set it from the file.
  - Else: refuse ("root password unknown; restore the file or reset").
- **SR-22 BE registration**: if `starrocks-be:9050` is absent from the backends, add it. Wait until it is alive or `STARTUP_TIMEOUT_SECONDS` expires.
- **SR-23 Opt-out**: with `STARROCKS_ENABLED=false`:
  - start, status, and stop leave out the StarRocks file
  - the product bootstrap prints one notice per skipped StarRocks step and continues
  - the scheduled reconciler skips StarRocks silently after one notice at start
  - `reconcile-starrocks` exits with a notice
- **SR-24 Enabled but unreachable**: the product bootstrap and on-demand reconcile fail with exit 1. The scheduled reconciler logs and retries on the next cycle.

## Added in Build and Test (2026-11-09)
- **SR-27 TLS**: the FE serves the SQL port with a certificate from the local StarRocks CA. JWT logins always use TLS and verify the server identity, because the client plugin requires it. Password logins are not forced onto TLS (`ssl_force_secure_transport` stays false).
- **SR-28 Reconcile ordering**: the user reconcile changes nothing while any managed role is missing. The scheduled reconciler can run before the product bootstrap.
- **SR-29 Manage limit**: the catalog identity is writer-level, so Polaris refuses table drops made through StarRocks, even for manage-level roles. Owners drop through Spark or Polaris.

## Output and secrets
- **SR-25** SQL goes over stdin, and the client output is captured. Only allowlisted status lines are printed. The root password, `srv-starrocks` secret, and user tokens are never printed or placed in arguments, the environment of other processes, or Compose.
- **SR-26** The login helper:
  - reads the password with no echo
  - writes the token to a mode-0600 temporary file that is removed on exit
  - mounts that file read-only into a pinned MySQL 9.x client container
