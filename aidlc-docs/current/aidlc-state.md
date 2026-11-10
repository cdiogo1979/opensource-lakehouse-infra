# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-11T00:50:00Z
- Current Stage: DEPLOY - Deploy (approved; intent closure)
- Intent: Subproject folders for product repositories: the platform DAG factory and validator accept workflows/<project>/<name>.json with entry points in notebooks/workload/<project>/, next to the existing flat layout; DAG IDs stay <bundle>-<name>.
- Intent ID: 20261111-workflow-subprojects
- Previous Intent: aidlc-docs/archive/20261110-repository-rename (closed)

## Workspace State
- Existing code: Yes. Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra. Git metadata: none.
- Reverse Engineering Needed: No (canonical functional-design/airflow-workflows.md describes the component).
- Note: draft edits to infra/airflow/lakehouse_dags/spec.py and factory.py were made before this intent was opened (see audit); they are reviewed in Code Generation.

## Code Location Rules
- Application Code: Workspace root (NEVER in aidlc-docs/)
- Documentation: aidlc-docs/ only

## Stage Progress
- [x] Workspace Detection — brownfield; previous intent closed.
- [x] Requirements Analysis — approved on 2026-11-11.
- [x] Workflow Planning — approved on 2026-11-11.
- [ ] Design stages — SKIP.
- [x] Code Generation — approved on 2026-11-11.
- [x] Build and Test — approved on 2026-11-11 (with CR-1, CR-2).
- [x] Deploy — handoff approved on 2026-11-11.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (as previous intents) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09) | Requirements Analysis (the spec already has Hypothesis properties) |
| Resiliency Baseline | No | Requirements Analysis |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Current Status
- Lifecycle Phase: DEPLOY
- Current Stage: Deploy
- Next Stage: Intent closure (artifact compaction)
- Status: Verification complete; closing the intent.

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "archive": "aidlc-docs/archive/20261111-workflow-subprojects",
  "current_stage": "DEPLOY - Deploy",
  "intent_id": "20261111-workflow-subprojects",
  "name": "Workflow Subprojects",
  "previous_intent": "aidlc-docs/archive/20261110-repository-rename",
  "status": "CLOSED",
  "summary": "aidlc-docs/archive/20261111-workflow-subprojects/intent-summary.md"
}
```
<!-- intent-lifecycle:end -->

## Open Follow-ups (carried over)
- **Transient bundle-refresh failure**: one task's Airflow bundle refresh hit "detected dubious ownership" on `tracking_repo` when two tasks started together (2026-11-10); not reproduced; investigate if it repeats.
- **JupyterHub keeps the product model it started with**: the Hub imports `infra/products/data_products.py` once, through a single-file bind mount; after that file changes, the Hub fails closed on newer product files until it restarts (found and fixed by a restart on 2026-11-10). The product commands or `start` should restart the Hub when the file changes.
- **Enforcing bundle class**: a later phase to stop Airflow parsing extra repository `.py` files under `dags/`. Since CR-6 (2026-11-10) Airflow scans only `dags/`, so this is limited to files there, which CI refuses.
- **RustFS console**: adopt a RustFS release that bundles console v0.1.38 or later.
