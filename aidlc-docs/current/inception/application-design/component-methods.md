# Component Methods — StarRocks Audit Capture

Signatures and purposes; rules come in Functional Design.

## C1 `infra/starrocks/audit_capture.py`
| Function | Purpose |
|---|---|
| `staging_ddl() -> list[str]` | `CREATE DATABASE IF NOT EXISTS starrocks_audit_db__`, `CREATE TABLE IF NOT EXISTS ...` |
| `STAGING_COLUMNS: tuple[tuple[str, str], ...]` | The expected columns and types |
| `column_problems(actual: list[tuple[str, str]]) -> list[str]` | Differences between the live table and `STAGING_COLUMNS` (missing, unexpected, type) |
| `loader_user_sql(password: str, exists: bool) -> list[str]` | `CREATE USER` (native password) or `ALTER USER ... IDENTIFIED BY`, then `GRANT INSERT ON TABLE ... TO USER` |
| `read_lock(path) -> PluginLock` | Version, source URL, SHA-256, license from `auditloader.lock` |
| `verify_package(path, lock) -> bytes` | The vendored package's bytes; raises on a SHA-256 mismatch |
| `render_plugin_conf(template: str, user: str, password: str) -> str` | The package's `plugin.conf` with `frontend_host_port`, `database`, `table`, `user`, `password` set and every other key kept |
| `build_package(vendored: bytes, conf: str) -> bytes` | The package with the rendered `plugin.conf` (deterministic zip) |
| `package_digest(package: bytes) -> str` | SHA-256 of the built package, recorded in the FE as the plugin's marker |
| `plugin_action(installed: dict | None, digest: str) -> str` | `install`, `reinstall` or `keep` |
| `ensure_audit_capture(runner, credentials_dir, runtime_dir, dry_run) -> dict` | Orchestrates the above; returns a report (no secrets) |
| `capture_status(runner) -> dict` | Plugin state and newest staging timestamp (for `status`) |

## C4 / C5 product model and grants
| Function | Purpose |
|---|---|
| `data_products.PlatformSources` (dataclass) | `starrocks_audit: dict[role, level]` |
| `data_products._platform_sources(raw) -> PlatformSources` | Parse and validate the block |
| `starrocks_common.build_model(products)` | Adds the audit read scopes to the model |
| `bootstrap-starrocks._audit_grants(role) -> set[Grant]` | `SELECT` on the staging table for a reading role |
| `bootstrap-starrocks.role_grants(model)` | Includes `_audit_grants` |

## C7 `infra/workload-python/python/lakehouse_starrocks.py`
| Function | Purpose |
|---|---|
| `connection_settings(environ) -> Settings` | Host, port, CA, user, mode (`airflow` or `jupyter`) from the environment; raises outside both |
| `token_expires_soon(token: str, now: float, margin: int) -> bool` | JWT `exp` check (no signature check: the server verifies) |
| `current_writer_token(environ, now) -> str` | The initial token, or a renewed one from `POST /v1/runs/token` (run handle, capability, broker CA) |
| `connect(*, password_prompt=getpass.getpass) -> pymysql.connections.Connection` | TLS connection; token login (Airflow) or password (Jupyter) |

## C9 / C10
| Change | Purpose |
|---|---|
| `factory._create_spark_container(...)` | Adds the CA volume and the four `LAKEHOUSE_STARROCKS_*` variables |
| `LakehouseSpawner` (volumes, environment) | Adds the CA volume and host, port and CA variables |
