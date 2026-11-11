# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-11T10:15:00Z
- Current Stage: DEPLOY - Deploy (approval pending)
- Intent: Move the data products and data layout content out of docs/components.md into its own reference page, and state that AI-DLC is an adaptation of the AWS AI-DLC v1 workflow.
- Intent ID: 20261111-data-products-reference
- Previous Intent: aidlc-docs/archive/20261111-documentation-restructure (closed)

## Workspace State
- Existing code: Yes. Documentation-only change. Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra.
- Reverse Engineering Needed: No; the previous intent's documentation analysis applies (archived).

## Stage Progress
- [x] Workspace Detection — brownfield; previous intent closed; small documentation intent.
- [x] Requirements Analysis — minimal depth; approved on 2026-11-11.
- [x] Workflow Planning — approved on 2026-11-11.
- [x] Code Generation — page created, links repointed, AI-DLC origin added.
- [x] Build and Test — links, moved content, pytest passed.
- [ ] Deploy — pr_request.md written (no deployment); awaiting approval.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No (documentation only) | Requirements Analysis |
| Property-Based Testing | No (no code) | Requirements Analysis |
| Resiliency Baseline | No | Requirements Analysis |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Follow-ups
- Materialized-view authoring in the developer journey and query-rewrite verification.
- Workflow params; per-workflow parallelism and Spark memory; Jupyter memory limit; vended-credential refresh for long writes; least-privilege reconciler identity; Hub restart on product model changes.

## Current Status
- Lifecycle Phase: VERIFICATION_COMPLETE
- Current Stage: Deploy
- Next Stage: Intent closure
- Status: Awaiting approval of code generation, build and test, and the Deploy handoff.

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "archive": "aidlc-docs/archive/20261111-data-products-reference",
  "current_stage": "DEPLOY - Deploy",
  "intent_id": "20261111-data-products-reference",
  "name": "Data Products Reference",
  "previous_intent": "aidlc-docs/archive/20261111-documentation-restructure",
  "status": "CLOSED",
  "summary": "aidlc-docs/archive/20261111-data-products-reference/intent-summary.md"
}
```
<!-- intent-lifecycle:end -->

## Open Follow-ups (carried over)
- **Developer journey: StarRocks materialized views** (user, 2026-11-11): a follow-up intent integrates MV authoring fully into the data product developer journey and verifies query rewrite acceleration for all users (CR-1 of 20261111-documentation-restructure).
- **Transient bundle-refresh failure**: one task's Airflow bundle refresh hit "detected dubious ownership" on `tracking_repo` when two tasks started together (2026-11-10); not reproduced; investigate if it repeats.
- **JupyterHub keeps the product model it started with**: the Hub imports `infra/products/data_products.py` once, through a single-file bind mount; after that file changes, the Hub fails closed on newer product files until it restarts (found and fixed by a restart on 2026-11-10). The product commands or `start` should restart the Hub when the file changes.
- **Enforcing bundle class**: a later phase to stop Airflow parsing extra repository `.py` files under `dags/`. Since CR-6 (2026-11-10) Airflow scans only `dags/`, so this is limited to files there, which CI refuses.
- **RustFS console**: adopt a RustFS release that bundles console v0.1.38 or later.
