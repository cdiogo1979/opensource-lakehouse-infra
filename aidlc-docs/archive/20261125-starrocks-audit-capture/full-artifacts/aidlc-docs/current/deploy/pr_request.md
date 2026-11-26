# PR request: StarRocks audit capture for the audit data product

Proposed pull request: `starrocks-audit-capture` into `main`. Intent `20261125-starrocks-audit-capture`, paired with the audit product's intent `20261125-starrocks-query-audit` (`opensource-lakehouse-audit-dp`). Not yet pushed or opened.

## Problem
The audit data product needs every StarRocks audit event: queries, logins and platform activity. Its bronze task must be able to read them as the product writer in Airflow, and as its owners and developers in Jupyter. Nobody else should be able to read them.

StarRocks 4.1.7 keeps its audit log only in a file inside the FE container. Workload code also had no way to connect to StarRocks.

## Solution
- **Capture:** StarRocks' AuditLoader plugin (5.0.0, "for 3.3.11+") writes every event to `starrocks_audit_db__.starrocks_audit_tbl__`. The table has one partition per day, keeps 7 days, and stores times in UTC. `fe.conf` enables login and logout events.
  - The plugin is **vendored**: StarRocks publishes it only at an unversioned URL with no checksum, so the repo keeps the package, verified against a locked SHA-256 before every install.
  - It loads as `srv-auditloader`, whose generated password allows only `INSERT` on that table.
  - Every `start` checks and installs it again, idempotently. A failure is reported without stopping `start`, and `status` shows the capture's health.
- **Access:** a new optional block in the product file, `platform_sources.starrocks_audit`, grants `SELECT` on the staging table per role, through the existing grant planning. Single-table grants are now planned, rendered and parsed. `data-products/audit.yaml` declares it for owner, developer and writer, with analysts at `none`.
- **Connection:** `lakehouse_starrocks.connect()` in the workload Python set returns a PyMySQL connection over verified TLS:
  - in Airflow runs, as the product writer, with the run's token renewed through the broker;
  - in Jupyter, as the signed-in user's Keycloak username, with a `getpass` password that's never stored.

  PyMySQL is added to the lock. Run containers and Jupyter servers get the StarRocks CA and settings.

## Main changes
| Area | Paths |
|---|---|
| Capture | `infra/starrocks/audit_capture.py` (new), `infra/starrocks/plugins/` (vendored zip and lock, new), `infra/starrocks/bootstrap-starrocks.py`, `infra/starrocks/conf/fe.conf`, `compose.starrocks.yml` (package mount, `starrocks-fe-plugins` volume), `scripts/lakehouse.sh` (runtime folder, status, certificate order, CA host path) |
| Access | `infra/products/data_products.py`, `infra/products/template.yaml`, `infra/starrocks/starrocks_common.py`, `infra/starrocks/bootstrap-starrocks.py` (table grants), `data-products/audit.yaml` (new in git) |
| Connection | `infra/workload-python/python/lakehouse_starrocks.py` (new), `infra/workload-python/requirements.in` and `requirements.lock` (`PyMySQL==1.1.2`), both workload Dockerfiles (import check), `infra/airflow/lakehouse_dags/factory.py`, `compose.airflow.yml`, `infra/jupyter/hub/lakehouse_policy.py`, `lakehouse_spawner.py`, `jupyterhub_config.py`, `compose.jupyter.yml` |
| Tests | `tests/starrocks/test_audit_capture.py`, `tests/products/test_platform_sources.py`, `tests/workload_env/test_lakehouse_starrocks.py` (new); updates to the product-access, compose, DAG factory, Jupyter mount and module contract tests |
| Docs | `docs/reference/starrocks.md` (Audit capture), `data-products.md` (Platform sources), `workload-python.md` (StarRocks connections), `operations.md`, `limitations.md`, `docs/security.md`, `docs/components.md` |

## Verification
| Check | Result |
|---|---|
| Host test suite | 730 passed, 3 skipped |
| `scripts/verify/dag-factory-tests.sh` (Airflow image) | 119 passed |
| `scripts/verify/broker-unit-tests.sh` | 13 passed |
| `scripts/verify/docs-links.py`; `docker compose config`, all modules; `bash -n` | PASS |
| Images rebuilt; `workload-python-parity.sh` | PASS (57 packages) |
| Live checks on the local stack | 10 of 10 PASS: plugin installed and idempotent; rows within a minute, logins included; loader `INSERT`-only; passwords masked in the captured statements; grants only for the audit owner, developer and writer; writer token login from a Spark run; the audit product's first uat loads (728 events with 728 distinct keys, five views refreshing); Jupyter password login (run by the user) |

Details: `aidlc-docs/current/construction/build-and-test/build-and-test-summary.md`.

## Deployment
Ordered steps are required: see [deploy_instructions.md](deploy_instructions.md). In short:
1. `scripts/lakehouse.sh start` rebuilds the images and recreates the StarRocks FE and JupyterHub, then installs the capture.
2. Apply `audit.yaml` for the grants.
3. Run `start-airflow`.
4. Users restart their Jupyter servers.

## Risks and limitations
- **The staging table keeps 7 days:** a consumer that stops pulling for longer loses those events.
- **The FE restart** that applies `fe.conf` briefly interrupts StarRocks. Password logins recover within a reconciler cycle, as after any restart.
- **The plugin is pinned at 5.0.0:** updating it is a reviewed commit of the zip plus its lock.
- **Lock:** only PyMySQL was added. The lock script would also have bumped 7 unrelated transitive packages, which I left for a maintenance change.
- **Spawner changes need a Hub image rebuild** (the code is baked in). `start` does it.
- **Rancher Desktop deletes unused images under disk pressure.** It happened twice during testing (the documented limitation). Keep the Docker build cache in check.
- **Pre-existing, not caused by this change:**
  - the StarRocks bootstrap re-applies existing grants on every run;
  - `start-airflow`'s final check waits while a product bundle has no DAGs (`audit-main` until its first promotion).
- **The audit log holds every statement of every user.** Only declared roles can read it. StarRocks masks `IDENTIFIED BY` values, and the audit product redacts credentials as well.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
