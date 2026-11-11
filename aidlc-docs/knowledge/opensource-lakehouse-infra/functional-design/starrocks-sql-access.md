# Functional Design — StarRocks SQL Access

This is the current functional design of the StarRocks component. For architecture, see [`../application-design.md`](../application-design.md); for the product access model, see [`lakehouse-product-access.md`](lakehouse-product-access.md). History is in the [StarRocks Integration](../../../archive/20261109-starrocks-integration/intent-summary.md) [Data Product and User Scripts](../../../archive/20261109-data-product-and-user-scripts/intent-summary.md), [StarRocks LDAP Login](../../../archive/20261109-starrocks-ldap-login/intent-summary.md), and [StarRocks Metadata Access](../../../archive/20261111-starrocks-metadata-access/intent-summary.md) intent archives.

## Responsibility
StarRocks 4.1.7 gives people and tools interactive SQL over every data product's Iceberg tables in Polaris, with access identical to each product's roles. It also hosts materialized views in internal databases. It owns no source data: tables live in Polaris and RustFS.

## Catalogs and databases
The three external catalogs are shared by all products. Each product's namespaces appear as databases in them, and each product has its own MV databases in `default_catalog`. For `default`:

| Environment | External catalog (Iceberg REST, Polaris warehouse) | Database (namespace) | Internal MV database (`default_catalog`) |
|---|---|---|---|
| prod | `lakehouse` | `default_lh` | `default_lh` |
| uat | `lakehouse_uat` | `default_lhuat` | `default_lhuat` |
| dev | `lakehouse_dev` | `default_lhdev` | `default_lhdev` |

Catalog properties:
- `type=iceberg`, `iceberg.catalog.type=rest`, and `iceberg.catalog.uri=http://polaris:8181/api/catalog`, with the warehouse set to the catalog name.
- `iceberg.catalog.security=oauth2`, with `oauth2.credential=srv-starrocks:<secret>`, `oauth2.server-uri` set to the Keycloak token endpoint at `keycloak:8080`, `oauth2.scope=openid`, and `oauth2.token-refresh-enabled=true`.
- `iceberg.catalog.vended-credentials-enabled=true`.
- `aws.s3.endpoint=http://rustfs:9000`, path-style access, and region `us-east-1`. No storage keys.

## Access model (mirrors Polaris)
- **Roles**: each product group maps to the role with underscores (`role-sales-owner` → `role_sales_owner`). Its levels come from the product file's `access` (catalog databases) and `materialized_views` (MV databases), on that product's databases only.
- **Default matrix** (`data-products/default.yaml`, also the template):

  | Role | prod | uat | dev | MV databases (prod / uat / dev) |
  |---|---|---|---|---|
  | `role_default_owner` | manage | manage | manage | manage / manage / manage |
  | `role_default_developer` | read | read | write | read / read / author |
  | `role_default_analyst` | read | none | none | read / none / none |
  | `role_default_writer` | write | write | write | author / author / author |
  | `role_platform_admin` | manage (catalog-wide) | manage (catalog-wide) | manage (catalog-wide) | manage in every product |

- **Levels**, in catalog `c` for the product database `d`:
  - **every level but `none`** also gets `SELECT ON ALL TABLES IN DATABASE information_schema` in `c` (see "Catalog metadata" below)
  - **read**: `USAGE ON CATALOG c`, `SELECT ON ALL TABLES IN DATABASE d`
  - **write**: read, plus `INSERT ON ALL TABLES IN DATABASE d` and `CREATE TABLE ON DATABASE d`. No drop, delete, alter, or `CREATE DATABASE`.
  - **manage**: `USAGE ON CATALOG c`, `ALL ON DATABASE d`, `ALL ON ALL TABLES IN DATABASE d`
  - **platform admin**: `ALL` on the catalog, all databases, and all tables
- **MV levels**:
  - **MV read**: `SELECT ON ALL MATERIALIZED VIEWS IN DATABASE d`
  - **MV author**: MV read plus `CREATE MATERIALIZED VIEW ON DATABASE d`, and `ALTER`, `REFRESH`, and `DROP` on its materialized views
  - **MV manage**: `ALL` on the database and its materialized views
- **Built-ins**: platform admins also get `user_admin`, `db_admin`, and `cluster_admin`.
- **Visibility**: a user sees only the databases they have privileges on.
- **Catalog metadata** (since 2026-11-11): StarRocks 4.1.7 checks `SELECT` on an external catalog's `information_schema` tables, which SQL clients (DBeaver's MySQL driver) query to list tables and columns; without it, product users got error 5203 ("SELECT privilege(s) on TABLE tables") although `SHOW TABLES` and queries worked. Every product role with `USAGE` on a catalog therefore holds `SELECT ON ALL TABLES IN DATABASE information_schema` there (`METADATA_DATABASE` in the bootstrap). The rows are filtered by the user's own privileges: a role with only this grant sees no table of any product (probed, and verified in Build and Test), so the shared catalogs reveal nothing across products. Platform admins already hold `ALL` on the catalogs.
- **Polaris is the outer bound.** The shared catalog identity `srv-starrocks` is in every product's writer group, so drops through StarRocks are refused by Polaris, even for manage-level roles. Polaris's read set includes `NAMESPACE_READ_PROPERTIES`, because StarRocks loads namespace metadata when it opens a database.
- **2026-11-09 migration of `default`**: catalog-wide grants were replaced by database-scoped ones. Writers and owners lost `CREATE DATABASE` on the catalogs, and developers gained MV authoring in dev (CR-2).

