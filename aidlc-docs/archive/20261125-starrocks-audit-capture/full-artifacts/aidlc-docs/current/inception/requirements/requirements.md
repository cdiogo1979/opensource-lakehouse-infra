# Requirements — StarRocks Audit Capture

Intent `20261125-starrocks-audit-capture`. Depth: **Standard**. Answers: [requirement-verification-questions.md](requirement-verification-questions.md) (Q1–Q6 A; Security Yes; Resiliency No; PBT Partial).

## Intent analysis
| Item | Value |
|---|---|
| User request | "go ahead with the platform intent" (the paired platform intent of the audit data product) |
| Consumer | `opensource-lakehouse-audit-dp` intent `20261125-starrocks-query-audit`: its bronze task reads `SELECT * FROM starrocks_audit_db__.starrocks_audit_tbl__` through `lakehouse_starrocks.connect()`, in Airflow (prod, uat) as `srv-audit-writer` and in Jupyter (dev) as the signed-in owner or developer |
| Request type | New feature (platform capability) |
| Scope | Multiple components: StarRocks bootstrap, product model and grants, workload Python set, Airflow DAG factory, JupyterHub spawner, docs |
| Complexity | Moderate |

## Functional requirements

### FR-1 Staging table
- FR-1.1 Database `starrocks_audit_db__` and table `starrocks_audit_tbl__` with the column set the pinned AuditLoader version writes, partitioned by day on `timestamp` with dynamic partitions that keep **7 days** (older partitions dropped by StarRocks), replication 1 (single backend).
- FR-1.2 Created if missing and checked on every StarRocks bootstrap (Q5:A); an existing table with other columns is reported, not altered.
- FR-1.3 Login and logout events are recorded: `fe.conf` sets `audit_log_modules=slow_query,query,connection` (rows with `queryType` `connection` and `disconnection`); it takes effect at the next StarRocks restart (Application Design AD-Q2:A).

### FR-2 Loader identity
- FR-2.1 A local StarRocks user `srv-auditloader` with a native password (Q1:A), generated once into `.runtime/credentials/srv-auditloader-password` (mode 0600) and never printed, logged, or written to the repository.
- FR-2.2 Its only privilege: `INSERT` on `starrocks_audit_db__.starrocks_audit_tbl__`. It is not a Keycloak or LDAP user; the user reconciler leaves it alone (it only manages LDAP and JWT users).

