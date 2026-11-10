# AI-DLC State Tracking

## Project Information
- **Project Type**: Brownfield
- **Start Date**: 2026-10-28
- **Current Stage**: CLOSED — Intent archived
- **Intent**: Authenticate developers and analysts to JupyterHub through Keycloak OIDC, forward each user's access-token JWT to their isolated Spark execution, and use Polaris RBAC and RustFS credential vending for data access.
- **Intent ID**: `20261028-jupyterhub-polaris-developer-token`
- **Previous Intent**: `aidlc-docs/archive/20261028-polaris-database-path-layout/` (closed and preserved)

## Workspace State
- **Existing Code**: Yes; the active local platform includes Keycloak, Polaris, RustFS, Spark, and the JupyterHub service defined in the main Compose stack.
- **Programming Languages / Configuration**: Python, Bash, SQL, YAML, Dockerfiles, Spark configuration
- **Build System**: Docker Compose and Python tooling
- **Workspace Root**: `/Users/carlosdiogo/code_repo/opensource-lakehouse-infra-v2`
- **Focused reverse engineering**: Existing Keycloak realm `lakehouse` defines `role-default-developer`; Polaris maps the username claim and the `resource_access/polaris/roles` claim, and the existing developer grants allow read across environments and writes to dev only. Human access tokens are configured for 300 seconds. JupyterHub OIDC, per-user Spark servers, and the token broker are implemented in the main Compose stack; previous FreeIPA-based Jupyter configuration is retained only in the prior intent archive. Polaris's issuer is `http://keycloak.localhost:8080/realms/lakehouse`, while service-to-service JWKS resolution uses Docker service DNS.

