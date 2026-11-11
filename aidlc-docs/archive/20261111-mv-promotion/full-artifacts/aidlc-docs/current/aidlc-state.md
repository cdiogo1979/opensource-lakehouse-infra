# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-11T20:30:00Z
- Current Stage: DEPLOY - Deploy (closing)
- Intent: Developers develop and test StarRocks materialized views in dev; the views reach uat and prod through the normal process (branches, CI, Airflow) instead of by hand. May also change the data product repository.
- Intent ID: 20261111-mv-promotion
- Previous Intent: aidlc-docs/archive/20261111-airflow-task-params (closed)

## Workspace State
- Existing code: Yes. Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra; also /Users/carlosdiogo/code_repo/opensource-lakehouse-sample-dp.
- Reverse Engineering Needed: focused (StarRocks grants and logins, Jenkins jobs, Airflow factory and broker, the product repository's deploy layer).

## Stage Progress
- [x] Workspace Detection — brownfield; previous intent closed; both repositories clean on main.
- [x] Requirements Analysis (CR-1), probes P1 and P2, Application Design — approved on 2026-11-11.
- [x] Code Generation U1 (platform) and U2 (sample), CR-2 — done.
- [x] Build and Test — automated and live UAT checks passed.
- [x] Deploy — reconciler restarted, start-airflow; sample main and uat at 925ef51.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes (a pipeline gains StarRocks write access in uat and prod) | Requirements Analysis |
| Property-Based Testing | Yes (definition parsing and environment substitution) | Requirements Analysis |
| Resiliency Baseline | No | Requirements Analysis |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Follow-ups
- Query-rewrite verification; per-workflow parallelism and Spark memory; Jupyter memory limit; vended-credential refresh for long writes; least-privilege reconciler identity; Hub restart on product model changes.

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "current_stage": "DEPLOY - Deploy",
  "intent_id": "20261111-mv-promotion",
  "name": "Materialized View Promotion",
  "previous_intent": "aidlc-docs/archive/20261111-airflow-task-params",
  "status": "COMPACTION"
}
```
<!-- intent-lifecycle:end -->
