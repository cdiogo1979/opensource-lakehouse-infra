# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-10T23:15:00Z
- Current Stage: CONSTRUCTION - Code Generation (approval pending)
- Intent: Follow the user's renames: the platform workspace folder (opensource-lakehouse-infra-v2 to opensource-lakehouse-infra) and the workload repository (cdiogo1979/opensource-lakehouse to cdiogo1979/opensource-lakehouse-sample-dp): recreate the stack from the new folder, update the product file, docs, tests and the notebooks' Initialization path.
- Intent ID: 20261110-repository-rename
- Previous Intent: aidlc-docs/archive/20261110-platform-spark-session-helper (closed)

## Workspace State
- Existing code: Yes (this workspace, now at /Users/carlosdiogo/code_repo/opensource-lakehouse-infra; the workload repository in a scratchpad clone).
- Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra
- Git metadata: None in this infrastructure workspace.
- Reverse Engineering Needed: No (the references were inventoried directly; see requirements.md).
- Knowledge project folder: aidlc-docs/knowledge/opensource-lakehouse-infra-v2/ (name kept as a stable identifier; archives link to it).

## Code Location Rules
- Application Code: Workspace root (NEVER in aidlc-docs/)
- Documentation: aidlc-docs/ only

## Stage Progress
- [x] Workspace Detection — brownfield; previous intent closed; reverse engineering skipped (direct inventory).
- [x] Requirements Analysis — approved on 2026-11-10.
- [x] Workflow Planning — approved on 2026-11-10.
- [ ] Reverse Engineering, User Stories, Application Design, Units Generation — SKIP.
- [ ] Functional, NFR, Infrastructure Design — SKIP.
- [ ] Code Generation — plan approved; 6 steps generated (code-summary.md); awaiting approval.
- [ ] Build and Test — EXECUTE.
- [ ] Deploy — EXECUTE (handoff).

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (as previous intents) |
| Property-Based Testing | No (no new business logic) | Requirements Analysis |
| Resiliency Baseline | No | Requirements Analysis (as previous intents) |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Current Status
- Lifecycle Phase: CONSTRUCTION
- Current Stage: Code Generation (unit rename)
- Next Stage: Build and Test
- Status: Awaiting approval of the generated changes.

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "current_stage": "CONSTRUCTION - Code Generation",
  "intent_id": "20261110-repository-rename",
  "name": "Repository Rename",
  "previous_intent": "aidlc-docs/archive/20261110-platform-spark-session-helper",
  "status": "IN_PROGRESS"
}
```
<!-- intent-lifecycle:end -->

## Open Follow-ups (carried over)
- **Transient bundle-refresh failure**: one task's Airflow bundle refresh hit "detected dubious ownership" on `tracking_repo` when two tasks started together (2026-11-10); not reproduced; investigate if it repeats.
- **JupyterHub keeps the product model it started with**: the Hub imports `infra/products/data_products.py` once, through a single-file bind mount; after that file changes, the Hub fails closed on newer product files until it restarts (found and fixed by a restart on 2026-11-10). The product commands or `start` should restart the Hub when the file changes.
- **Enforcing bundle class**: a later phase to stop Airflow parsing extra repository `.py` files under `dags/`. Since CR-6 (2026-11-10) Airflow scans only `dags/`, so this is limited to files there, which CI refuses.
- **RustFS console**: adopt a RustFS release that bundles console v0.1.38 or later.
- **Pre-reset backup**: `.runtime/backups/20261031-pre-reset` is no longer needed to restore Jenkins jobs; keep or delete at the user's choice.
