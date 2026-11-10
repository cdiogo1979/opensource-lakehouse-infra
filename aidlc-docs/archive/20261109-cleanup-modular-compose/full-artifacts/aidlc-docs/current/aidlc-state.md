# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-09T11:20:16Z
- Current Stage: DEPLOY - Deploy Handoff
- Intent: Remove files no longer needed (including the TPC-H generator and loader) and split Docker Compose into modules: core (Keycloak, Polaris, RustFS), Jupyter, Jenkins, Airflow, StarRocks.
- Intent ID: 20261109-cleanup-modular-compose
- Previous Intent: aidlc-docs/archive/20261109-starrocks-integration (closed)

## Workspace State
- Existing code: Yes.
- Languages/configuration: Python, Bash, YAML, JSON, Docker Compose.
- Build system: Docker Compose; pytest contract tests.
- Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra-v2
- Git metadata: None in this infrastructure workspace.
- Reverse Engineering Needed: Yes — focused cleanup inventory and Compose module map.
- Reverse-engineering artifacts: aidlc-docs/current/inception/reverse-engineering/

## Code Location Rules
- Application Code: Workspace root (NEVER in aidlc-docs/)
- Documentation: aidlc-docs/ only
- Structure patterns: See code-generation.md Critical Rules

## Stage Progress
- [x] Workspace Detection — brownfield; prior intent closed and archived.
- [x] Focused Reverse Engineering — approved on 2026-11-09.
- [x] Requirements Analysis — approved on 2026-11-09.
- [x] User Stories — SKIPPED.
- [x] Workflow Planning — approved on 2026-11-09.
- [ ] Application Design — SKIP
- [ ] Units Generation — SKIP (single unit: cleanup-modular-compose)
- [ ] Functional Design — SKIP
- [ ] NFR Requirements — SKIP
- [ ] NFR Design — SKIP
- [ ] Infrastructure Design — SKIP
- [x] Code Generation Part 1 — plan approved on 2026-11-09.
- [x] Code Generation Part 2 — approved on 2026-11-09.
- [x] Build and Test — approved on 2026-11-09.
- [x] Deploy Handoff — approved on 2026-11-09.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q6: B) |
| Property-Based Testing | No | Requirements Analysis (Q7: C) |
| Resiliency Baseline | No | Requirements Analysis (Q8: B) |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Current Status
- Lifecycle Phase: DEPLOY
- Current Stage: Deploy Handoff
- Next Stage: Intent closure (separate approval)
- Status: Deploy handoff approved; verification passed. Awaiting intent closure approval.

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "current_stage": "DEPLOY_HANDOFF",
  "intent_id": "20261109-cleanup-modular-compose",
  "name": "Cleanup and Modular Compose",
  "previous_intent": "aidlc-docs/archive/20261109-starrocks-integration",
  "status": "COMPACTION"
}
```
<!-- intent-lifecycle:end -->

## Open Follow-ups (after 20261109-starrocks-integration)
- **Next intent (requested 2026-11-09)**: BI access with long-lived, per-data-product Keycloak tokens.
  - One client per data product, for example `srv-default-bi`, with a service account and an access-token lifespan to be decided.
  - StarRocks roles come from its Keycloak groups. It is revoked by removing it from the groups.
  - Power BI goes through ODBC (Connector/ODBC 9.1+ `openid-token-file`, verify first).
  - The reconciler needs an exception for BI service accounts, and each client an audience mapper for `starrocks`.
  - Password sync from Keycloak is not possible; shared LDAP was not chosen.
- **Spark smoke image**: move `scripts/bootstrap/smoke-spark.sh` and the Spark part of `scripts/verify/role-matrix.py` off the missing legacy image `local/spark-iceberg:3.5.5_1.8.1-krb5` to the v2 Spark runtime. Until then, `bootstrap-default-product.sh` stops before its StarRocks steps.
- **Probe residue**: Build and Test probe data files (`sr_bt_*`) remain in the three buckets, because Polaris refuses purge.
- **Jenkins CI job**: restore it from `.runtime/backups/20261031-pre-reset/jenkins-home.tar.gz`, or define it as code.
- Unexplained disappearance of stopped `hive-dremio-rustfs-*` and `iceberg-poc-*` containers (2026-10-31; volumes intact). The legacy Spark image is now also gone.
- **Airflow developer-role drift**: the code maps `User`; the tests expect `Admin`.
- **JupyterHub broker tests** need `PYTHONPATH=infra/jupyter/hub`.
- **RustFS console**: adopt a RustFS release that bundles console v0.1.38 or later.
- **Deferred folders**: remove `write-service-account` references from the deferred `infra/tpch-loader` when it is revived. They are already gone from `infra/starrocks`.
