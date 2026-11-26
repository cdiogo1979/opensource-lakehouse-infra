# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-25T18:56:54Z
- Current Stage: Intent closure (compaction)
- Intent: Platform support for the audit data product's StarRocks source: capture StarRocks audit events into a staging table (AuditLoader), let the audit product read it (grants in the product model), and give workload code a StarRocks connection (`lakehouse_starrocks.connect()`) in Airflow runs and Jupyter.
- Intent ID: 20261125-starrocks-audit-capture
- Previous Intent: aidlc-docs/archive/20261113-airflow-python-packages (closed)
- Paired intent: `opensource-lakehouse-audit-dp` intent `20261125-starrocks-query-audit` (on hold at closure, waiting for this one). Its deploy instructions steps 2 to 4 are this intent's scope.

## Workspace State
- **Existing Code**: Yes (Docker Compose platform; Python bootstrap, reconcilers, Airflow DAG factory, workload Python set; tests under `tests/`).
- **Workspace Root**: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra
- **Branch**: `main`; working tree: `data-products/audit.yaml` untracked (created and applied by the user on 2026-11-25, re-applied after setting `access.analyst.prod: none`).
- **Reverse Engineering Needed**: No. Canonical knowledge `aidlc-docs/knowledge/opensource-lakehouse-infra/` covers the platform (application design; functional designs for product access, StarRocks SQL access, workload Python, Airflow workflows, MV promotion, Jenkins).

### Workspace findings (Workspace Detection)
1. StarRocks 4.1.7 has no built-in audit table; the open-source way is the AuditLoader FE plugin, which reads `fe.audit.log` and stream-loads it into `starrocks_audit_db__.starrocks_audit_tbl__` with a StarRocks user and password from its `plugin.conf`.
2. `infra/starrocks/bootstrap-starrocks.py` `plan_grants` revokes every privilege on a managed role that the product files don't declare: a hand-made `SELECT` on the staging table would be revoked, so the grant must be modeled.
3. Airflow Spark run containers (`lakehouse_dags/factory.py`) get `LAKEHOUSE_INITIAL_ACCESS_TOKEN`, the broker URL and CA, `LAKEHOUSE_RUN_HANDLE` and `LAKEHOUSE_RUN_CAPABILITY` (renewal via `POST /v1/runs/token`), join the `data-access` network where `starrocks-fe` listens, but don't mount the StarRocks CA.
4. `lakehouse_dags/mv_deploy.connect` already logs in to StarRocks with a writer token over TLS (PyMySQL plus the `authentication_openid_connect_client` handshake); PyMySQL is in the Airflow image, **not** in the workload Python lock (`infra/workload-python/requirements.in`).
5. Jupyter user servers join `data-access` (DockerSpawner `data_access_network_name`); people log in to StarRocks with LDAP passwords (only product writers use token login).
6. The StarRocks CA is at `.runtime/container-mounts/starrocks-ca.crt` (mounted in Airflow and core services).

## Code Location Rules
- **Application Code**: Workspace root (NEVER in aidlc-docs/)
- **Documentation**: aidlc-docs/ only

## Stage Progress
### INCEPTION PHASE
- [x] Workspace Detection — brownfield; previous intent closed; new intent opened (2026-11-25T18:56:54Z).
- [x] Reverse Engineering — SKIPPED: canonical knowledge current.
- [x] Requirements Analysis — approved 2026-11-25 (approve-continue).
- [x] User Stories — SKIPPED.
- [x] Workflow Planning — approved 2026-11-25.
- [x] Application Design — approved 2026-11-25.
- [x] Units Generation — SKIPPED: U1 starrocks-audit-capture, U2 product-platform-sources, U3 workload-starrocks-connection.

### CONSTRUCTION PHASE
- [x] Functional Design (U1-U3 consolidated) — approved 2026-11-25
- [x] Code Generation U1, U2, U3, docs — approved 2026-11-26
- [x] NFR Requirements, NFR Design, Infrastructure Design — SKIPPED
- [x] Build and Test — approved 2026-11-26; all live checks PASS (10 of 10)

### DEPLOY PHASE
- [x] Deploy handoff — approved 2026-11-26; branch pushed (`starrocks-audit-capture`)

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes | Requirements Analysis |
| Resiliency Baseline | No | Requirements Analysis |
| Property-Based Testing | Partial (PBT-02, -03, -07, -08, -09 enforced) | Requirements Analysis |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "current_stage": "DEPLOY - Deploy",
  "intent_id": "20261125-starrocks-audit-capture",
  "name": "StarRocks Audit Capture",
  "previous_intent": "aidlc-docs/archive/20261113-airflow-python-packages",
  "status": "COMPACTION"
}
```
<!-- intent-lifecycle:end -->
