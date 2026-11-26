# StarRocks

Reference: interactive SQL over the Iceberg tables. Back to the [README](../../README.md). Step-by-step for analysts: the [data analyst journey](../journeys/data-analyst.md).

StarRocks (one FE and one BE) reads and writes the three Polaris catalogs.
- **Memory**: `STARROCKS_FE_MEMORY_LIMIT` (default `2g`) and `STARROCKS_BE_MEMORY_LIMIT` (default `4g`).
- **Ports**: SQL `9030` and HTTP `8030`, both on loopback.

## Log in

Use your username and password, the same as for Keycloak sign-in. StarRocks checks the password against the LDAP directory, and **every connection must use TLS** (plain-text connections are refused):

```sh
./scripts/clients/starrocks-login.sh joe-developer                  # asks for the password
./scripts/clients/starrocks-login.sh maria-owner -e "SHOW CATALOGS"
```

Product writers (`srv-<product>-writer`) don't log in with a password: their StarRocks users use **token login** (`authentication_jwt`, Keycloak's keys and issuer, the token's `preferred_username`), so only the platform's materialized-view deploy, holding a broker-issued writer token, logs in as them. The reconciler keeps writers on token login and everyone else on LDAP, switching a user in place (grants and owned views kept) if it is on the wrong one. The emergency admin account is `root`, with the password in `.runtime/credentials/starrocks-root-password`. Avoid it for normal work, because it bypasses the role model.

## DBeaver and other JDBC clients

1. **In DBeaver**: create a **StarRocks** connection to host `127.0.0.1`, port `9030`, with your username and password; on the **SSL** tab, enable SSL (or set the driver property `sslMode=REQUIRED`).
2. **Other JDBC and BI clients** (MySQL Connector/J, or ODBC): username and password, with `sslMode=REQUIRED`. The client sends the password with the MySQL clear-text authentication plugin, which these drivers use only over TLS.
3. **Browsing catalogs**:
   - Leave the connection's default database empty: the session starts in `default_catalog`. Its databases `default_lh`, `default_lhuat` and `default_lhdev` are the products' **materialized-view databases**, not the Iceberg namespaces; DBeaver's MySQL-style tree may show them under whichever node you opened.
   - The Iceberg tables are in the catalogs `lakehouse` (prod), `lakehouse_uat` and `lakehouse_dev`, one database per product namespace. Browse them, or use fully qualified names: `SHOW TABLES FROM lakehouse_dev.default_lhdev;`, `SELECT * FROM lakehouse_uat.default_lhuat.tpch_region;`.
   - Table lists come from each catalog's `information_schema`. Every product role may read it where it has catalog access, and its rows show only the databases and tables your roles grant, so other products' tables stay hidden.
   - DBeaver may show one catalog's databases under another catalog's node: refresh the node (F5), or use one connection per catalog (for example `jdbc:mysql://127.0.0.1:9030/lakehouse.default_lh`).

## Verify the certificate

Optional:
- Import the CA:

  ```sh
  keytool -importcert -noprompt -alias starrocks-ca -file .runtime/container-mounts/starrocks-ca.crt \
    -keystore ~/.starrocks/truststore.p12 -storetype PKCS12 -storepass <choose-one>
  ```

- Set `sslMode=VERIFY_IDENTITY`, `trustCertificateKeyStoreUrl=file:/Users/<you>/.starrocks/truststore.p12`, and `trustCertificateKeyStorePassword=<choose-one>`.
- Import the CA again after a reset.

## Catalogs and roles

- **Catalogs**: `lakehouse`, `lakehouse_uat`, and `lakehouse_dev` reach Polaris as the service account `srv-starrocks` (writer level) and use Polaris-issued storage credentials.
- **Roles**: StarRocks roles are named after the groups (`role_default_owner`, `role_sales_owner`, and so on) and grant the same access as Polaris, on the product's database in each catalog only:
  - read is `SELECT`
  - write adds `CREATE TABLE` and `INSERT`
  - manage is everything except dropping Iceberg tables (see [Known limitations](limitations.md))
  - `role_platform_admin` manages the whole catalogs
  - every product role with access to a catalog also reads that catalog's `information_schema` (filtered by its own privileges), which SQL clients use to list tables
