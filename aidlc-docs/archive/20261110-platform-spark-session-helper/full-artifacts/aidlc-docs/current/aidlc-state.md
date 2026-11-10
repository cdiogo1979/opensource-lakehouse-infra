# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-10T18:10:00Z
- Current Stage: DEPLOY - Deploy (approved; intent closure)
- Intent: A platform-owned Spark session helper for workload code in Airflow and Jupyter (catalogs, token provider, redaction), leaving product repositories with config loading and arguments; remove legacy code from the workload helpers; product selection and a fixed environment rule in Jupyter; a task-arguments convention for Jupyter; tests for the helpers.
- Intent ID: 20261110-platform-spark-session-helper
- Previous Intent: aidlc-docs/archive/20261110-shared-workload-requirements (closed)

## Workspace State
- Existing code: Yes (this infrastructure workspace; workload repository cdiogo1979/opensource-lakehouse in a scratchpad clone at 0bc9ecd).
- Languages/configuration: Python, Java (token provider), Bash, YAML, JSON, Dockerfiles, Docker Compose.
- Build system: Docker Compose; pytest contract and Hypothesis tests.
- Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra-v2
- Git metadata: None in this infrastructure workspace.
- Reverse Engineering Needed: Yes — focused on how Spark sessions are configured in both images and the workload helpers.
- Reverse-engineering artifacts: aidlc-docs/current/inception/reverse-engineering/

## Code Location Rules
- Application Code: Workspace root (NEVER in aidlc-docs/)
- Documentation: aidlc-docs/ only
- Structure patterns: See code-generation.md Critical Rules

## Stage Progress
- [x] Workspace Detection — brownfield; previous intent closed and archived.
- [x] Focused Reverse Engineering — approved on 2026-11-10.
- [x] Requirements Analysis — approved on 2026-11-10 (with CR-1).
- [ ] User Stories — SKIP.
- [x] Workflow Planning — approved on 2026-11-10 (with CR-2, CR-3).
- [x] Application Design — approved on 2026-11-10.
- [ ] Units Generation — SKIP (one unit, `spark-session`).
- [x] Functional Design — approved on 2026-11-10.
- [ ] NFR Requirements, NFR Design, Infrastructure Design — SKIP.
- [x] Code Generation — approved on 2026-11-10.
- [x] Build and Test — approved on 2026-11-10 (with CR-4, CR-5; the interactive Jupyter check not reported).
- [x] Deploy — handoff approved on 2026-11-10.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q5: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q5: A) |
| Resiliency Baseline | No | Requirements Analysis (Q5: A) |
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
  "current_stage": "DEPLOY - Deploy",
  "intent_id": "20261110-platform-spark-session-helper",
  "name": "Platform Spark Session Helper",
  "previous_intent": "aidlc-docs/archive/20261110-shared-workload-requirements",
  "status": "COMPACTION"
}
```
<!-- intent-lifecycle:end -->

## Open Follow-ups (carried over)
- **Transient bundle-refresh failure**: one task's Airflow bundle refresh hit "detected dubious ownership" on `tracking_repo` when two tasks started together (2026-11-10); not reproduced; investigate if it repeats.
- **JupyterHub keeps the product model it started with**: the Hub imports `infra/products/data_products.py` once, through a single-file bind mount; after that file changes, the Hub fails closed on newer product files until it restarts (found and fixed by a restart on 2026-11-10). The product commands or `start` should restart the Hub when the file changes.
- **Enforcing bundle class**: a later phase to stop Airflow parsing extra repository `.py` files under `dags/`. Since CR-6 (2026-11-10) Airflow scans only `dags/`, so this is limited to files there, which CI refuses.
- **RustFS console**: adopt a RustFS release that bundles console v0.1.38 or later.
- **Pre-reset backup**: `.runtime/backups/20261031-pre-reset` is no longer needed to restore Jenkins jobs; keep or delete at the user's choice.
