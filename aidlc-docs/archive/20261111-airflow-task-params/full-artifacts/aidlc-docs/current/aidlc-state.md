# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-11T18:00:00Z
- Current Stage: DEPLOY - Deploy (approval pending)
- Intent: Enable task parameters in Airflow: values chosen when a DAG is triggered reach the workflow's tasks as task arguments.
- Intent ID: 20261111-airflow-task-params
- Previous Intent: aidlc-docs/archive/20261111-data-products-reference (closed)

## Workspace State
- Existing code: Yes. Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra.
- Reverse Engineering Needed: No; focused read of infra/airflow/lakehouse_dags (factory.py, spec.py) and the canonical airflow-workflows design.

## Stage Progress
- [x] Workspace Detection — brownfield; previous intent closed.
- [x] Requirements Analysis — approved on 2026-11-11 (per-task trigger values; replace on overlap; sample repo later).
- [x] Workflow Planning — approved on 2026-11-11.
- [x] Probe P1 — object Param works; Airflow doesn't validate its content.
- [x] Code Generation — task_args.py, factory wiring, tests, docs.
- [x] Build and Test — automated checks pass; live UAT runs passed (valid and invalid task_args).
- [ ] Deploy — applied with start-airflow; pr_request.md written; closure approval pending.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes (trigger-time values reach product code) | Requirements Analysis |
| Property-Based Testing | Yes (argument rendering) | Requirements Analysis |
| Resiliency Baseline | No | Requirements Analysis |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Follow-ups
- Materialized-view authoring in the developer journey, query-rewrite verification, and a StarRocks credential for pipeline MV DDL.
- Per-workflow parallelism and Spark memory; Jupyter memory limit; vended-credential refresh for long writes; least-privilege reconciler identity; Hub restart on product model changes.

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "current_stage": "DEPLOY - Deploy",
  "intent_id": "20261111-airflow-task-params",
  "name": "Airflow Task Parameters",
  "previous_intent": "aidlc-docs/archive/20261111-data-products-reference",
  "status": "COMPACTION"
}
```
<!-- intent-lifecycle:end -->
