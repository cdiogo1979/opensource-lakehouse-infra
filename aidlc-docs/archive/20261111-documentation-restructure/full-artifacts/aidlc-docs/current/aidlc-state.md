# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-11T06:30:00Z
- Current Stage: DEPLOY - Deploy (approval pending)
- Intent: Restructure the platform documentation for easy navigation: clear components, user journeys (platform admin, data product owner, data product developer, data analyst / BI user), and a big-picture platform evolution (the AI-DLC framework, then the main intents). Deliver a separate README draft for review before replacing the current one.
- Intent ID: 20261111-documentation-restructure
- Previous Intent: aidlc-docs/archive/20261111-reconciler-starrocks-recovery (closed)

## Workspace State
- Existing code: Yes. Documentation-only change. Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra.
- Reverse Engineering Needed: Yes — focused on the current README and the archived intents.

## Stage Progress
- [x] Workspace Detection — brownfield; previous intent closed.
- [x] Focused Reverse Engineering — current README (589 lines, 13 sections) and 27 archived intents read.
- [x] Requirements Analysis — approved on 2026-11-11 (CR-1, CR-2).
- [x] Workflow Planning — approved on 2026-11-11.
- [x] Code Generation — draft approved on 2026-11-11 after the change requests.
- [x] Build and Test — approved on 2026-11-11.
- [x] Review and switch — README.md and docs/ in place; previous README kept at construction/switch/README.previous.md; links, coverage and tests rechecked.
- [ ] Deploy — pr_request.md written (no deployment steps); awaiting approval.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No (documentation only) | Requirements Analysis |
| Property-Based Testing | No (no code) | Requirements Analysis |
| Resiliency Baseline | No | Requirements Analysis |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Current Status
- Lifecycle Phase: DEPLOY
- Current Stage: Deploy
- Next Stage: Intent closure
- Status: Awaiting approval of the Deploy handoff.

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "current_stage": "DEPLOY - Deploy",
  "intent_id": "20261111-documentation-restructure",
  "name": "Documentation Restructure",
  "previous_intent": "aidlc-docs/archive/20261111-reconciler-starrocks-recovery",
  "status": "COMPACTION"
}
```
<!-- intent-lifecycle:end -->

## Open Follow-ups (carried over)
- **Developer journey: StarRocks materialized views** (user, 2026-11-11): a follow-up intent integrates MV authoring fully into the data product developer journey and verifies query rewrite acceleration for all users (CR-1 of 20261111-documentation-restructure).
- **Transient bundle-refresh failure**: one task's Airflow bundle refresh hit "detected dubious ownership" on `tracking_repo` when two tasks started together (2026-11-10); not reproduced; investigate if it repeats.
- **JupyterHub keeps the product model it started with**: the Hub imports `infra/products/data_products.py` once, through a single-file bind mount; after that file changes, the Hub fails closed on newer product files until it restarts (found and fixed by a restart on 2026-11-10). The product commands or `start` should restart the Hub when the file changes.
- **Enforcing bundle class**: a later phase to stop Airflow parsing extra repository `.py` files under `dags/`. Since CR-6 (2026-11-10) Airflow scans only `dags/`, so this is limited to files there, which CI refuses.
- **RustFS console**: adopt a RustFS release that bundles console v0.1.38 or later.