## Role enforcement (`infra/starrocks/bootstrap-starrocks.py`)
- It creates missing managed roles and every product's MV databases, and grants every privilege of the product files again. `GRANT` is idempotent, and StarRocks reports `ALL` as individual privileges, so some grants are reissued on each run (27 for `default`).
- Additions run before revocations.
- **Database-scoped forms**: `ALL TABLES IN DATABASE d` is parsed and rendered alongside the existing forms.
- **Options**: `--product FILE` validates a file (the roles always follow every file). `--inventory` prints a product's MV-database object counts. `--remove [--purge-data]` drops a product's MV databases (`FORCE`; refused while they hold objects without purge) and roles, then converges the platform admin over the remaining products.
- It revokes, and reports by name, managed-role privileges the matrix does not cover. A privilege is covered when it is desired, or when `ALL` is desired on the same object.
- A grant form it cannot parse is reported for manual review and never revoked. Roles and users it does not manage are never changed.
- Catalogs: a missing catalog is created. An existing one is compared without its masked credential: equal means no change, and a difference stops the run with nothing changed, naming only the catalog. `--recreate-catalogs` drops and recreates all three, for secret rotation or repair, with no data loss.
- `--runtime-only` (core start):
  - **Root password**: kept if root logs in with the file password. Set from the file if root logs in with an empty one (a fresh FE). Otherwise it refuses.
  - **Backend**: registers `starrocks-be:9050` and waits until it is alive. In 4.1.7 the host is read from the `IP` column.

## Users (`infra/starrocks/reconcile-starrocks-users.py`)
- **Desired users**: every enabled Keycloak user in at least one group of any product file, except `service-account-*` users. Roles are the union of their groups' roles, plus the built-ins for platform admins.
- **Managed users and login methods**: people log in with LDAP (`IDENTIFIED WITH authentication_ldap_simple`); each product's writer user (`writer_user.username`) logs in with its Keycloak access token (`IDENTIFIED WITH authentication_jwt AS '{"jwks_url": "http://keycloak:8080/realms/lakehouse/protocol/openid-connect/certs", "principal_field": "preferred_username", "required_issuer": "http://keycloak.localhost:8080/realms/lakehouse"}'`; `STARROCKS_JWT_JWKS_URL`, `KEYCLOAK_ISSUER` override). A user on the wrong method is **switched in place** with `ALTER USER … IDENTIFIED WITH …`, which keeps its grants and the materialized views it owns. Both plugins count as managed for drops.
- **Apply order**: create, switch, grant, revoke, `SET DEFAULT ROLE ALL`, then drop managed users who left every product group. A native-password user with a desired name is a conflict: it is reported and left unchanged. `root` and built-in users are never managed.
- **Bind pattern**: after its safety checks, every run re-applies the LDAP bind pattern if the FE lost it (an FE restart resets this runtime setting). `--bind-pattern-only` does only that, with the root login and no Keycloak read or product validation; the scheduled cycle runs it first (since 2026-11-11), so logins recover even while the user sync is refused.
- **Safety**:
  - If Keycloak is unreadable or returns no product-group members, nothing changes and the exit code is non-zero.
  - If any managed role is missing, nothing changes. This happens when the scheduled run precedes the product bootstrap.
  - **Except** for products being removed: a product group missing from Keycloak counts as empty, and its roles are no longer required.
  - If a product file is invalid, nothing changes.
  - The scheduled image provides Python, pinned PyYAML and the MariaDB client; the product model, both reconcile scripts, `starrocks_common.py` and `run.sh` are mounted read-only from the repository (since 2026-11-11: a baked-in copy of an older model had refused every cycle with `unknown keys: repo`), and `data-products/` likewise.
- **When it runs**: in the product bootstrap; on demand with `lakehouse.sh reconcile-starrocks` (the `docker exec` transport); and on the scheduled `polaris-group-reconciler` cycle (network transport: the MariaDB client connects with `--ssl --ssl-verify-server-cert` and the StarRocks CA mounted at `/run/certs/starrocks-ca.crt`; skipped when StarRocks is disabled).
- **MV authorship**: a dropped user's materialized views may stop refreshing; an owner or platform admin must re-create them.

