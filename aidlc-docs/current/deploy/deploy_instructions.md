# Deployment instructions: StarRocks audit capture

Intent `20261125-starrocks-audit-capture`. These are the ordered steps for a platform checkout moving to this change. Nothing here was executed as a deployment. The local stack already runs this branch's code, from the Build and Test live checks; for it, only steps 1 and 7 remain, after the merge.

Manual steps: all of them. Automated by the scripts: the image rebuilds, the FE and Hub recreation when their configuration or image changes, the audit capture on every start, and the grants on every product apply.

### 1. Merge and update the checkout
- **Action:** merge `starrocks-audit-capture` into `main`, then pull it on the machine that runs the platform.
- **Prerequisites:** review approved; CI is the vulnerability-scan workflow only.
- **Validation:** `git log` shows the merge; `infra/starrocks/plugins/auditloader-5.0.0.zip` matches `auditloader.lock` (`shasum -a 256`).

### 2. Free disk space if needed
- **Action:** check the Docker VM disk (`docker system df`; Rancher Desktop: `rdctl shell df -h /mnt/data`). Above about 80%, prune the build cache with `docker builder prune -f`.
- **Why:** under disk pressure, unused images, including the rebuilt Jupyter image, are deleted.

### 3. Start the core stack
- **Execution:** `./scripts/lakehouse.sh start`.
- **What it does here:**
  - rebuilds the Spark runtime, Jupyter single-user and JupyterHub images (new `lakehouse_starrocks`, PyMySQL and spawner);
  - creates `.runtime/starrocks-audit`;
  - creates the StarRocks certificates before JupyterHub;
  - recreates the StarRocks FE (new `fe.conf`, plugin volume and package mount; **StarRocks is briefly unavailable**) and JupyterHub;
  - runs `bootstrap-starrocks.py --runtime-only`, which creates the staging table and `srv-auditloader` and installs the plugin.
- **Validation:**
  - the start prints `StarRocks audit capture: plugin installed, plugin_version 5.0.0, table ok, user created.` (later starts print `plugin kept`);
  - within about a minute, `./scripts/lakehouse.sh status` prints `audit capture: plugin INSTALLED; newest row 0 min ago`.
- **Failure handling:**
  - `ERROR: StarRocks audit capture not set up: ...` doesn't stop the start. Fix the cause and run `python3 infra/starrocks/audit_capture.py`.
  - A checksum mismatch means the vendored zip was changed: restore it from `main`.
  - If the FE doesn't recreate (compose saw no change), run `docker compose -f compose.core.yml -f compose.starrocks.yml up -d --force-recreate starrocks-fe`, then `python3 infra/starrocks/bootstrap-starrocks.py --runtime-only`.

### 4. Apply the grants
- **Execution:** `scripts/operations/create-data-product.sh data-products/audit.yaml` (asks for the platform admin password; `--dry-run` first to preview). Running the full `python3 infra/starrocks/bootstrap-starrocks.py` also works.
- **Validation:** as root, `SHOW GRANTS FOR ROLE role_audit_writer` lists `GRANT SELECT ON TABLE starrocks_audit_db__.starrocks_audit_tbl__`; the same holds for `role_audit_owner` and `role_audit_developer`, and **not** for `role_audit_analyst` or any other product.
- **Failure handling:** if the grant fails because the table is missing, finish step 3 first.

### 5. Restart Airflow
- **Execution:** `./scripts/lakehouse.sh start-airflow` (new `LAKEHOUSE_STARROCKS_CA_HOST_PATH`; rebuilds the Spark runtime image). Pick a time with no running DAG runs: the Airflow containers are recreated.
- **Validation:** `docker exec lakehouse-local-airflow-scheduler-1 sh -c 'echo $LAKEHOUSE_STARROCKS_CA_HOST_PATH'` prints the host path of `starrocks-ca.crt`.
- **Known:** the command's final DAG check waits while `audit-main` has no DAGs (until the audit product promotes `uat` to `main`). Airflow is up; stop the wait with Ctrl-C.

### 6. Jupyter users
- **Action:** users stop and restart their servers (File → Hub Control Panel), so they get the StarRocks CA, `LAKEHOUSE_STARROCKS_HOST`, `_PORT`, `_CA` and their `LAKEHOUSE_STARROCKS_USER`.
- **Validation:** `import lakehouse_starrocks; lakehouse_starrocks.connect()` prompts for the password and connects. For an audit owner or developer, `SELECT ... FROM starrocks_audit_db__.starrocks_audit_tbl__` returns rows.

### 7. Hand over to the audit product
- **Action:** the paired intent resumes: its dev validation in Jupyter, then `audit-uat-starrocks_audit` hourly. Both have been running on the local stack since 2026-11-26.
- **Validation:** see `opensource-lakehouse-audit-dp`'s `aidlc-docs/current/deploy/deploy_instructions.md`, steps 6 and 10.

## Rollback
- **Capture off:** `UNINSTALL PLUGIN AuditLoader;` (as root). Removing `audit_log_modules` from `fe.conf` takes effect at the next FE restart.
- **Access off:** remove `platform_sources` from `audit.yaml` and apply it; the grants are revoked.
- **Code:** revert the merge; the helper and variables are then unused.
- **Data:** `DROP DATABASE starrocks_audit_db__` and `DROP USER 'srv-auditloader'@'%'` remove the capture entirely. The audit product's own tables are separate and unaffected.

## Inputs needed and blockers
| Item | Owner | Status |
|---|---|---|
| Approval to push `starrocks-audit-capture` and open the PR | you | Pending |
| Platform admin password for step 4 | platform admin | Needed at step 4 |
