# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-12T17:00:00Z
- Current Stage: DEPLOY - Commit (push pending approval)
- Intent: (1) Scan the images the platform builds instead of their upstream bases; (2) remove the compiler toolchain (and kernel headers) from the Spark runtime; (3) remove the Spark jars the platform doesn't use.
- Intent ID: 20261112-spark-image-hardening
- Previous Intent: aidlc-docs/archive/20261112-scan-stale-targets (closed)

## Stage Progress
- [x] Workspace Detection — clean tree.
- [x] Requirements Analysis — approved ("approved and continue").
- [x] Workflow Planning — minimal, inline: one unit (Spark runtime image + scan tooling + workflow + docs); User Stories, Application/Functional/NFR/Infrastructure Design skipped (changes inside existing component boundaries).
- [x] Code Generation — Spark runtime Dockerfile; list-images.py `targets()`; vulnerability-scan.py `--build` with export scanning; workflow on ubuntu-24.04-arm; guard tests; docs.
- [x] Build and Test — 663 tests passed (3 skipped); runtime and single-user rebuilt; parity OK; Spark smoke (Parquet, ORC, Iceberg) OK; dry-run scan of 15 targets OK; live checks passed (checkpoint stream, UAT DAG, Jupyter by the user). Approved.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes (runtime attack surface; CI builds) | Requirements Analysis |
| Property-Based Testing | No | Requirements Analysis |
| Resiliency Baseline | No | Requirements Analysis |

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "current_stage": "DEPLOY",
  "intent_id": "20261112-spark-image-hardening",
  "name": "Spark Image Hardening and Built-Image Scanning",
  "previous_intent": "aidlc-docs/archive/20261112-scan-stale-targets",
  "status": "IN_PROGRESS"
}
```
<!-- intent-lifecycle:end -->