### FR-3 AuditLoader plugin
- FR-3.1 The official AuditLoader package (`https://releases.starrocks.io/resources/auditloader.zip`, version 5.0.0, "for 3.3.11+", Apache-2.0) is **vendored** in the repository with its SHA-256 and source URL, and verified before every install; a checksum mismatch stops the bootstrap. (Application Design AD-Q1:A, 2026-11-25: the GitHub repository has no versioned releases, superseding Q2:A's download of a pinned release.)
- FR-3.2 Its `plugin.conf` is rendered at bootstrap (FE address, database, table, `srv-auditloader` and its password) into a package under `.runtime/` (mode 0600), copied into the FE container, and installed with `INSTALL PLUGIN` if it is not installed; a changed package (new version or password) is reinstalled (uninstall, install).
- FR-3.3 Runs on every `scripts/lakehouse.sh start` with the StarRocks module, idempotently (Q5:A); `scripts/lakehouse.sh status` reports the plugin's state and the newest staging row's age.

### FR-4 Read access, modeled in the product file (Q3:A)
- FR-4.1 New optional product-file block `platform_sources`, with one source `starrocks_audit` mapping each role (`owner`, `developer`, `analyst`, `writer`) to `none` or `read`; absent means `none` for every role.
- FR-4.2 `read` grants `SELECT` on `starrocks_audit_db__.starrocks_audit_tbl__` (and `USAGE`-level access needed to reach it, if any) to that product role in StarRocks; the grant is part of the declared grants, so the bootstrap keeps it and revokes it when the block or level is removed.
- FR-4.3 `data-products/audit.yaml` declares `platform_sources: {starrocks_audit: {owner: read, developer: read, analyst: none, writer: read}}`; no other product declares it. The product validator refuses unknown sources and levels.

### FR-5 `lakehouse_starrocks.connect()`
- FR-5.1 A module `lakehouse_starrocks` in the workload Python set (beside `lakehouse_spark`), in the Spark runtime and Jupyter images, returning a PyMySQL DB-API connection to StarRocks over TLS verified with the StarRocks CA, `autocommit`, with connect and read timeouts.
- FR-5.2 **Airflow runs**: logs in as the run's product writer (`srv-<product>-writer`) with the run's current access token (the initial token, renewed through the token broker with the run handle and capability when close to expiry), using StarRocks' token login (`authentication_openid_connect_client`), as `mv_deploy.connect` does.
- FR-5.3 **Jupyter**: logs in as the signed-in user (JupyterHub user name) with their StarRocks (LDAP) password, asked with `getpass` every time a connection is opened (Q4:A); never stored, logged or put in the environment.
- FR-5.4 Host, port and CA path come from platform-set environment variables, never from product repositories; outside an Airflow run or Jupyter server it raises a clear error.
- FR-5.5 PyMySQL is added, pinned, to the workload Python set (`infra/workload-python/requirements.in`, re-locked).

### FR-6 Reachability
- FR-6.1 Airflow Spark run containers and Jupyter user servers get the StarRocks CA mounted read-only and the StarRocks host and port in their environment; both already reach `starrocks-fe:9030` through the `data-access` network (to be confirmed by a check).

### FR-7 Repository, docs and knowledge (Q6:A)
- FR-7.1 Commit `data-products/audit.yaml` (as applied, plus the `platform_sources` block).
- FR-7.2 Update the docs: StarRocks reference (audit capture, the loader user, the staging table), data products reference (`platform_sources`), security (the new credential, the audit log's sensitivity), operations (plugin reinstall, password rotation), workload Python (the new module and PyMySQL), components and limitations; canonical knowledge at closure.

## Non-functional requirements
- NFR-1 **Security** (Security Baseline enabled):
  - least privilege: the loader writes to one table only; readers get `SELECT` on one table only, through declared product roles; the audit product's analysts and every other product get nothing (SECURITY-06, -08);
  - credentials: generated, 0600, never in the repository, logs or images; `plugin.conf` exists only in `.runtime/` and inside the FE container (SECURITY-12);
  - supply chain and integrity: the plugin is pinned by version and SHA-256 from the official repository; PyMySQL pinned in the lock (SECURITY-10, -13);
  - transport: the helper uses TLS with certificate verification (SECURITY-01); the plugin's stream load stays inside the FE container (FE to its own HTTP port) and is documented as such;
  - logging: no token, password or `plugin.conf` content in logs (SECURITY-03);
  - misuse cases: another product's writer reading the audit log; an analyst reading full SQL; a tampered plugin download; a leaked loader password (it can only insert into the staging table).
- NFR-2 **Idempotence**: every bootstrap step can run on every start without changing a correct state.
- NFR-3 **Compatibility**: existing products, the MV deploy and people's StarRocks logins are unchanged; products without `platform_sources` get no new grant.
- NFR-4 **Testing**: unit tests for the pure parts (product-file parsing and validation, grant planning, `plugin.conf` rendering, connection-parameter selection, token renewal decision), example-based plus Hypothesis properties for pure functions and round trips (PBT partial: PBT-02, -03, -07, -08, -09); live checks on the running platform.

## Probes (to settle in Application Design or Build and Test)
- P-1 The AuditLoader release compatible with 4.1.7, its table DDL and columns, whether it records connection events, and the FE time zone (the audit product's bronze expects UTC `timestamp`).
- P-2 Whether the token login works for the writer from a Spark run container exactly as from the Airflow scheduler (same issuer and audience).
- P-3 Network reachability of `starrocks-fe:9030` from a Spark run container and a Jupyter server.

## Extensions
| Extension | Decision |
|---|---|
| Security Baseline | Yes (blocking) |
| Resiliency Baseline | No |
| Property-Based Testing | Partial |
