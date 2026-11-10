# Code Summary — StarRocks Integration

Intent `20261109-starrocks-integration`, unit `starrocks-integration`. Code generation is complete. Nothing has been run against the live stack yet; that happens in Build and Test.

## Requirements traceability
| Requirement | Change |
|---|---|
| FR-1 Separate Compose file | New `docker-compose.starrocks.yml`: FE and BE `4.1.7` upstream images pinned by digest (arm64), no custom build. Loopback ports 9030 and 8030. Networks `core`, `data-access`, and internal `lakehouse-local_starrocks`. Volumes `starrocks-fe-meta` and `starrocks-be-storage`. Memory limits and health checks. New `infra/starrocks/conf/fe.conf` and `be.conf`, mounted read-only (FE heap 1280 MB). New `.env.example` keys. `docker-compose.deferred.yml` status updated. |
| FR-2 Lifecycle | `scripts/lakehouse.sh` includes the StarRocks file in all Compose commands (including Airflow) unless `STARROCKS_ENABLED=false`, safely for bash 3.2. `start` brings up FE and BE and runs `bootstrap-starrocks.py --runtime-only` (root password, BE registration). `status` and `stop` cover StarRocks. There is a new `reconcile-starrocks [--dry-run]`. `prepare-lakehouse-runtime.py` creates `starrocks-root-password` and `srv-starrocks-client-secret`. `reset-lakehouse.py` covers both volumes and the network. |
| FR-3 Polaris identity | `bootstrap-realm.py` and `realm-contract.json` add the confidential `srv-starrocks` client (service account only, Polaris role mapper), and put its service account in `role-default-writer`. The Polaris reconciler already creates principals for service-account members, so it needed no change. |
| FR-4 Catalogs | `infra/starrocks/bootstrap-starrocks.py` creates `lakehouse`, `lakehouse_uat`, and `lakehouse_dev`. Settings: `iceberg.catalog.type=rest`, `security=oauth2` as `srv-starrocks`, token refresh, vended credentials, and the RustFS endpoint without keys. A conflict stops the run with nothing changed. `--recreate-catalogs` is explicit. It is called from `bootstrap-default-product.sh` after the Spark smoke tables, and reads the three smoke tables. |
| FR-5 Roles | Five managed roles, with grants generated from the matrix and enforced exactly by coverage, as corrected in SR-10 and P4. `ALL` covers expanded privileges, and unparsable grants are reported. Platform admins also get `user_admin`, `db_admin`, and `cluster_admin`. |
| FR-6 MV databases | `default_lh`, `default_lhuat`, and `default_lhdev` in `default_catalog`, with read, author, and manage grants. |
| FR-7 JWT login | `bootstrap-realm.py` adds the public `starrocks` client (password grant, audience mapper `aud=starrocks`). `infra/starrocks/reconcile-starrocks-users.py` creates JWT users per product-group member (issuer, audience, JWKS, `preferred_username`). It grants and revokes roles, sets default roles, and drops users who left. It skips service accounts, never touches root or password users, and aborts on an empty or failed Keycloak read. Scheduled runs use the extended `polaris-group-reconciler` (with `mariadb-client=11.8.9-r0` and a network transport). `scripts/starrocks-login.sh` uses a `mysql:9.7.2` client with the OpenID Connect plugin, which was verified present. |
| FR-8 Legacy retirement | Removed `infra/starrocks/{fe,be,kerberos,ldap-access,sql-bootstrap,preflight}`, `conf/{core-site,hive-site}.xml`, and `scripts/bootstrap-starrocks-sql.sh`. Verified copies are in `code/legacy-starrocks-snapshot/` (17 files) until the closure archive. |
| FR-9 README | New "StarRocks SQL" section (login, catalogs, roles, reconcile, MV caveat). Start, reset, users table, and deferred text updated. |

## Shared module
`infra/starrocks/starrocks_common.py` holds the environments and matrices, quoting, `.env` opt-out detection, and the SQL transports. `DockerExecRunner` uses `docker exec` with `-e MYSQL_PWD` copied from the environment, never as an argument. `NetworkRunner` uses the MariaDB client with `--skip-ssl`. SQL goes over stdin, and output is captured.

## Tests
New files in `tests/starrocks/`:
- `starrocks_strategies.py`
- `test_starrocks_properties.py`: P1–P8; PBT-02/03/07/08/09 with Hypothesis and `print_blob`
- `test_starrocks_compose_contract.py`
- `test_starrocks_bootstrap_contract.py`

Updated: `tests/operations/test_reset_lakehouse.py` and `tests/keycloak/test_bootstrap_users_contract.py`.

Full suite: 213 passed, 1 skipped, plus 2 earlier Airflow drift failures (out of scope). The JupyterHub broker tests pass (10) with `PYTHONPATH`. Compose config across all three files, shell syntax, and Python compilation all pass.

**Found by PBT**: P4 showed that "equal to the matrix" was too strict when `ALL` covers individual privileges. The design (SR-10, P4) and the test now use coverage.

## Risks still to verify live (Build and Test)
1. StarRocks accepts hyphenated JWT usernames.
2. Keycloak accepts `scope=openid` for client credentials, and Polaris accepts the `srv-starrocks` token and principal.
3. Vended credentials plus the configured endpoint reach RustFS.
4. MV refresh works.
5. FE and BE fit in the memory limits.
6. The SQL forms `SHOW ALL AUTHENTICATION`, `SHOW GRANTS FOR ROLE`, and the `GRANT ... ON ALL ... IN ALL DATABASES` grammar on 4.1.7.

Risk 1 from design, the MySQL client's OpenID Connect plugin, is already resolved.

## Build and Test changes
1. **Backend column**: the backend host is read from the 4.1.7 `IP` column.
2. **Polaris read privilege**: the read set gains `NAMESPACE_READ_PROPERTIES`, approved by the user.
3. **Reconciler role guard**: the reconciler refuses to change anything until the managed roles exist.
4. **SQL TLS**, approved by the user: `scripts/prepare-starrocks-certificates.py`, `infra/starrocks/fe-entrypoint.sh`, the Compose entrypoint and mounts, the `lakehouse.sh` call, and verified TLS in `starrocks-login.sh`.

Tests after these changes: 219 passed, 1 skipped, and the 2 earlier Airflow drift failures.
5. **JDBC token helper**, requested by the user: `scripts/starrocks-token.sh`, for DBeaver and other JDBC clients through Connector/J 9.1+ `idTokenFile`. Verified live, with a README section.
