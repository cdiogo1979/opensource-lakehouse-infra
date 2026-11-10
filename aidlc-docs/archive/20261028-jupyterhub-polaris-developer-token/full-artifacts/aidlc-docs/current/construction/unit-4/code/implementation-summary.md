# Unit 4 — Implementation and Build/Test Summary

## Outcome

Generated Unit 4 source-contract tests, an explicitly opt-in live role-matrix test entry point, and updated end-to-end/operator test instructions. The approved Build and Test stage passed 82 pytest cases and 5 Hypothesis subtests, both pinned image builds, Compose validation, Python/Bash compilation, and Keycloak realm-contract JSON validation. No runtime file, service, provider, identity, grant, bucket, catalog, table, object, or volume was changed during Build and Test.

## Generated and updated artifacts

| Path | Result |
|---|---|
| `pytest.ini` | Registers integration/live markers and scopes pytest collection to `tests`. |
| `tests/integration/test_unit4_hub_journey_contract.py` | Checks approved Keycloak/Hub group admission, PKCE/password-auth configuration, developer/analyst/owner/writer role matrix, and deny-by-default behavior using pure source contracts. |
| `tests/integration/test_unit4_spark_polaris_contract.py` | Adds an opt-in pytest entry point for the existing role-matrix verifier. It skips unless `LAKEHOUSE_LIVE_ROLE_MATRIX=1`; when enabled, that verifier creates temporary role clients/principals and unique smoke-table rows and attempts cleanup. Captured output is checked for success and cleanup markers and JWT-shaped strings. |
| `aidlc-docs/current/construction/build-and-test/e2e-test-instructions.md` | Documents browser OIDC, server/home/network isolation, role outcomes, token-expiry behavior, cleanup, and safe evidence. |
| `aidlc-docs/current/construction/build-and-test/integration-test-instructions.md` | Documents source-only and opt-in live commands, test side effects, cleanup, and still-unverified provider behaviors. |
| `aidlc-docs/current/construction/build-and-test/performance-test-instructions.md` | Defines the two-user local profile, five-second STS target measurement boundary, reporting requirements, and deferred resiliency scenarios. |
| `README.md` | Reconciles the current JupyterHub Build and Test status and points to the Unit 4 results. |
| `aidlc-docs/current/construction/build-and-test/unit-4-build-and-test-summary.md` | Records the executed checks, outcome, and open evidence. |
| `aidlc-docs/current/construction/build-and-test/build-and-test-summary.md` | Identifies Unit 4 as the current Build and Test result and links prior unit records. |
| `aidlc-docs/current/construction/build-and-test/unit-test-instructions.md` | Replaces stale counts with the reproducible disposable-container pytest command. |

## Safety and execution boundaries

- Live role-matrix checks are skipped by default and require an explicit environment opt-in.
- Browser OIDC checks remain manual; no browser automation dependency was added.
- No direct inspection or output of JWTs, refresh tokens, client secrets, passwords, or temporary RustFS credentials is requested.
- The existing `scripts/verify-role-matrix.py` is reused as-is. No change to its identity, grant, bucket, catalog, or data behavior was made.
- Unit 3 gaps are not marked as passed or waived.
- The workspace was mounted read-only in the full pytest container; the live role-matrix test remained skipped because its explicit opt-in was unset.

## Test/build status

Build and Test outcome: both image builds passed; Compose validation, Python compilation, Bash syntax, and Keycloak JSON validation passed; the full pytest suite passed 82 tests with 1 explicit live-test skip and 5 Hypothesis subtests. The live role-matrix verifier passed in Unit 3 and was not repeated under its one-time authorization. Browser E2E, exact RustFS STS scope/lifetime, post-expiry refresh behavior, strict total latency, concurrency/performance, and scheduled resiliency validation remain unverified. Full results are in `aidlc-docs/current/construction/build-and-test/unit-4-build-and-test-summary.md`.

## Open verification items

- Actual RustFS 1.0.4 STS session policy and lifetime, and direct denial outside its vended scope.
- Behavior when vended-credential refresh is needed after the 300-second Keycloak user JWT expires. Current behavior is expected to fail closed; no in-session JWT renewal is implemented.
- Strict five-second end-to-end STS deadline; existing per-stage timeouts do not prove the total bound.
- Two-user live concurrency and performance measurements.
- Deferred resiliency validation date; owner remains the platform operator and the schedule is unset.

## Traceability

| Stories | Unit 4 evidence |
|---|---|
| US-01 — Keycloak sign-in | Manual browser OIDC acceptance instructions; live browser execution remains Build and Test. |
| US-02 — Isolated personal environment | Manual per-user server, home-volume, Docker-socket, and network checks. |
| US-03 — Current user identity in Spark | Manual token-expiry/new-session guidance; no bearer token inspection. |
| US-04 — Developer access | Role contract and existing opt-in live role matrix. |
| US-05 — Analyst access | Role contract and existing opt-in live role matrix. |
| US-06 — Safe operations | Redaction, cleanup, diagnostics, startup/stop, and evidence guidance. |

FR-1–FR-7 are represented by the browser, server, broker, Spark/Polaris, storage-scope, and role-matrix checks above. The currently open evidence is listed in the verification section and must remain explicit in Build and Test and Deploy Handoff.

## Build and Test scope amendment and outcome

The user clarified that this intent's objective is a running JupyterHub and completed end-to-end testing. Build and Test therefore fixed runtime blockers on that path: unsupported Hub/OAuthenticator settings, broker CA trust extension, spawner host-versus-container path validation, DockerSpawner local-image pull behavior, duplicate singleuser command invocation, missing OpenJDK security files, and Spark's three-catalog configuration. These are narrow fixes required to meet the existing approved journey; they do not change role grants, bucket/catalog data, or provider identity policy.

Final evidence: 38 JupyterHub regression tests passed in the Hub image; Compose validation passed; Keycloak, Polaris, RustFS, both databases, and JupyterHub are healthy. A temporary developer completed Keycloak authorization-code login, the production Keycloak-to-Polaris reconciliation functions, isolated Spark server creation, reads from all three environment smoke tables, a dev-only insert/delete, and denied writes in production and UAT. Temporary user, Polaris principal/role, probe row, server/home volume, and Hub auth state were cleaned up. The login was exercised at the HTTP protocol level with a test client; GUI-browser automation and home persistence across a server restart were not verified. Other remaining gaps are recorded in the Unit 4 Build and Test summary.
