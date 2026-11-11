# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-11T01:10:00Z
- Current Stage: DEPLOY - Deploy
- Intent: Fix StarRocks metadata access for product roles: tools such as DBeaver list tables through `information_schema.tables` with an Iceberg catalog as the current catalog, and StarRocks refuses non-admin users ("SELECT privilege on TABLE tables"), although their table grants are correct.
- Intent ID: 20261111-starrocks-metadata-access
- Previous Intent: aidlc-docs/archive/20261111-spark-s3-checkpoints (closed)

## Workspace State
- Existing code: Yes. Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra. Git metadata: none.
- Reverse Engineering Needed: Yes — focused on StarRocks' external-catalog `information_schema` and the product role grants.

## Stage Progress
- [x] Workspace Detection — brownfield; previous intent closed.
- [x] Focused Reverse Engineering — approved on 2026-11-11.
- [x] Requirements Analysis — approved on 2026-11-11.
- [x] Workflow Planning — approved on 2026-11-11.
- [x] Code Generation — approved on 2026-11-11.
- [x] Build and Test — approved on 2026-11-11 (user confirmed DBeaver).
- [x] Deploy — handoff approved on 2026-11-11; closure approved.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes | Requirements Analysis (Q3: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q3: A) |
| Resiliency Baseline | No | Requirements Analysis (Q3: A) |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Current Status
- Lifecycle Phase: DEPLOY
- Current Stage: Deploy
- Next Stage: Intent closure
- Status: Closure approved; compaction in progress.

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "archive": "aidlc-docs/archive/20261111-starrocks-metadata-access",
  "current_stage": "DEPLOY - Deploy",
  "intent_id": "20261111-starrocks-metadata-access",
  "name": "StarRocks Metadata Access",
  "previous_intent": "aidlc-docs/archive/20261111-spark-s3-checkpoints",
  "status": "CLOSED",
  "summary": "aidlc-docs/archive/20261111-starrocks-metadata-access/intent-summary.md"
}
```
<!-- intent-lifecycle:end -->

## Open Follow-ups (carried over)
- **Transient bundle-refresh failure**: one task's Airflow bundle refresh hit "detected dubious ownership" on `tracking_repo` when two tasks started together (2026-11-10); not reproduced; investigate if it repeats.
- **JupyterHub keeps the product model it started with**: the Hub imports `infra/products/data_products.py` once, through a single-file bind mount; after that file changes, the Hub fails closed on newer product files until it restarts (found and fixed by a restart on 2026-11-10). The product commands or `start` should restart the Hub when the file changes.
- **Enforcing bundle class**: a later phase to stop Airflow parsing extra repository `.py` files under `dags/`. Since CR-6 (2026-11-10) Airflow scans only `dags/`, so this is limited to files there, which CI refuses.
- **RustFS console**: adopt a RustFS release that bundles console v0.1.38 or later.