## Login
- **Method**: people log in with their own username and LDAP password; product writers only with a Keycloak token (the materialized-view deploy; see `materialized-view-promotion.md`). People use the same password as for Keycloak. One StarRocks user has exactly one login method (probed), so the former token login was retired: the `starrocks` Keycloak client and `scripts/clients/starrocks-token.sh` are gone.
- **TLS**: the FE serves the SQL port with a certificate from a local CA (SAN `starrocks-fe`, `localhost`, `127.0.0.1`), made by `scripts/setup/prepare-starrocks-certificates.py`. `ssl_force_secure_transport = true` refuses every plain-text connection, root included. This matters because the client sends the password in clear text inside the TLS session (`mysql_clear_password`).
- **Password check**: the FE binds to LDAP over LDAPS (`ldap:636`, `ssl_conn_allow_insecure = false`, trust store `/run/certs/ldap-ca.crt`) as `uid=${USER},ou=people,dc=lakehouse,dc=local`, so StarRocks holds no LDAP credential.
  - **Where the pattern is set**: it is a runtime setting. `fe.conf` would expand `${USER}` as an environment variable ("no such env variable: USER") and the FE would refuse to start, so `bootstrap-starrocks.py --runtime-only` sets it at every start and the user sync re-applies it.
- **Command line**: `scripts/clients/starrocks-login.sh [--password-file FILE] <user>` uses a `mysql:9.7.2` container with `--enable-cleartext-plugin` and `--ssl-mode=VERIFY_IDENTITY` against the StarRocks CA. Service users use their password file under `.runtime/credentials/`.
- **JDBC, DBeaver, and BI tools**: username and password with `sslMode=REQUIRED`, or `VERIFY_IDENTITY` with a truststore of the StarRocks CA. Connector/J 9.3.0 was verified with both; `DISABLED` is refused.
- **Browsing in SQL clients**: leave the connection's default database empty (the session starts in `default_catalog`, whose `default_lh`, `default_lhuat` and `default_lhdev` are the materialized-view databases, not the Iceberg namespaces; DBeaver may draw them under whichever node is open). Iceberg tables are browsed in the catalogs or named `catalog.database.table`. Users reconnect after a grant change, because roles are read at login.
- **Secret handling**: the password is read without echo or from a file, and reaches the client container only through `MYSQL_PWD` (copied by `docker run -e`). Nothing secret is printed or put in arguments. Host-side SQL passes the root password through `MYSQL_PWD`, copied by `docker exec -e`, never as an argument.

## Opt-out and failure behavior
- **`STARROCKS_ENABLED=false`** (environment or `.env`; case-insensitive): start, status, and stop leave out the StarRocks file. Both scripts print a notice and exit 0. The scheduled cycle skips StarRocks.
- **Enabled but unreachable**: the product bootstrap and on-demand reconcile fail with exit 1. The scheduled cycle logs the failure and retries.
- **LDAP unavailable**: new password logins fail (LDAP bind); open sessions continue.
- **Keycloak unavailable**: SQL logins keep working (they depend on LDAP only), but catalog token renewal to Polaris fails until Keycloak returns.
- **FE restarted outside `lakehouse.sh start`**: password logins fail ("empty password is not allowed for simple authentication") until the next scheduled cycle's bind-pattern step (at most one interval, 300 s by default), or `reconcile-starrocks-users.py --bind-pattern-only` on the host at once.

## Testable properties (Hypothesis; partial PBT mode)
- P1: catalog properties round-trip through render and parse.
- P2: JWT users are switched in place, never recreated or dropped while desired.
- P3: grants equal the matrix for each role and environment.
- P4: applying a grant plan covers the matrix and leaves unmanaged roles alone.
- P5: desired users follow groups and exclude service accounts.
- P6: applying a user plan leaves every desired user with its login method (token for writers, LDAP for people) and exactly its roles; native-password users are never changed (P2b re-plans to no switch).
- P7: the catalog plan ignores the credential.
- P8 (advisory): planning against the desired state is empty.
- P9: a role holds the `information_schema` metadata grant on a catalog exactly when it holds `USAGE` there, only as `SELECT`, never on the database itself.

The tests are in `tests/starrocks/`.

## Known limits and follow-ups
- **Writers have no password login** (one login method per user, probe P1 of mv-promotion): use an owner account to inspect deployed views.
- **Verified 2026-11-11 (MV promotion)**: the reconciler switched `srv-default-writer` to token login in place; the deploy logged in as it with a broker token over TLS.
- **Verified 2026-11-11 (metadata access)**: 10 metadata grants applied for `default`, then converged; a developer lists tables in all three catalogs, an analyst in prod only (uat and dev refused); a role with only the metadata grant sees nothing of `default`; the user confirmed DBeaver.
- **Resolved 2026-11-11**: a password login stayed broken after an FE restart because the scheduled reconciler refused every cycle (stale baked-in product model). The reconciler now runs mounted current code, restores the bind pattern first, and its container healthcheck reports unhealthy when no cycle fully succeeded within two intervals plus a minute (`lakehouse.sh status` shows `reconciler`).
- A new product becomes readable through StarRocks within about five minutes. The catalogs cache the `srv-starrocks` token, and its new writer-group role arrives at the next token renewal (Keycloak access tokens last 300 s).
- Owner and platform-admin cannot drop Iceberg tables through StarRocks (accepted).
- Reporting tools such as Power BI can now connect with a username and password over TLS (ODBC or JDBC). The user confirmed DBeaver and BI-tool logins on 2026-11-09.
- Probe data files from Build and Test (`sr_bt_*`) were left in the buckets because Polaris refuses purge; they were deleted directly from RustFS on 2026-11-09.
