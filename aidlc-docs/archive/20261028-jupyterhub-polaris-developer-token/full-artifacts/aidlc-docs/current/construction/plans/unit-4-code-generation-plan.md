# Unit 4 Code Generation Plan — End-to-End Verification and Operations

## Purpose

Prepare cross-component acceptance checks and operator guidance for the approved JupyterHub developer and analyst journeys. Unit 4 consumes the running implementations from Units 1–3; it does not add a new production service or change authorization policy.

## Unit context and design-stage assessment

- **Stories:** US-01–US-06. Unit 4 is the verification owner for all stories and the operations-documentation owner for US-06.
- **Requirements:** FR-1–FR-7 and approved security, token-lifecycle, storage-scope, latency, isolation, and operational requirements.
- **Dependencies:** Units 1–3 implementations and focused checks; local Compose stack; Keycloak OIDC realm; Polaris role mappings; RustFS test buckets and smoke tables.
- **Conditional design stages:** Functional Design, NFR Requirements/Design, and Infrastructure Design are skipped for Unit 4. Unit 4 adds no business behavior, service boundary, NFR, or deployment resource; it verifies the approved contracts and writes operational guidance. The approved Unit-of-Work, story map, and Units 1–3 designs are the source of expected behavior.
- **Unit 3 review:** Build, static, live role-matrix, cleanup, and Polaris listener-isolation checks passed and were approved. The user has not waived Unit 3 gaps. Unit 4 must verify them where feasible and report any remaining limitation as unverified.

## Approved behavior and safety boundaries

- Developer: read production, UAT, and dev; write only dev.
- Analyst: read production only; no writes.
- Owner and writer: verify only the already approved product role behavior documented in the role-matrix contract.
- Browser authentication uses the existing Keycloak realm and OIDC client; test users must be temporary and removed after verification.
- Spark receives the authenticated user's access token through the Hub broker; tokens, refresh tokens, and temporary object credentials must not appear in logs, process arguments, durable config, or test reports.
- Spark must use Polaris-vended RustFS credentials. Tests may create uniquely named temporary rows/objects only in approved smoke resources and must restore or remove only what they create.
- No bucket/catalog/database reset, persistent grant change, existing-user membership change, secret rotation, image/version upgrade, public endpoint exposure, or deployment is included.
- Running/reconfiguring the local stack and temporary OIDC/test data are within the previously approved local Build and Test scope. A new persistent identity or policy/grant change is not authorized by this plan.

## Verification gaps to address or report

1. Observe the actual RustFS STS credential lifetime and session policy returned through Polaris; attempt read/write outside the approved resource scope and verify denial without printing credentials.
2. Exercise credential use and refresh behavior against the pinned Polaris/RustFS/Iceberg versions. The current 300-second Keycloak user JWT expires before the user-approved 3600-second storage credential, and Spark OAuth renewal is disabled. Verify the expected fail-closed behavior when Polaris needs the expired JWT; do not claim successful in-session user-token renewal unless implementation evidence supports it.
3. Measure end-to-end STS acquisition latency against the five-second target and state the measurement boundary. Existing per-stage timeouts do not prove a total deadline.
4. Exercise two independent users concurrently and run the applicable local performance checks. Do not infer production capacity from the two-user profile.
5. Preserve deferred resiliency scenarios and operator owner; record that a validation date is still unset unless the platform operator supplies one.

## Code and documentation targets

- New `tests/integration/test_unit4_hub_journey_contract.py` — integration-facing contract checks for OIDC admission configuration, current-user server binding, token-safe diagnostics, and the role-to-journey expectations. Reuse existing unit helpers; never expose fixture token values.
- New `tests/integration/test_unit4_spark_polaris_contract.py` — opt-in local integration checks for Spark-to-Polaris authentication, developer/analyst allow-deny matrix, table locations, vended RustFS access, scope denial, credential expiry behavior, and bounded latency observations. Mark provider-mutating checks explicitly and require a live-stack opt-in.
- Existing `infra/spark-bootstrap/verify_role_matrix.py` — extend only if needed to capture safe STS duration/scope/refresh observations and independent-user concurrency; preserve unique probe naming and cleanup of only test-created data/identities.
- Existing `tests/` test configuration or `pytest.ini` — add explicit integration markers and safe defaults so live-provider checks do not run in ordinary source-only CI.
- Existing `aidlc-docs/current/construction/build-and-test/e2e-test-instructions.md` — document browser OIDC steps for developer and analyst, unapproved-group denial, server/home isolation, Spark authorization, expiry/failure behavior, and cleanup. Browser interaction remains a manual operator step unless the approved plan later adds a browser automation dependency.
- Existing `aidlc-docs/current/construction/build-and-test/integration-test-instructions.md` — document stack readiness, live integration commands, temporary resource boundaries, safe output review, and cleanup verification.
- Existing `aidlc-docs/current/construction/build-and-test/performance-test-instructions.md` — record the two-user local profile, STS timing measurement method, acceptance threshold, and limits.
- Existing `README.md` — add or reconcile operational start/stop, onboarding, troubleshooting, failure behavior, and rollback guidance without duplicating contradictory instructions.
- `aidlc-docs/current/construction/unit-4/code/implementation-summary.md` — record generated artifacts, test results when Build and Test is run, evidence, remaining gaps, and story/requirement traceability.

Do not change application production logic in this plan. If verification demonstrates a product-code defect, record evidence and prepare a separate reviewed plan amendment before changing Units 1–3 implementation.

