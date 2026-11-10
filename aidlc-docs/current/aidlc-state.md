# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-11T04:00:00Z
- Current Stage: DEPLOY - Deploy (approval pending)
- Intent: Durable Spark Structured Streaming checkpoints in each product's bucket: a Hadoop S3 filesystem in the Spark images and a credential path for a checkpoint prefix, for Airflow runs and Jupyter, so product notebooks can stream from Iceberg tables (requested by the paused opensource-lakehouse-sample-dp intent 20261111-tpch-medallion).
- Intent ID: 20261111-spark-s3-checkpoints
- Previous Intent: aidlc-docs/archive/20261111-workflow-subprojects (closed)

## Workspace State
- Existing code: Yes. Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra. Git metadata: none.
- Reverse Engineering Needed: Yes — focused on Spark's storage access, RustFS identity and STS, and the token flows.

## Stage Progress
- [x] Workspace Detection — brownfield; previous intent closed.
- [x] Focused Reverse Engineering — approved on 2026-11-11.
- [x] Requirements Analysis — approved on 2026-11-11.
- [ ] User Stories — SKIP.
- [x] Workflow Planning — approved on 2026-11-11.
- [x] Application Design — approved on 2026-11-11 (static checkpoint keys, CR-1).
- [ ] Units Generation — SKIP (one unit, `s3-checkpoints`).
- [x] Functional Design — approved on 2026-11-11.
- [ ] NFR Requirements, NFR Design, Infrastructure Design — SKIP.
- [x] Code Generation — approved on 2026-11-11.
- [x] Build and Test — approved on 2026-11-11 (verification complete).
- [ ] Deploy — pr_request.md and deploy_instructions.md written; awaiting approval.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes | Requirements Analysis (Q4: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q4: A) |
| Resiliency Baseline | No | Requirements Analysis (Q4: A) |
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
  "intent_id": "20261111-spark-s3-checkpoints",
  "name": "Spark S3 Checkpoints",
  "previous_intent": "aidlc-docs/archive/20261111-workflow-subprojects",
  "status": "VERIFICATION_COMPLETE"
}
```
<!-- intent-lifecycle:end -->

## Open Follow-ups (carried over)
- **Transient bundle-refresh failure**: one task's Airflow bundle refresh hit "detected dubious ownership" on `tracking_repo` when two tasks started together (2026-11-10); not reproduced; investigate if it repeats.
- **JupyterHub keeps the product model it started with**: the Hub imports `infra/products/data_products.py` once, through a single-file bind mount; after that file changes, the Hub fails closed on newer product files until it restarts (found and fixed by a restart on 2026-11-10). The product commands or `start` should restart the Hub when the file changes.
- **Enforcing bundle class**: a later phase to stop Airflow parsing extra repository `.py` files under `dags/`. Since CR-6 (2026-11-10) Airflow scans only `dags/`, so this is limited to files there, which CI refuses.
- **RustFS console**: adopt a RustFS release that bundles console v0.1.38 or later.
