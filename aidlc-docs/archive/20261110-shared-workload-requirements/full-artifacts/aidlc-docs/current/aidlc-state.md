# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-10T12:12:00Z
- Current Stage: DEPLOY - Deploy (approved; intent closure)
- Intent: A common, pinned requirements file for all workload code, used by both the Airflow Spark containers and the Jupyter Spark environment, plus optional product extras installed at run start constrained by the platform lock; a Python 3.10 Jupyter kernel matching the Spark runtime (CR-2 of the previous intent).
- Intent ID: 20261110-shared-workload-requirements
- Previous Intent: aidlc-docs/archive/20261110-platform-dag-factory (closed)

## Workspace State
- Existing code: Yes (this infrastructure workspace; workload repository cdiogo1979/opensource-lakehouse in a scratchpad clone).
- Languages/configuration: Python, Bash, YAML, JSON, Dockerfiles, Docker Compose.
- Build system: Docker Compose; pytest contract and Hypothesis tests.
- Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra-v2
- Git metadata: None in this infrastructure workspace.
- Reverse Engineering Needed: Yes — focused on the Spark runtime and Jupyter images, their Python environments and packages, and network reach.
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
- [x] Workflow Planning — approved on 2026-11-10 (with CR-2).
- [x] Application Design — approved on 2026-11-10.
- [ ] Units Generation — SKIP (one unit, `workload-python`).
- [x] Functional Design — approved on 2026-11-10.
- [ ] NFR Requirements, NFR Design, Infrastructure Design — SKIP.
- [x] Code Generation — approved on 2026-11-10.
- [x] Build and Test — approved on 2026-11-10 (with CR-3 to CR-6).
- [x] Deploy — handoff approved on 2026-11-10.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q8: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q8: A) |
| Resiliency Baseline | No | Requirements Analysis (Q8: A) |
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
  "intent_id": "20261110-shared-workload-requirements",
  "name": "Shared Workload Requirements",
  "previous_intent": "aidlc-docs/archive/20261110-platform-dag-factory",
  "status": "COMPACTION"
}
```
<!-- intent-lifecycle:end -->

## Open Follow-ups (carried over)
- **Transient bundle-refresh failure**: one task's Airflow bundle refresh hit "detected dubious ownership" on `tracking_repo` when two tasks started together (2026-11-10); not reproduced; investigate if it repeats.
- **JupyterHub keeps the product model it started with**: the Hub imports `infra/products/data_products.py` once, through a single-file bind mount; after that file changes, the Hub fails closed on newer product files until it restarts (found and fixed by a restart on 2026-11-10). The product commands or `start` should restart the Hub when the file changes.
- **Enforcing bundle class**: a later phase to stop Airflow parsing extra repository `.py` files under `dags/`. Since CR-6 (2026-11-10) Airflow scans only `dags/`, so this is limited to files there, which CI refuses.
- **Platform Spark session helper** (analysis of 2026-11-10): move the Polaris catalog, token-provider and redaction settings from the workload repository's `notebooks/common/job_runtime.py` (also duplicated in the Jupyter image's `lakehouse_spark.py`) into one platform module in both images; remove the `spark-files` and `LAKEHOUSE_BUNDLE_CONFIG_DIR` legacy code; let Jupyter select a product for `configs/<product>/`; fix `jupyter_helper.py` (stale `init_environment` references, forced `dev` against the notebooks' text); a Jupyter convention for task arguments; tests for `job_runtime` and the helper.
- **RustFS console**: adopt a RustFS release that bundles console v0.1.38 or later.
- **Pre-reset backup**: `.runtime/backups/20261031-pre-reset` is no longer needed to restore Jenkins jobs; keep or delete at the user's choice.
