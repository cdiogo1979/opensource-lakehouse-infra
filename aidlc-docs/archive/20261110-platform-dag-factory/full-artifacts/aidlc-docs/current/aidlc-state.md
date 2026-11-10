# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-10T10:18:00Z
- Current Stage: Intent Closure
- Intent: Move the DAG-building logic out of the product repositories into the platform: a product repository holds workflows/*.json (DAG and task definitions), notebooks/ (all of it, also used by Jupyter), configs/ (also used by Jupyter), and a minimal stub; the platform builds the DAGs.
- Intent ID: 20261110-platform-dag-factory
- Previous Intent: aidlc-docs/archive/20261110-data-product-jenkins-pipelines (closed)

## Workspace State
- Existing code: Yes (this infrastructure workspace and the workload repository cdiogo1979/opensource-lakehouse).
- Languages/configuration: Python, Bash, YAML, JSON, Docker Compose.
- Build system: Docker Compose; pytest contract and Hypothesis tests.
- Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra-v2
- Git metadata: None in this infrastructure workspace; the workload repository is worked in a scratchpad clone.
- Reverse Engineering Needed: Yes — focused on the DAG factory, the Airflow processes and images, bundle settings, and the workload repository's tests and docs.
- Reverse-engineering artifacts: aidlc-docs/current/inception/reverse-engineering/

## Code Location Rules
- Application Code: Workspace root (NEVER in aidlc-docs/)
- Documentation: aidlc-docs/ only
- Structure patterns: See code-generation.md Critical Rules

## Stage Progress
- [x] Workspace Detection — brownfield; previous intent closed and archived.
- [x] Focused Reverse Engineering — approved on 2026-11-10.
- [x] Requirements Analysis — approved on 2026-11-10.
- [x] User Stories — SKIP.
- [x] Workflow Planning — approved on 2026-11-10.
- [x] Application Design — approved on 2026-11-10.
- [x] Units Generation — SKIP (one unit: dag-factory).
- [x] Functional Design — approved on 2026-11-10 (incl. CR-1).
- [x] NFR Requirements / NFR Design / Infrastructure Design — SKIP.
- [x] Code Generation — approved on 2026-11-10.
- [x] Build and Test — approved on 2026-11-10.
- [x] Deploy — handoff (deploy_instructions.md, pr_request.md, opensource-lakehouse.patch) approved on 2026-11-10.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q9: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q9: A) |
| Resiliency Baseline | No | Requirements Analysis (Q9: A) |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Current Status
- Lifecycle Phase: DEPLOY
- Current Stage: Intent Closure
- Next Stage: CLOSED
- Status: Verification complete; closure approved; compacting.

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "current_stage": "Intent Closure",
  "intent_id": "20261110-platform-dag-factory",
  "name": "Platform DAG Factory",
  "previous_intent": "aidlc-docs/archive/20261110-data-product-jenkins-pipelines",
  "status": "COMPACTION",
  "verification_outcome": "passed"
}
```
<!-- intent-lifecycle:end -->

## Open Follow-ups (carried over)
- **Next intent: shared workload requirements (CR-2, deferred 2026-11-10)**: a platform base requirements file (pinned, with a lock) baked into both the Spark runtime and the Jupyter images, plus optional product `requirements.txt` extras installed at run start and constrained by the platform lock; a Python 3.10 Jupyter kernel matching the Spark runtime (today Spark 3.10.16, Jupyter 3.13.16; Jupyter lacks pandas, numpy, pyarrow; PyYAML and requests differ).
- **RustFS console**: adopt a RustFS release that bundles console v0.1.38 or later.
- **Pre-reset backup**: `.runtime/backups/20261031-pre-reset` is no longer needed to restore Jenkins jobs; keep or delete at the user's choice.