- **MV databases** (one per product and environment, levels from the file; for `default`):
  - the writer creates, refreshes, and drops materialized views in all three; in UAT and production the platform deploys the product repository's declared views as the writer ([promotion](data-products.md#promoting-materialized-views))
  - developers do the same in dev, and read production and UAT
  - analysts read production
  - owners and platform admins manage them
  - materialized views accelerate queries for everyone through query rewrite ([Data products](data-products.md#materialized-views-and-query-acceleration))
- **Enforcement**: the bootstrap revokes and reports any privilege added to these roles by hand.

## Users

Every Keycloak user in a product group has a StarRocks user with exactly their groups' roles.
- **Sync**: in the product bootstrap, every five minutes, or on demand with `./scripts/lakehouse.sh reconcile-starrocks [--dry-run]`.
- **After a StarRocks restart**: the FE forgets its LDAP bind pattern and password logins fail ("empty password is not allowed for simple authentication"). Each five-minute cycle first sets it again, independently of Keycloak and the product files, so logins recover within five minutes; to fix it at once, run `python3 infra/starrocks/reconcile-starrocks-users.py --bind-pattern-only`.
- **Health**: the scheduled sync runs the repository's current code (mounted read-only). Its container is `unhealthy` when no cycle fully succeeded for two intervals plus a minute; `./scripts/lakehouse.sh status` shows it as `reconciler`, and `docker logs lakehouse-local-polaris-group-reconciler-1` says why.
- **Leaving a group**: removing someone from all groups drops their StarRocks user.
- **Safety**: if Keycloak cannot be read, nothing changes.
- **Secret rotation**: to rotate the `srv-starrocks` secret, or to repair the catalogs, run `python3 infra/starrocks/bootstrap-starrocks.py --recreate-catalogs`. Data is untouched.

## Audit capture

StarRocks writes every audit event (queries, slow queries, logins and logouts) to the staging table `starrocks_audit_db__.starrocks_audit_tbl__`, through its AuditLoader plugin. The audit data product pulls it hourly into its Iceberg tables.

- **What `start` sets up** (`infra/starrocks/audit_capture.py`, run by `bootstrap-starrocks.py --runtime-only`; safe to repeat):
  - the staging table: the AuditLoader columns, one partition per day of `timestamp` (UTC), **7 days kept** (`partition_live_number`); an existing table is checked, never altered;
  - the loader user `srv-auditloader`: a native StarRocks password generated once into `.runtime/credentials/srv-auditloader-password`, and only `INSERT` on the staging table;
  - the plugin: the package vendored at `infra/starrocks/plugins/auditloader-5.0.0.zip` is checked against `auditloader.lock` (SHA-256), its `plugin.conf` gets the loader's user and password, and the result (`.runtime/starrocks-audit/auditloader.zip`, mounted read-only into the FE) is installed; it is reinstalled only when it changes. The FE keeps installed plugins in the volume `starrocks-fe-plugins`.
- **Login events** need `audit_log_modules = slow_query,query,connection` in `infra/starrocks/conf/fe.conf` (set); `queryType` is then `query`, `slow_query`, `connection` or `disconnection`. A change of `fe.conf` takes effect at the next StarRocks restart.
- **Who can read it**: only product roles whose product file declares `platform_sources.starrocks_audit: read` ([Data products](data-products.md#platform-sources)), today the audit product's owners, developers and writer. Everyone else, analysts of the audit product included, is refused. The table holds every statement of every user: treat it as sensitive.
- **Status**: `./scripts/lakehouse.sh status` prints `audit capture: plugin INSTALLED; newest row <n> min ago`.
- **If it fails**: the start continues and prints `ERROR: StarRocks audit capture not set up: ...`; a package that doesn't match its checksum is never installed. Fix the cause and run `python3 infra/starrocks/audit_capture.py` (or `start` again).
- **From workload code**: `lakehouse_starrocks.connect()` ([Workload Python](workload-python.md#starrocks-connections)).
- **Updating the plugin**: download the new package from `https://releases.starrocks.io/resources/auditloader.zip`, check `plugin.properties` (version, supported StarRocks versions), replace the vendored file, and update every field of `auditloader.lock` in the same reviewed commit; the next `start` reinstalls it.
