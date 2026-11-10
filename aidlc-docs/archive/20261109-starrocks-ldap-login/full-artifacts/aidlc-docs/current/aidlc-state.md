# AI-DLC State Tracking

## Project Information
- Project Type: Brownfield
- Start Date: 2026-11-09T19:45:02Z
- Current Stage: DEPLOY - Deploy
- Intent: Users, including service users, log in to StarRocks with their own username and password: a lightweight LDAP directory as the shared password store, Keycloak federating its users, StarRocks checking passwords against LDAP.
- Intent ID: 20261109-starrocks-ldap-login
- Previous Intent: aidlc-docs/archive/20261109-data-product-and-user-scripts (closed)

## Workspace State
- Existing code: Yes.
- Languages/configuration: Python, Bash, YAML, JSON, Docker Compose.
- Build system: Docker Compose; pytest contract tests.
- Workspace root: /Users/carlosdiogo/code_repo/opensource-lakehouse-infra-v2
- Git metadata: None in this infrastructure workspace.
- Reverse Engineering Needed: Yes — focused on user creation paths, password handling, and StarRocks authentication, plus a feasibility probe of StarRocks 4.1.7 LDAP login.
- Reverse-engineering artifacts: aidlc-docs/current/inception/reverse-engineering/

## Code Location Rules
- Application Code: Workspace root (NEVER in aidlc-docs/)
- Documentation: aidlc-docs/ only
- Structure patterns: See code-generation.md Critical Rules

## Stage Progress
- [x] Workspace Detection — brownfield; prior intent closed and archived.
- [x] Focused Reverse Engineering — approved on 2026-11-09.
- [x] Requirements Analysis — approved on 2026-11-09.
- [x] User Stories — SKIP (login method change for existing personas).
- [x] Workflow Planning — approved on 2026-11-09.
- [x] Application Design — approved on 2026-11-09.
- [ ] Units Generation — SKIP (one unit: ldap-password-login).
- [x] Functional Design — approved on 2026-11-09.
- [ ] NFR Requirements / NFR Design / Infrastructure Design — SKIP.
- [x] Code Generation — approved on 2026-11-09.
- [x] Build and Test — approved on 2026-11-09.
- [x] Deploy — handoff approved on 2026-11-09.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q5: B) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q6: B) |
| Resiliency Baseline | No | Requirements Analysis (Q7: B) |
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
  "intent_id": "20261109-starrocks-ldap-login",
  "name": "StarRocks LDAP Login",
  "previous_intent": "aidlc-docs/archive/20261109-data-product-and-user-scripts",
  "status": "COMPACTION"
}
```
<!-- intent-lifecycle:end -->

## Open Follow-ups (after 20261109-data-product-and-user-scripts)
- **Next intent candidate**: BI access with long-lived, per-data-product Keycloak tokens.
  - One client per data product, for example `srv-default-bi`; its token lifetime is still to decide.
  - StarRocks roles come from the account's Keycloak groups; it is revoked by removing it from the groups.
  - Power BI goes through ODBC (Connector/ODBC 9.1+ `openid-token-file`, verify first).
  - The reconciler needs an exception for BI service accounts, and each client an audience mapper for `starrocks`.
- **Writer workloads for other products**: the Airflow token broker writes only as `srv-default-writer`; wire other products' writer users (`srv-<p>-writer`) to their workloads.
- **Jenkins CI job**: restore it from `.runtime/backups/20261031-pre-reset/jenkins-home.tar.gz`, or define it as code.
- **Airflow developer-role drift**: `default.yaml` maps developers to `User`; `tests/airflow/test_keycloak_sso_contract.py` still expects `Admin`.
- **Probe residue**: Build and Test probe data files (`sr_bt_*`) remain in the `default` buckets, because Polaris refuses purge.
- **JupyterHub broker tests** need `PYTHONPATH=infra/jupyter/hub`.
- **RustFS console**: adopt a RustFS release that bundles console v0.1.38 or later.
- **Local Docker pruning**: unused images disappear between sessions (Rancher Desktop Kubernetes image GC; the VM disk was near its threshold). The `mysql:9.7.2` client image was re-pulled during this intent.
- **Removal backups**: `.runtime/backups/*-remove-sales` (three test runs) can be deleted when no longer needed.
