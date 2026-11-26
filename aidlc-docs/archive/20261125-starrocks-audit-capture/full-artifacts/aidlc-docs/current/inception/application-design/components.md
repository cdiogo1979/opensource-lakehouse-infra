# Components — StarRocks Audit Capture

Decisions: [application-design-plan.md](../plans/application-design-plan.md) (AD-Q1 vendor the plugin, AD-Q2 record logins); requirements Q1 to Q6.

## U1 `starrocks-audit-capture` (StarRocks component, `infra/starrocks/`)

### C1 Audit capture module — `infra/starrocks/audit_capture.py` (new)
- **Purpose**: everything the platform needs so that StarRocks writes its audit log to a table: the staging database and table, the loader user, and the AuditLoader plugin.
- **Responsibilities**:
  - the staging DDL (4.1 docs columns plus `ScanStats`; expression partition by day; `partition_live_number` 7; replication 1); create if missing, compare columns if present (report, never alter);
  - the loader user `srv-auditloader` (native password, generated once into `.runtime/credentials/srv-auditloader-password`, 0600) with `INSERT` on the staging table only;
  - the plugin: verify the vendored package's SHA-256; render `plugin.conf` (FE `127.0.0.1:8030`, database, table, user, password) into a package under `.runtime/starrocks-audit/` (0600), which `compose.starrocks.yml` mounts read-only into the FE at `/opt/lakehouse/starrocks-audit/` (the package must stay at its install path); the FE plugin folder becomes the named volume `starrocks-fe-plugins` (Functional Design AC-8, AC-9); `INSTALL PLUGIN` when missing; reinstall (`UNINSTALL PLUGIN AuditLoader`, then install) when the rendered package's digest differs from the installed one (version or password change);
  - a status check: plugin state from `SHOW PLUGINS`, the newest staging `timestamp`.
- **Interface**: called from `bootstrap-starrocks.py --runtime-only` (every `scripts/lakehouse.sh start`) and from `scripts/lakehouse.sh status`; pure functions for DDL, column comparison, `plugin.conf` rendering and package digests.

### C2 Vendored plugin — `infra/starrocks/plugins/auditloader-5.0.0.zip` (new) and `infra/starrocks/plugins/auditloader.lock` (new)
- The official package, unchanged, plus a small lock file: version, source URL, SHA-256, license. Updating it is a reviewed commit; the vulnerability scan workflow lists it.

### C3 `fe.conf` and `compose.starrocks.yml` (changed)
- `compose.starrocks.yml`: the read-only `.runtime/starrocks-audit` mount and the `starrocks-fe-plugins` volume (AC-8, AC-9).
- `audit_log_modules=slow_query,query,connection` so connection and disconnection events are logged (effective at the next StarRocks restart).

## U2 `product-platform-sources` (product model and StarRocks grants)

### C4 Product model — `infra/products/data_products.py`, `infra/products/template.yaml` (changed)
- New optional block `platform_sources`, one known source `starrocks_audit`, levels `none` or `read` per role (`owner`, `developer`, `analyst`, `writer`); absent means `none`. Unknown sources, roles or levels fail validation.

### C5 StarRocks grant model — `infra/starrocks/starrocks_common.py`, `infra/starrocks/bootstrap-starrocks.py` (changed)
- `role_grants` adds `SELECT` on `starrocks_audit_db__.starrocks_audit_tbl__` in `default_catalog` for every product role with `read`; `plan_grants` keeps it (declared) or revokes it (no longer declared), like every other product grant.

### C6 Product file — `data-products/audit.yaml` (committed)
- As applied, plus `platform_sources: {starrocks_audit: {owner: read, developer: read, analyst: none, writer: read}}`.

## U3 `workload-starrocks-connection`

### C7 Connection module — `infra/workload-python/python/lakehouse_starrocks.py` (new)
- `connect()` returns a PyMySQL connection over verified TLS: in an Airflow run as the product writer with the run's current token (token login), in Jupyter as the signed-in user with a `getpass` password (LDAP login); host, port, CA and user from the environment the platform sets.

### C8 Workload lock — `infra/workload-python/requirements.in`, `requirements.lock` (changed)
- `PyMySQL` pinned (pure Python); relocked with `scripts/setup/lock-workload-python.sh`; the Spark runtime and Jupyter single-user images rebuilt.

### C9 Airflow run containers — `infra/airflow/lakehouse_dags/factory.py`, `compose.airflow.yml` (changed)
- Mount the StarRocks CA read-only at `/run/certs/starrocks-ca.crt`; set `LAKEHOUSE_STARROCKS_HOST`, `LAKEHOUSE_STARROCKS_PORT`, `LAKEHOUSE_STARROCKS_CA`, `LAKEHOUSE_STARROCKS_USER` (the product's writer).

### C10 Jupyter user servers — `infra/jupyter/hub/lakehouse_spawner.py`, `compose.jupyter.yml` (changed)
- Same CA mount and host, port and CA variables; the user is the JupyterHub user name.

## Docs (all units)
- `docs/reference/starrocks.md`, `docs/reference/data-products.md`, `docs/security.md`, `docs/reference/operations.md`, `docs/reference/workload-python.md`, `docs/components.md`, `docs/reference/limitations.md`.