## Ordered generation steps

### Step 1 — Finalize test boundaries and harness

- [x] Define source-only versus opt-in provider integration markers and safe defaults in `pytest.ini` and the live role-matrix wrapper test.
- [x] Reuse the existing unique role-matrix probe identifiers and cleanup behavior; add output checks for JWT-shaped strings and secret-field labels.
- [x] Reuse the existing role-matrix verifier without changing its identity/data behavior; do not add persistent identities or alter existing membership/grants.

### Step 2 — Add cross-component integration contracts

- [x] Add Hub journey and role/server contract checks; browser and home/network isolation remain manual Build and Test checks.
- [x] Add a gated Spark/Polaris role-matrix check that reuses the existing allow/deny and table-location verifier. Exact direct STS scope/lifetime and expiry behavior are documented as unverified where the pinned interfaces are not safely exposed by current test code.
- [x] Document an independent two-user concurrency procedure in the performance instructions; no automated load harness is added.
- [x] Ensure provider-mutating role-matrix execution skips unless its explicit `LAKEHOUSE_LIVE_ROLE_MATRIX=1` opt-in is set.

### Step 3 — Complete operator verification instructions

- [x] Update end-to-end, integration, and performance test instructions with ordered setup, expected outcomes, redaction checks, and cleanup.
- [x] Include browser OIDC verification and unapproved-group denial without storing passwords or tokens in test artifacts.
- [x] Include RustFS STS lifetime/scope observation and expired-user-JWT expected behavior; distinguish successful credential refresh from expected fail-closed rejection.
- [x] Record deferred resiliency scenario owner and explicitly unset validation date.

### Step 4 — Reconcile operator documentation and traceability

- [x] Update README operating guidance to match the verified Unit 1–3 behavior and identify the remaining evidence.
- [x] Map verification artifacts to US-01–US-06 and FR-1–FR-7 in the implementation summary.
- [x] Create Unit 4 implementation summary with generated paths, security boundaries, and Build and Test follow-up.
- [x] Update plan progress and AI-DLC state to identify the review gate and unrun tests.

### Step 5 — Review and Build and Test handoff

- [x] Review generated integration checks for opt-in behavior, cleanup safety, and secret redaction.
- [x] Do not execute tests, start/reconfigure services, or mutate provider/test data during Code Generation.
- [x] Hand provider tests to the separate Build and Test gate; report all passed and unverified results independently.

## Approval gate

## Build and Test scope amendment — runtime blockers

The user clarified on 2026-10-28 that the intent's objective is a running JupyterHub and completed end-to-end testing, which had not yet been achieved. Starting the approved stack exposed three runtime issues: the generated broker CA lacked an Authority Key Identifier rejected by Python's TLS verifier; Hub configured an unsupported active-user limit name; and OAuthenticator configured an unsupported userinfo HTTP-method name. To complete the stated objective, Build and Test includes narrowly scoped corrections to `jupyterhub_config.py` and `prepare-jupyterhub-broker-certificates.py`, with regression tests. The existing broker CA will be explicitly rotated only after confirming no user servers are active; Hub auth-state, provider data volumes, grants, catalogs, buckets, and user identities are preserved. Continue the live browser-to-Spark checks and report any remaining limitation.

**Generation result:** The planned test/configuration and operator-documentation artifacts were generated and approved by the user on 2026-10-28. Unit 3 gaps remain visible and unverified.

**Build and Test result:** 82 pytest cases and 5 Hypothesis subtests passed; one opt-in live role-matrix wrapper skipped by default. The later Hub regression suite passed 38 tests, and live OIDC/Spark journeys and authorization checks passed. The user reports GUI browser testing complete. Follow-up checks verified Polaris's one-hour credential lifetime, sampled RustFS read scope, and fail-closed JWT expiry requiring a new Spark session. Other operation-level scope, a strict total-latency guarantee, concurrent Spark workload/performance, resiliency scheduling, and supply-chain checks remain accepted limitations. See `aidlc-docs/current/construction/build-and-test/unit-4-build-and-test-summary.md`.

**Review gate:** The user considers Build and Test complete with the limitations above recorded. Skipped and unverified checks are not represented as passed.

## Build and Test scope amendment — complete the stated intent outcome

On 2026-10-28 the user clarified that the intent's objective is to leave JupyterHub running and complete an end-to-end developer journey; a source-only suite and image build did not satisfy that objective. This clarification authorizes narrow runtime fixes discovered along the approved local path, superseding the source-generation boundary above only for defects blocking this E2E. The fixes covered supported Hub/OAuthenticator options, broker certificate trust, host bind-mount validation, local singleuser image pull behavior, the singleuser entrypoint command, Java runtime configuration, and Spark catalog configuration. Existing provider data, user grants, buckets, catalogs, and unrelated identities remain outside scope. A temporary developer and matching Polaris principal/role, unique test row, user server/home volume, and Hub auth state are allowed only for this test and must be removed afterward.

**Final Build and Test result:** The user journey passed using the production Keycloak-to-Polaris reconciliation functions, and all six stack services were healthy with JupyterHub left running. Spark read all three smoke tables, wrote and cleaned one dev row, and was denied writes in prod and UAT. Thirty-eight final JupyterHub regression tests and Compose validation passed. The user reports GUI browser testing complete. Follow-up checks verified one-hour credentials, sampled table-prefix scope, and fail-closed behavior after JWT expiry. Remaining limitations are recorded in the Build and Test summary; the user considers testing complete.
