# Functional Design — StarRocks SQL Access

This is the current functional design of the StarRocks component. For architecture, see [`../application-design.md`](../application-design.md); for the product access model, see [`lakehouse-product-access.md`](lakehouse-product-access.md). History is in the [StarRocks Integration](../../../archive/20261109-starrocks-integration/intent-summary.md) and [Data Product and User Scripts](../../../archive/20261109-data-product-and-user-scripts/intent-summary.md) intent archives.

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
- **Managed users**: JWT users only, created with `IDENTIFIED WITH authentication_jwt`:
  - `jwks_url` = Keycloak certs at `keycloak:8080`
  - `principal_field` = `preferred_username`
  - `required_issuer` = `http://keycloak.localhost:8080/realms/lakehouse`
  - `required_audience` = `starrocks`
- **Apply order**: create, grant, revoke, `SET DEFAULT ROLE ALL`, then drop users that left every product group. A non-JWT user with a desired name is a conflict: it is reported and left unchanged. `root` and built-in users are never managed.
- **Safety**:
  - If Keycloak is unreadable or returns no product-group members, nothing changes and the exit code is non-zero.
  - If any managed role is missing, nothing changes. This happens when the scheduled run precedes the product bootstrap.
  - **Except** for products being removed: a product group missing from Keycloak counts as empty, and its roles are no longer required.
  - If a product file is invalid, nothing changes.
  - The scheduled image ships the product model with pinned PyYAML and reads `data-products/` from a read-only mount.
- **When it runs**: in the product bootstrap; on demand with `lakehouse.sh reconcile-starrocks` (the `docker exec` transport); and on the scheduled `polaris-group-reconciler` cycle (network transport, with the MariaDB client using `--skip-ssl`, and skipped when StarRocks is disabled).
- **MV authorship**: a dropped user's materialized views may stop refreshing; an owner or platform admin must re-create them.

## Login
- **TLS**: the FE serves the SQL port with a certificate from a local CA (SAN `starrocks-fe`, `localhost`, `127.0.0.1`), made by `scripts/setup/prepare-starrocks-certificates.py`. Token logins always use TLS, because the client plugin refuses plaintext. Password logins (root) are not forced onto TLS.
- **Command line**: `scripts/clients/starrocks-login.sh <user>` gets a password-grant token from the `starrocks` client and connects with a `mysql:9.7.2` container, `--default-auth=authentication_openid_connect_client`, and `--ssl-mode=VERIFY_IDENTITY`.
- **JDBC and DBeaver**: DBeaver's StarRocks connection type needs only `idTokenFile` (verified by the user). Other JDBC clients use Connector/J 9.1 or later with `idTokenFile`, `defaultAuthenticationPlugin=authentication_openid_connect_client`, and `sslMode=REQUIRED` (or `VERIFY_IDENTITY` with a truststore of the StarRocks CA).
  - **Token freshness**: tokens last 300 seconds and are checked only when a connection opens. `scripts/clients/starrocks-token.sh --watch` keeps the token file fresh with the refresh token.
- **Secret handling**: the password is read without echo or from a file, and sent on stdin. Token files are mode 0600 and written atomically. Nothing secret is printed or put in arguments. Host-side SQL passes the root password through `MYSQL_PWD`, copied by `docker exec -e`, never as an argument.

## Opt-out and failure behavior
- **`STARROCKS_ENABLED=false`** (environment or `.env`; case-insensitive): start, status, and stop leave out the StarRocks file. Both scripts print a notice and exit 0. The scheduled cycle skips StarRocks.
- **Enabled but unreachable**: the product bootstrap and on-demand reconcile fail with exit 1. The scheduled cycle logs the failure and retries.
- **Keycloak unavailable**: new logins fail (no token, no JWKS). Open sessions continue. Catalog token renewal fails until Keycloak returns.

## Testable properties (Hypothesis; partial PBT mode)
- P1: catalog properties round-trip through render and parse.
- P2: the JWT identity clause round-trips.
- P3: grants equal the matrix for each role and environment.
- P4: applying a grant plan covers the matrix and leaves unmanaged roles alone.
- P5: desired users follow groups and exclude service accounts.
- P6: applying a user plan converges, and password users are never changed.
- P7: the catalog plan ignores the credential.
- P8 (advisory): planning against the desired state is empty.

The tests are in `tests/starrocks/`.

## Known limits and follow-ups
- A new product becomes readable through StarRocks within about five minutes. The catalogs cache the `srv-starrocks` token, and its new writer-group role arrives at the next token renewal (Keycloak access tokens last 300 s).
- Owner and platform-admin cannot drop Iceberg tables through StarRocks (accepted).
- User tokens are short-lived. Tools with scheduled refresh, such as Power BI, need the planned long-lived, per-data-product BI token clients (follow-up intent). Power BI needs ODBC with a token file, which is not yet verified.
- Probe data files from Build and Test remain in the buckets, because Polaris refuses purge.
