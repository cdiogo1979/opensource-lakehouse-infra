# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-09T21:09:25Z
- Current Stage: DEPLOY - Intent Closure
- Intent: A `repo` section in each data product file (Git URL, prod and UAT branches, read-only) that drives the product's Airflow DAG bundles; bundles are created when a product with a repo is applied; optionally the Airflow write credential (secret name) per product.
- Intent ID: 20261109-data-product-airflow-bundles
- Previous Intent: aidlc-docs/archive/20261109-starrocks-ldap-login (closed)

## Workspace State
- Existing code: Yes.
- Languages/configuration: Python, Bash, YAML, JSON, Docker Compose.
- Build system: Docker Compose; pytest contract and Hypothesis tests.
- Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra-v2
- Git metadata: None in this infrastructure workspace.
- Reverse Engineering Needed: Yes — focused on the Airflow bundle configuration, the writer token broker, and the data product apply flow.
- Reverse-engineering artifacts: aidlc-docs/current/inception/reverse-engineering/

## Code Location Rules
- Application Code: Workspace root (NEVER in aidlc-docs/)
- Documentation: aidlc-docs/ only
- Structure patterns: See code-generation.md Critical Rules

## Stage Progress
- [x] Workspace Detection — brownfield; prior intent closed and archived.
- [x] Focused Reverse Engineering — approved on 2026-11-09.
- [x] Requirements Analysis — approved on 2026-11-09 (incl. CR-1).
- [x] User Stories — SKIP.
- [x] Workflow Planning — approved on 2026-11-09.
- [x] Application Design — approved on 2026-11-09.
- [ ] Units Generation — SKIP (one unit: airflow-bundles).
- [x] Functional Design — approved on 2026-11-09.
- [ ] NFR Requirements / NFR Design / Infrastructure Design — SKIP.
- [x] Code Generation — approved on 2026-11-09.
- [x] Build and Test — approved on 2026-11-09.
- [x] Deploy — handoff approved on 2026-11-09.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q5: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q5: A) |
| Resiliency Baseline | No | Requirements Analysis (Q5: A) |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Current Status
- Lifecycle Phase: DEPLOY
- Current Stage: Intent Closure
- Next Stage: none (closing)
- Status: Closure approved; compaction manifest prepared.

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "current_stage": "INTENT_CLOSURE",
  "intent_id": "20261109-data-product-airflow-bundles",
  "name": "Data Product Airflow Bundles",
  "previous_intent": "aidlc-docs/archive/20261109-starrocks-ldap-login",
  "status": "COMPACTION",
  "verification_outcome": "passed"
}
```
<!-- intent-lifecycle:end -->

## Open Follow-ups (after 20261109-data-product-airflow-bundles)
- **BI and DBeaver check**: Power BI (ODBC or JDBC) and DBeaver can now use username and password over TLS. Confirm interactively; Connector/J 9.3.0 is verified. The earlier long-lived BI token idea is only needed if a tool cannot store a password.
- **Pre-migration backup**: `.runtime/backups/20261109T203416Z-pre-ldap/` holds a Keycloak database dump with password hashes (mode 0600). Keep it in encrypted storage or delete it once the migration is confirmed.
- **Jenkins CI job**: restore it from `.runtime/backups/20261031-pre-reset/jenkins-home.tar.gz`, or define it as code.
- **Airflow developer-role drift**: `default.yaml` maps developers to `User`; `tests/airflow/test_keycloak_sso_contract.py` still expects `Admin`.
- **Probe residue**: Build and Test probe data files (`sr_bt_*`) remain in the `default` buckets, because Polaris refuses purge.
- **JupyterHub broker tests** need `PYTHONPATH=infra/jupyter/hub`.
- **RustFS console**: adopt a RustFS release that bundles console v0.1.38 or later.
- **Workload repository test**: `tests/jenkins_deployment/test_airflow_bundle_client.py::test_dag_factory_reuses_spark_container_for_bundle_workloads` in `opensource-lakehouse` still expects `dag_name="init_environment"` (stale since commit "rename dag").
- **Stale Airflow DAG record**: `dev-test_environment` (built from `00b6623` under `default-main`) remains until deleted; the broker refuses it.
- **Local Docker pruning**: unused images disappear between sessions (Rancher Desktop Kubernetes image GC). The `mysql:9.7.2` client image and a JDK image were pulled again during the last intents.
- **Removal backups**: `.runtime/backups/*-remove-*` (test runs) can be deleted when no longer needed.
- **Removed script copy**: the retired `starrocks-token.sh` is kept only in the session scratchpad.
