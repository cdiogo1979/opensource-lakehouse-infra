# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-09T09:25:53Z
- Current Stage: DEPLOY - Deploy Handoff
- Intent: Integrate StarRocks in a separate Compose file, create its Iceberg catalogs on Polaris from the product bootstrap, and align StarRocks roles with the product roles.
- Intent ID: 20261109-starrocks-integration
- Previous Intent: aidlc-docs/archive/20261031-environment-reset-bootstrap-users (closed)

## Workspace State
- Existing code: Yes.
- Languages/configuration: Python, Bash, YAML, JSON, Docker Compose, SQL.
- Build system: Docker Compose; pytest contract tests.
- Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra-v2
- Git metadata: None in this infrastructure workspace.
- Reverse Engineering Needed: Yes — focused on legacy StarRocks assets, the deferred Compose entry, and the Polaris/Keycloak/RustFS integration points.
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
- [x] Application Design — approved on 2026-11-09.
- [ ] Units Generation — SKIP (single unit: starrocks-integration)
- [x] Functional Design — approved on 2026-11-09.
- [ ] NFR Requirements — SKIP
- [ ] NFR Design — SKIP
- [ ] Infrastructure Design — SKIP (covered in Application Design)
- [x] Code Generation Part 1 — plan approved on 2026-11-09.
- [x] Code Generation Part 2 — approved on 2026-11-09.
- [x] Build and Test — approved on 2026-11-09.
- [x] Deploy Handoff — approved on 2026-11-09.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q9: B) |
| Property-Based Testing | Partial — PBT-02, 03, 07, 08, 09 enforced; others advisory | Requirements Analysis (Q10: B) |
| Resiliency Baseline | No | Requirements Analysis (Q11: B) |
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
  "intent_id": "20261109-starrocks-integration",
  "name": "StarRocks Integration",
  "previous_intent": "aidlc-docs/archive/20261031-environment-reset-bootstrap-users",
  "status": "COMPACTION"
}
```
<!-- intent-lifecycle:end -->

## Open Follow-ups (from 20261031-environment-reset-bootstrap-users)
- Restore the Jenkins CI job from `.runtime/backups/20261031-pre-reset/jenkins-home.tar.gz`, or define it as code.
- Unexplained disappearance of stopped `hive-dremio-rustfs-*` and `iceberg-poc-*` containers during Build and Test (volumes intact; not the reset).
- Airflow developer-role drift: code maps `User`, tests expect `Admin`.
- JupyterHub broker tests need `PYTHONPATH=infra/jupyter/hub`.
- Adopt a RustFS release that bundles console v0.1.38 or later.
- Remove `write-service-account` references from the deferred `infra/tpch-loader` and `infra/starrocks` when they are revived.
- New intent (requested 2026-11-09): BI access with long-lived, per-data-product Keycloak tokens.
  - One client per data product, for example `srv-default-bi`, with a service account and an access-token lifespan to be decided in that intent.
  - StarRocks roles come from the account's Keycloak groups. It is revoked by removing it from the groups (the reconciler drops the user).
  - Power BI goes through ODBC (Connector/ODBC 9.1+ `openid-token-file`, to be verified first).
  - The reconciler needs an exception for BI service accounts, and each BI client an audience mapper for `starrocks`.
  - Password sync from Keycloak is not possible (only hashes are stored). The shared-LDAP alternative was presented and not chosen.
