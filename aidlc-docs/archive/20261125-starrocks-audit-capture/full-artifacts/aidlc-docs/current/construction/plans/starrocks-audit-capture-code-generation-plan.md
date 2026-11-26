# Code Generation Plan — StarRocks Audit Capture (U1, U2, U3, docs)

Intent `20261125-starrocks-audit-capture`. Single source of truth for Code Generation. Design: [application design](../../inception/application-design/application-design.md), [functional design](../starrocks-audit-capture/functional-design/) (AC-1 to AC-23). Branch: `starrocks-audit-capture` from `main`.

## Context
- Workspace root `/Users/carlosdiogo/code_repo/opensource-lakehouse-infra`; brownfield; existing patterns followed: `starrocks_common.SqlRunner` (`query`, `execute`), grant planning in `bootstrap-starrocks.py`, product parsing in `data_products.py`, host-path environment variables for mounts (`LAKEHOUSE_BROKER_CA_HOST_PATH`), the spawner's in-container validation of mounted CAs, Hypothesis strategies under `tests/*/…_strategies.py`.
- Consumer: `opensource-lakehouse-audit-dp` bronze task (`lakehouse_starrocks.connect()`, `SELECT *` on the staging table).
- Not in this stage: image rebuilds and live checks (Build and Test); pushing (asked at Deploy).

## Steps

### U1 `starrocks-audit-capture`
- [x] **1** Vendor the package: `infra/starrocks/plugins/auditloader-5.0.0.zip` (the inspected official file, SHA-256 `cd2a8a…a8ea2`) and `infra/starrocks/plugins/auditloader.lock` (AC-5).
- [x] **2** `infra/starrocks/audit_capture.py`: staging DDL and columns (AC-1, AC-2), loader password and user (AC-3, AC-4), lock and verification (AC-5), `plugin.conf` rendering (AC-6), deterministic package and digest (AC-7), install decision and execution (AC-8), `ensure_audit_capture`, `capture_status` (AC-11), a small CLI (`--status`, `--dry-run`).
- [x] **3** `infra/starrocks/bootstrap-starrocks.py`: run audit capture after the root password, BE and LDAP login, in `--runtime-only` and full runs, before `ensure_roles` (AC-12); `--dry-run` prints the plan.
- [x] **4** `infra/starrocks/conf/fe.conf`: `audit_log_modules = slow_query,query,connection` (AC-10). `compose.starrocks.yml`: read-only mount `./.runtime/starrocks-audit:/opt/lakehouse/starrocks-audit`, named volume `starrocks-fe-plugins:/opt/starrocks/fe/plugins` (AC-8, AC-9).
- [x] **5** `scripts/lakehouse.sh`: create `.runtime/starrocks-audit` (0700) before StarRocks starts (bind-mount source must exist); `status` prints the capture line (AC-11).
- [x] **6** Tests: `tests/starrocks/test_audit_capture.py` (DDL, column problems, password file mode and reuse, user SQL, lock and checksum, rendering, package determinism, install decision, orchestration with a fake runner, no secret in reports or output) and Hypothesis properties (rendering and package round trips, column check, install decision); `tests/starrocks/test_starrocks_compose_contract.py` updated for the mount and volume.

### U2 `product-platform-sources`
- [x] **7** `infra/products/data_products.py`: `platform_sources` parsing and validation (AC-13, AC-14), `Product.platform_sources`; `infra/products/template.yaml`: commented example.
- [x] **8** `infra/starrocks/starrocks_common.py`: model carries the reading roles; `bootstrap-starrocks.py`: `TABLE db.table` grants in `role_grants`, `render_grant`, `parse_role_grants` (AC-15).
- [x] **9** `data-products/audit.yaml`: `platform_sources: {starrocks_audit: {owner: read, developer: read, analyst: none, writer: read}}` (AC-16).
- [x] **10** Tests: `tests/products/test_data_products.py` (block accepted, defaults, refusals) and properties; `tests/starrocks/test_product_access.py` (grants for reading roles only, revoked when undeclared) and the grant render/parse round-trip property.

### U3 `workload-starrocks-connection`
- [x] **11** `infra/workload-python/python/lakehouse_starrocks.py` (AC-17 to AC-21).
- [x] **12** `infra/workload-python/requirements.in`: `PyMySQL==<latest 1.1.x>`; `requirements.lock` regenerated with `scripts/setup/lock-workload-python.sh` (needs the Spark image and PyPI) (AC-23).
- [x] **13** `infra/airflow/lakehouse_dags/factory.py`: CA volume and `LAKEHOUSE_STARROCKS_*` variables in run containers, the writer from the product file (AC-22); `compose.airflow.yml`: `LAKEHOUSE_STARROCKS_CA_HOST_PATH` for the scheduler.
- [x] **14** `infra/jupyter/hub/lakehouse_spawner.py` (+ `jupyterhub_config.py` trait): CA volume (validated like the broker CA) and host, port, CA variables; `compose.jupyter.yml`: host path variable and the in-container CA mount for validation (AC-22).
- [x] **15** Tests: `tests/workload_env/test_lakehouse_starrocks.py` (mode, settings, token expiry, renewal request with a fake broker, login arguments with a fake PyMySQL, no secrets in errors) and properties; `tests/airflow/test_dag_factory.py` and `tests/jupyterhub/…` updated for the mounts and variables.

### Docs and verification
- [x] **16** Docs: `docs/reference/starrocks.md` (audit capture, loader user, staging table, plugin lifecycle and rotation), `docs/reference/data-products.md` (`platform_sources`), `docs/security.md` (new credential, audit log sensitivity), `docs/reference/operations.md` (reinstall, password rotation, FE restart for login events), `docs/reference/workload-python.md` (`lakehouse_starrocks`, PyMySQL), `docs/components.md`, `docs/reference/limitations.md`; README component table if needed.
- [x] **17** Verify: full `pytest` (unit; live and integration markers excluded), the repository's lint and scan steps as CI runs them, `bash -n scripts/lakehouse.sh`, `docker compose config` for the changed modules.
- [x] **18** Code summary `aidlc-docs/current/construction/starrocks-audit-capture/code/summary.md`; commit on `starrocks-audit-capture` (local only).

### Step 19 — Added during generation (DOC-02)
- [x] Capture failures reported, not fatal (bootstrap); AC-5 updated.
- [x] Lock: previous lock plus only `PyMySQL==1.1.2` (the script's 7 transitive bumps not taken).
- [x] StarRocks certificates generated before JupyterHub starts (the Hub mounts the CA).
- [x] `starrocks_ca_volume` helper in `lakehouse_policy.py`; `tests/operations/test_compose_modules_contract.py` gets the new required variable.

## Traceability
| Requirement / rule | Steps |
|---|---|
| FR-1, AC-1, AC-2, AC-10 | 2, 4, 6 |
| FR-2, AC-3, AC-4 | 2, 6 |
| FR-3, AC-5 to AC-9 | 1, 2, 4, 6 |
| FR-3.3, AC-11, AC-12 | 3, 5 |
| FR-4, AC-13 to AC-16 | 7 to 10 |
| FR-5, AC-17 to AC-21, AC-23 | 11, 12, 15 |
| FR-6, AC-22 | 13, 14, 15 |
| FR-7 | 9, 16 |
| NFR-1 security | 1, 2, 11, 14, 16 (reviewed in 17) |
| NFR-4 testing (PBT-02/-03/-07/-08/-09) | 6, 10, 15 |