## Extension Configuration
- **Security Baseline**: Disabled by explicit user choice during Requirements Analysis. Required OIDC, token, least-privilege, and isolation controls remain in scope.
- **Property-Based Testing**: Full enforcement approved. Hypothesis properties are defined in Unit 3 Functional Design and planned for role authorization, resource paths, and runtime credential/cache invariants. Jenkins is selected for CI integration with seed reporting.
- **Resiliency Baseline**: Applicable local timeout, bounded-pool, health, and failure-containment controls are in scope. Production-only resilience and formal change/incident controls are N/A for the local proof-of-concept. Resiliency test execution is deferred to a separately scheduled validation activity; scenarios and named owner/date are required in the Build and Test / Deploy Handoff.

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "archive": "aidlc-docs/archive/20261028-jupyterhub-polaris-developer-token",
  "current_stage": "CLOSED",
  "intent_id": "20261028-jupyterhub-polaris-developer-token",
  "previous_intent": "aidlc-docs/archive/20261028-polaris-database-path-layout",
  "status": "CLOSED",
  "summary": "The user approved the Deploy Handoff and closed this intent. The developer OIDC-to-JupyterHub-to-Spark/Polaris/RustFS journey and analyst production-only access passed; GUI browser testing was user-confirmed complete. Polaris one-hour vended credentials, sampled RustFS table-prefix read scope, fail-closed JWT expiry requiring a new Spark session, concurrent server startup, and home persistence were verified. Accepted limitations remain documented and were not represented as passing: other S3 operations, automatic in-session JWT renewal, strict five-second STS latency/p95, concurrent Spark workload/performance, scheduled resiliency validation, and complete dependency lock/security scanning. Temporary test resources were cleaned up. The local deploy handoff is archived; no production deployment or external exposure occurred.",
  "verification_outcome": "CLOSED_WITH_ACCEPTED_LIMITATIONS"
}
```
<!-- intent-lifecycle:end -->

## Stage Progress
- [x] Prior intent closed and preserved under `aidlc-docs/archive/20261028-polaris-database-path-layout/`.
- [x] Workspace detection and focused reverse engineering.
- [x] Requirements verification: all questions answered and incorporated; user approved requirements.
- [x] Workflow planning: user approved the plan and continued.
- [x] User Stories: six mapped stories and three personas generated; user approved and continued.
- [x] Application Design: plan and five design artifacts approved.
- [x] Units Generation: four units, dependency matrix, and complete story/requirement map approved.
- [x] Construction Unit 1 — Functional Design: business logic, business rules, and domain entities approved.
- [x] Construction Unit 1 — NFR Requirements: local capacity, performance, availability, security, and technology decisions approved.
- [x] Construction Unit 1 — NFR Design: patterns and logical components approved.
- [x] Construction Unit 1 — Infrastructure Design: local Compose mapping and deployment architecture approved.
- [x] Construction Unit 1 — Code Generation Planning and Generation: plan approved, implementation and source-only tests generated and reviewed.
- [x] Construction Unit 1 — Build and Test: 20 focused source tests and both image builds passed; user accepted the documented full-lock, live integration, performance, and E2E verification gaps as a Unit 1 waiver. They remain unverified, not passed.
- [x] Construction Unit 2 — Functional Design Planning: clarification answers are specific and recorded.
- [x] Construction Unit 2 — Functional Design: user approved the artifacts and instructed continuation.
- [x] Construction Unit 2 — Functional Design: broker identity binding, token freshness/refresh, concurrency, Spark handoff, failure, and domain artifacts generated and approved.
- [x] Construction Unit 2 — NFR Requirements Planning: all five recommended answers accepted and recorded.
- [x] Construction Unit 2 — NFR Requirements: requirements and technology decisions generated and approved.
- [x] Construction Unit 2 — NFR Design Planning: internal TLS listener, certificate lifecycle, and observability choices answered.
- [x] Construction Unit 2 — NFR Design: patterns and logical components generated and approved.
- [x] Construction Unit 2 — Infrastructure Design Planning: listener binding, certificate file/mount layout, trust delivery, and startup/rotation choices answered.
- [x] Construction Unit 2 — Infrastructure Design: deployment artifacts generated and approved.
- [x] Construction Unit 2 — Code Generation Planning: implementation plan approved.
- [x] Construction Unit 2 — Code Generation: broker, certificate/network integration, Spark handoff, focused test sources, and docs generated and reviewed.
- [x] Construction Unit 2 — Build and Test: 34 JupyterHub tests, 6 Keycloak contract tests, both image builds, Compose rendering, Python compilation, and shell syntax passed; live integration/performance and full dependency lock remain open.
- [x] Construction Unit 3 — Functional Design Planning: user approved all four recommended answers.
- [x] Construction Unit 3 — Functional Design: authorization, operation, credential-vending, failure, and domain artifacts generated and approved.
- [x] Construction Unit 3 — NFR Requirements Planning: user approved all five recommended answers.
- [x] Construction Unit 3 — NFR Requirements: NFR requirements and technology decisions generated and approved.
- [x] Construction Unit 3 — NFR Design Planning: user approved all five recommended answers.
- [x] Construction Unit 3 — NFR Design: patterns and logical components generated and approved.
- [x] Construction Unit 3 — Infrastructure Design Planning: user approved all four recommended choices for Polaris runtime config, management reachability, STS bounds, and storage-scope verification.
- [x] Construction Unit 3 — Infrastructure Design: artifacts reviewed and approved; pinned-image configuration and runtime behavior remain verification gates.
- [x] Construction Unit 3 — Code Generation Planning: PBT, Resiliency, and Jenkins answers incorporated; user approved the complete plan.
- [x] Construction Unit 3 — Code Generation: Polaris source configuration, role/path oracle and verifier, Spark credential-refresh contract, focused test sources, Jenkins pipeline, README guidance, and implementation summary generated. No tests/build/runtime/provider changes performed; see the summary for compatibility gaps.
- [x] Construction Unit 3 — Build and Test: 75 pytest cases plus 5 Hypothesis subtests passed with seed `20261028`; both images, Compose rendering, static checks, and local role/path/config contracts passed. Live role matrix and management listener isolation passed. Follow-up checks verified one-hour Polaris credentials, sampled table-prefix reads and cross-environment denial, plus fail-closed JWT expiry behavior. User considers testing complete with the remaining limitations documented in `construction/build-and-test/unit-3-build-and-test-summary.md`.
- [x] Construction Unit 4 — Code Generation Planning and Generation: plan approved; source-contract tests, opt-in live role-matrix wrapper, end-to-end/integration/performance instructions, README updates, and implementation summary generated. Tests and runtime/provider operations were not run.
- [x] Construction Unit 4 — Code Generation Review: user approved generated artifacts and continued to Build and Test.
- [x] Construction Unit 4 — Build and Test execution: 82 pytest cases plus 5 Hypothesis subtests passed (one opt-in wrapper skipped), and the final Hub regression suite passed 38 tests. The Keycloak-to-JupyterHub-to-Spark/Polaris/RustFS developer journey passed, with follow-up developer/analyst authorization, concurrent server startup, and home persistence checks. The user reports GUI-browser verification complete. Follow-up checks verified one-hour Polaris credentials and sampled RustFS scope; the user confirmed expired JWTs require a new Spark session. Temporary identities, principals/assignments, Hub auth state, test containers, and home volumes were cleaned up. See `construction/build-and-test/unit-4-build-and-test-summary.md` for accepted limitations.
- [x] Construction Unit 4 — Build and Test Review: user considers testing complete with accepted limitations recorded in the Unit 4 and composite summaries.
- [x] Deploy Handoff: local operator guide approved; startup/bootstrap, URLs, user enrollment, credential behavior, backup, rollback boundaries, test evidence, and accepted limitations are documented.
- [x] Intent closure: user approved the Deploy Handoff; final current artifacts and relevant source/config/test snapshot preserved under `aidlc-docs/archive/20261028-jupyterhub-polaris-developer-token/`.

## Current Status

Unit 1 verification gaps were explicitly waived by the user; they remain waived only for Unit 1. Unit 2 and Unit 3 Build and Test results are recorded in their stage summaries. Unit 3's one-hour Polaris credential lifetime, sampled RustFS read scope, role matrix, management-listener isolation, and fail-closed post-expiry behavior are verified. The user considers testing complete with strict total latency, complete S3-operation scope, performance/concurrency, and resiliency follow-up limitations accepted and documented.

Intent `20261028-jupyterhub-polaris-developer-token` is closed after user approval of the Deploy Handoff. Build and Test and the primary JupyterHub developer/analyst journeys are complete. The handoff and relevant current artifacts/source/config/test snapshot are preserved at `aidlc-docs/archive/20261028-jupyterhub-polaris-developer-token/`. Known limitations remain visible as accepted, not passed. No production deployment or external exposure occurred.
