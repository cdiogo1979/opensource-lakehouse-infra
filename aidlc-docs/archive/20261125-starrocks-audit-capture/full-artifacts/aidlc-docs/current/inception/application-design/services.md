# Services and Orchestration — StarRocks Audit Capture

No new service. New work runs inside existing entry points.

| When | Entry point | What happens |
|---|---|---|
| Every `scripts/lakehouse.sh start` with StarRocks enabled | `bootstrap-starrocks.py --runtime-only` (after the root password and BE) | C1 `ensure_audit_capture`: staging database and table, loader user and password, plugin verify, render, install or reinstall |
| Product apply (`create-data-product.sh`), StarRocks bootstrap without `--runtime-only`, scheduled StarRocks sync | `bootstrap-starrocks.py` grant planning | C5: `SELECT` on the staging table for product roles with `platform_sources.starrocks_audit: read`; revoked when no longer declared |
| `scripts/lakehouse.sh status` | `audit_capture.capture_status` | Prints `audit capture: plugin INSTALLED, newest event <age>` (or the problem) |
| Every minute (StarRocks, built in) | AuditLoader inside the FE | Stream-loads the audit queue into the staging table as `srv-auditloader` |
| Daily (StarRocks, built in) | Expression partitions with `partition_live_number` 7 | Drops staging partitions older than 7 days |
| Airflow DAG run of any product | `factory._create_spark_container` | Run container gets the StarRocks CA and variables (unused unless the code calls `lakehouse_starrocks`) |
| Jupyter server start | `LakehouseSpawner` | Server gets the StarRocks CA and variables |
| Workload code | `lakehouse_starrocks.connect()` | Connection as the writer (Airflow, token, renewed through the broker) or the user (Jupyter, `getpass`) |

## Ordering
1. StarRocks starts (with `fe.conf` `audit_log_modules`), root password, BE (existing).
2. Audit capture (C1) — needs the root runner; before grants.
3. Grants (C5) — the staging table exists.
4. Airflow and JupyterHub pass the CA and variables to new containers.

## Failure behavior
- Package checksum mismatch: the runtime bootstrap stops with a clear message; StarRocks keeps running without (re)installing the plugin.
- Plugin install failure: reported; `status` shows it; the staging table and user stay.
- Staging table with other columns: reported, not altered (an admin decides; the plugin's loads would fail).
- Broker renewal failure in a run: `connect()` raises; the task fails and retries per its workflow.
