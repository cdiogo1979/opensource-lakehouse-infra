# Code Summary — StarRocks Audit Capture (U1, U2, U3)

Intent `20261125-starrocks-audit-capture`, branch `starrocks-audit-capture`. Plan: [starrocks-audit-capture-code-generation-plan.md](../../plans/starrocks-audit-capture-code-generation-plan.md).

## Files
| Unit | Change | Path |
|---|---|---|
| U1 | Created | `infra/starrocks/audit_capture.py` (staging table, `srv-auditloader`, plugin verify, render, install, status, CLI) |
| U1 | Created | `infra/starrocks/plugins/auditloader-5.0.0.zip` (official package, unchanged), `infra/starrocks/plugins/auditloader.lock` |
| U1 | Modified | `infra/starrocks/bootstrap-starrocks.py` (capture after root, BE, LDAP; before roles; failure reported, not fatal) |
| U1 | Modified | `infra/starrocks/conf/fe.conf` (`audit_log_modules`), `compose.starrocks.yml` (read-only package mount, `starrocks-fe-plugins` volume) |
| U1 | Modified | `scripts/lakehouse.sh` (`.runtime/starrocks-audit` created before StarRocks; `status` line; StarRocks certificates before JupyterHub; `LAKEHOUSE_STARROCKS_CA_HOST_PATH` for Airflow) |
| U2 | Modified | `infra/products/data_products.py` (`platform_sources`), `infra/products/template.yaml` (commented example) |
| U2 | Modified | `infra/starrocks/starrocks_common.py` (`audit_readers`), `infra/starrocks/bootstrap-starrocks.py` (`TABLE db.table` grants: plan, render, parse) |
| U2 | Created (as applied, plus the block) | `data-products/audit.yaml` |
| U3 | Created | `infra/workload-python/python/lakehouse_starrocks.py` |
| U3 | Modified | `infra/workload-python/requirements.in` (`PyMySQL==1.1.2`), `requirements.lock` (one added line) |
| U3 | Modified | `infra/spark-runtime/Dockerfile`, `infra/jupyter/singleuser/Dockerfile` (build-time import check of `lakehouse_starrocks`, `pymysql`) |
| U3 | Modified | `infra/airflow/lakehouse_dags/factory.py` (CA mount and `LAKEHOUSE_STARROCKS_*` in run containers), `compose.airflow.yml` |
| U3 | Modified | `infra/jupyter/hub/lakehouse_policy.py` (`starrocks_ca_volume`), `lakehouse_spawner.py`, `jupyterhub_config.py`, `compose.jupyter.yml` |
| Tests | Created | `tests/starrocks/test_audit_capture.py`, `tests/products/test_platform_sources.py`, `tests/workload_env/test_lakehouse_starrocks.py` |
| Tests | Modified | `tests/starrocks/test_product_access.py`, `test_starrocks_compose_contract.py`, `tests/airflow/test_dag_factory.py`, `tests/jupyterhub/test_checkpoint_key_mounts.py`, `tests/operations/test_compose_modules_contract.py` |
| Docs | Modified | `docs/reference/starrocks.md` (Audit capture), `data-products.md` (Platform sources), `operations.md`, `workload-python.md` (StarRocks connections), `limitations.md`, `docs/security.md`, `docs/components.md` |

## Verification (2026-11-26)
| Check | Result |
|---|---|
| `pytest` (host; venv from `tests/requirements-pbt.txt`, PyYAML and the Hub's `requirements.txt`) | 729 passed, 3 skipped |
| `scripts/verify/dag-factory-tests.sh` (Airflow image) | 119 passed |
| `scripts/verify/broker-unit-tests.sh` | 13 passed |
| `scripts/verify/docs-links.py` | 24 files, no broken links |
| `bash -n scripts/lakehouse.sh`; `docker compose config` with all modules | PASS |
| `lakehouse_starrocks` on Python 3.10.12 (Spark runtime image) | parses and imports |
| `workload_python.py check-lock` | OK, 57 packages |

## Deviations and decisions (DOC-02)
- **Lock**: `lock-workload-python.sh` also bumped 7 unrelated transitive packages (certifi, charset-normalizer, decorator, exceptiongroup, markdown-it-py, mdit-py-plugins, packaging, wcwidth). Kept the previous lock plus only `PyMySQL==1.1.2` (it has no dependencies), validated with `check-lock`; a full re-lock is left to a maintenance change.
- **Capture failure is not fatal** (AC-5 refined): `bootstrap-starrocks.py` reports it and continues, so `start` brings up Airflow and Jupyter; nothing is installed from an unverified package.
- **StarRocks certificates before JupyterHub**: the Hub now mounts the StarRocks CA; created first so Docker never puts a directory in its place.
- **Spawner check moved to `lakehouse_policy.starrocks_ca_volume`** so it is unit-tested like the checkpoint-key mounts.
- **Cross-intent**: the audit product must treat `queryType = disconnection` as a connection event (its `CONNECTION_MARKERS`).

## Not yet verified (Build and Test)
Image rebuilds with PyMySQL; the FE restart with the new `fe.conf` and the plugin volume; plugin installed and loading rows; the `TABLE` grant as StarRocks reports it; the writer's token login from a Spark run container; the Jupyter password login; the audit product's bronze and silver in dev and uat.
