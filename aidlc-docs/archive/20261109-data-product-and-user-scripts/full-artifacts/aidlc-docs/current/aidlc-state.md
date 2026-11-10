# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-09T14:38:09Z
- Current Stage: DEPLOY - Deploy
- Intent: Two operator scripts: create a new data product (buckets, catalogs/databases, roles) from a data-product name, and create a new user (group assignment is done in Keycloak).
- Intent ID: 20261109-data-product-and-user-scripts
- Previous Intent: aidlc-docs/archive/20261109-cleanup-modular-compose (closed)

## Workspace State
- Existing code: Yes.
- Languages/configuration: Python, Bash, YAML, JSON, Docker Compose.
- Build system: Docker Compose; pytest contract tests.
- Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra-v2
- Git metadata: None in this infrastructure workspace.
- Reverse Engineering Needed: Yes — focused on how the 'default' product is wired into every component.
- Reverse-engineering artifacts: aidlc-docs/current/inception/reverse-engineering/

## Code Location Rules
- Application Code: Workspace root (NEVER in aidlc-docs/)
- Documentation: aidlc-docs/ only
- Structure patterns: See code-generation.md Critical Rules

## Stage Progress
- [x] Workspace Detection — brownfield; prior intent closed and archived.
- [x] Focused Reverse Engineering — approved on 2026-11-09.
- [x] Requirements Analysis — approved on 2026-11-09.
- [x] User Stories — SKIP (operator tooling, one persona).
- [x] Workflow Planning — approved on 2026-11-09.
- [x] Application Design — approved on 2026-11-09 (incl. change request CR-1).
- [ ] Units Generation — SKIP (one unit: data-product-provisioning).
- [x] Functional Design — approved on 2026-11-09.
- [ ] NFR Requirements / NFR Design / Infrastructure Design — SKIP.
- [x] Code Generation — approved on 2026-11-09 (incl. CR-2, CR-3, CR-4).
- [x] Build and Test — approved on 2026-11-09.
- [x] Deploy — handoff approved on 2026-11-09.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q8: B) |
| Property-Based Testing | No | Requirements Analysis (Q9: C) |
| Resiliency Baseline | No | Requirements Analysis (Q10: B) |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Current Status
- Lifecycle Phase: DEPLOY
- Current Stage: Deploy
- Next Stage: Intent Closure
- Status: Deploy approved; intent closure pending separate approval.

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "current_stage": "DEPLOY",
  "intent_id": "20261109-data-product-and-user-scripts",
  "name": "Data Product and User Scripts",
  "previous_intent": "aidlc-docs/archive/20261109-cleanup-modular-compose",
  "status": "COMPACTION"
}
```
<!-- intent-lifecycle:end -->

## Open Follow-ups (after 20261109-cleanup-modular-compose)
- **Next intent**: BI access with long-lived, per-data-product Keycloak tokens.
  - One client per data product, for example `srv-default-bi`; its token lifetime is still to decide.
  - StarRocks roles come from the account's Keycloak groups; it is revoked by removing it from the groups.
  - Power BI goes through ODBC (Connector/ODBC 9.1+ `openid-token-file`, verify first).
  - The reconciler needs an exception for BI service accounts, and each client an audience mapper for `starrocks`.
- **Jenkins CI job**: restore it from `.runtime/backups/20261031-pre-reset/jenkins-home.tar.gz`, or define it as code.
- **Probe residue**: Build and Test probe data files (`sr_bt_*`) remain in the three buckets, because Polaris refuses purge.
- **Airflow developer-role drift**: the code maps `User`; the tests expect `Admin`.
- **JupyterHub broker tests** need `PYTHONPATH=infra/jupyter/hub`.
- **RustFS console**: adopt a RustFS release that bundles console v0.1.38 or later.
- **Local Docker pruning**: unused images (and earlier, stopped containers) disappeared outside the sessions. Check whether Rancher Desktop or a cleanup job prunes them.
