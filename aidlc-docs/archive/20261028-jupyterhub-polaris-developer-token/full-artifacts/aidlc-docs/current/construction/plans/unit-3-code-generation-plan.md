# Unit 3 Code Generation Plan — Polaris Authorization and RustFS Credential Vending

## Purpose

Implement the approved Unit 3 outcome: Polaris authorizes each user's existing Keycloak identity and roles, and vends short-lived RustFS credentials for authorized catalog locations. Preserve the approved developer/analyst access matrix, current three-catalog mapping, local Compose topology, and no-reset boundary. This plan is the single source of truth for Unit 3 Code Generation. Test sources may be added as listed; execution and live provider checks belong to Build and Test.

## Unit context and contracts

- **Stories:** US-04 (developer reads all environments and writes dev only), US-05 (analyst reads production only and never writes), and US-06 (operator diagnoses outcomes without seeing credentials).
- **Requirements:** Unit 3 identity, role, operation, location, short-lived credential, refresh, redaction, latency, and two-user concurrency requirements.
- **Dependencies:** Approved Unit 1 Keycloak OIDC and isolated Spark runtime; approved Unit 2 Hub broker and exact user JWT handoff; Unit 3 Functional, NFR, NFR Design, and Infrastructure Design; existing Polaris/RustFS services and three catalog grants.
- **Authorization contract:** Polaris validates issuer, signature, expiry, explicit `polaris` audience, verified `preferred_username`, and only allow-listed role claims. Developer reads prod/UAT/dev and mutates dev only. Analyst reads prod only and cannot mutate. No shared writer identity substitutes for a user.
- **Credential contract:** Polaris vends only short-lived credentials after authorization. Spark uses the supported Iceberg/Polaris credential-refresh behavior under the same user's JWT and resource scope. No static or root-key fallback.
- **Infrastructure contract:** Keep Polaris port 8181 loopback-published, management port 8182 unpublished and loopback-bound, current `core`/`data-access` networks, and current read-only runtime application-properties mount. Keep credential duration/cache targets at 900/600 seconds and STS end-to-end deadline at 5 seconds, subject to exact pinned-image compatibility checks.
- **Storage contract:** Preserve `lakehouse` → `bucket-default`, `lakehouse_uat` → `bucket-default-uat`, and `lakehouse_dev` → `bucket-default-dev`. Table path convention remains `bucket/catalog/db/table`. No bucket, catalog, grant, identity, or data reset is included.
- **Test identity boundary:** Generate tests and verification code only. Build and Test may use already approved test identities and clean up only their own probes. If a new analyst identity is required, request the previously specified separate approval before creating it.
- **Out of scope:** No new service, monitoring backend, role/grant redesign, broad security-baseline controls, Keycloak group lifecycle change, credential broker change, version upgrade, migration, or runtime deployment during Code Generation.

## Code targets

Modify existing files in place and add only the listed focused test/verification targets:

- `infra/polaris/oidc.properties` — retain and verify current issuer/JWKS, principal, audience, and role-claim mappings; add the supported Polaris management-listener host setting only after the pinned-image property and behavior are confirmed.
- `scripts/prepare-lakehouse-runtime.py` — render the approved non-secret credential duration/cache settings into the existing generated Polaris runtime properties; preserve protected secret assembly, atomic writes, and restrictive permissions. Do not directly alter `.runtime` during Code Generation.
- `docker-compose.yml` — only if pinned Polaris behavior requires a Compose-level management binding; keep REST publication on loopback, do not publish port 8182, and preserve network memberships and mounts.
- `infra/jupyter/singleuser/lakehouse_spark.py` — update only the Polaris/Iceberg temporary credential refresh configuration after verifying exact Iceberg 1.8.1 behavior. Keep the Hub-provided user JWT runtime-only and do not enable OAuth refresh-token sharing with Spark.
- `infra/jupyter/singleuser/spark-defaults.conf` — only for verified, non-secret catalog defaults or safe redaction settings required by the supported refresh contract.
- Existing `infra/spark-bootstrap/verify_role_matrix.py` — extend non-destructive verification for expected catalog/database/table path and vended-credential behavior where the pinned interfaces make this observable. Preserve probe cleanup and never print token or temporary credential values.
- New `tests/polaris/test_unit3_runtime_config.py` — runtime property generation, safe output, duration/cache invariants, and no secret regression.
- New `tests/polaris/test_unit3_authorization_properties.py` — Hypothesis properties for the role/environment/operation oracle, union-of-grants, deny-by-default, and analyst no-write invariants using reusable domain strategies.
- New `tests/polaris/test_unit3_location_properties.py` — Hypothesis properties for valid `bucket/catalog/db/table` resolution, approved catalog-to-bucket mapping, and rejection of malformed, duplicated, traversal, or cross-environment paths.
- New `tests/polaris/test_unit3_runtime_properties.py` — Hypothesis properties for positive credential/cache settings, cache strictly shorter than duration, and safe generated configuration output.
- New `tests/requirements-pbt.txt` — pinned Hypothesis test dependency, installed only in the test environment and not in runtime images.
- New root `Jenkinsfile` — add a Jenkins Python test stage for the repository test suite, install the test-only requirements, and set/log a reproducible per-build Hypothesis seed. Keep pipeline scope limited to validation; it does not deploy or mutate services.
- New `tests/polaris/test_unit3_compose_contract.py` — loopback REST publication, no host-published management port, read-only runtime mount, and approved network-boundary contracts.
- New `tests/jupyterhub/test_unit3_spark_credential_refresh.py` — pinned refresh configuration, same-user JWT preservation, no static storage fallback, in-memory-only token handling, and redacted failures.
- `README.md` — document the operator diagnostics and safe behavior only if commands or runtime preparation behavior change.
- `aidlc-docs/current/construction/unit-3/code/implementation-summary.md` — record generated changes, compatibility evidence, unresolved gaps, and US/requirement traceability.

If an exact configuration key, refresh interface, STS deadline, or scope behavior cannot be verified for the pinned versions, stop that implementation step and record a compatibility gap for review. Do not guess configuration names, broaden credentials, weaken the approved authorization behavior, or change pinned versions without a reviewed plan revision.

## Ordered generation steps

### Step 1 — Verify pinned compatibility before editing runtime configuration

- [x] Confirm official Polaris 1.8.0 duration/cache property names and integer-second syntax. Effective values in the generated runtime file remain a Build and Test check.
- [x] Confirm Quarkus's management-host property and configure loopback while retaining the healthcheck. Actual binding and reachability remain a pinned-image runtime check.
- [ ] Confirm RustFS 1.0.4 supports the requested STS duration and the exact location/operation scope Polaris can request. Current RustFS docs confirm a 15-minute minimum, but the pinned runtime and returned session scope remain unverified.
- [x] Confirm the supported Polaris per-stage storage timeout and finite-pool properties. A strict five-second end-to-end deadline is not provided by the documented properties; the gap is recorded rather than claiming the target is enforced.
- [x] Confirm Iceberg 1.8.1's Polaris REST-vended credential refresh and distinguish it from OAuth access-token refresh. Preserve the existing Hub token contract; the original 300-second JWT will fail closed after expiry.
- [x] Record source/version evidence and unresolved compatibility gaps in the implementation summary.

### Step 2 — Update safe Polaris runtime configuration generation

- [x] Set the user-approved 3600-second credential duration and 600-second cache target through the existing generated application-properties merge; verify the effective vended lifetime in Build and Test.
- [x] Add the verified Quarkus management-listener loopback setting to the Polaris properties template.
- [x] Preserve the existing read-only Compose mount, secret inputs, atomic generation, file modes, OIDC settings, and redacted helper output.
- [x] Do not edit or print any `.runtime/credentials` or `.runtime/container-mounts` file during Code Generation; Build and Test owns runtime preparation and service restart.

### Step 3 — Preserve and verify Polaris claim and grant mapping

- [x] Preserve the canonical issuer/JWKS, explicit `polaris` audience, `preferred_username`, and existing allow-listed role-claim mapping in `infra/polaris/oidc.properties`.
- [x] Preserve existing grants and principal mappings; no mapping or grant change was required by compatibility review.
- [x] Add source-level authorization/path properties and focused tests for deny-by-default. Actual Polaris fail-closed behavior remains a live verification gate; no identities/groups/grants were changed.

### Step 4 — Configure the supported Spark/Iceberg credential refresh path

- [x] Confirm the existing Iceberg 1.8.1 REST vended-credential refresh endpoint mechanism; document it distinctly from OAuth refresh.
- [x] Keep the exact user access JWT in transient Spark client state; Spark receives no refresh token or Hub client secret.
- [x] Keep Polaris OAuth-token renewal disabled; do not substitute a service/writer identity.
- [x] Preserve fail-closed semantics and no persistent/root fallback. Runtime expiration, rejection, and mutation retry behavior remain Build and Test verification gates.

### Step 5 — Add focused source tests

- [x] Add Polaris runtime-property tests for exact duration/cache values, their invariant, safe diagnostic output, and OIDC/unrelated-property preservation.
- [x] Add Compose contract tests for 8181 loopback-only publication, unpublished 8182 management port, read-only config mount, and network boundary.
- [x] Add Spark credential-refresh contract tests for same-user JWT continuity, OAuth/vended refresh separation, and no static/root fallback.
- [x] Implement Hypothesis properties for role authorization, role union, deny-by-default, analyst no-write, exact approved locations, adversarial segments, and runtime credential/cache constraints.
- [x] Use structured role/environment/operation and Unicode-safe path strategies, including unknown/empty roles, traversal, duplicate database segments, and cross-environment buckets.
- [x] Keep Hypothesis shrinking enabled; Jenkins uses a logged build-number seed and archives pytest output. Named developer/analyst examples accompany properties. No defects were discovered in this stage because tests were not executed.
- [x] Add a Jenkins test-only stage with the build-number seed, test-only dependencies, and archived log; no deployment behavior.
- [x] Evaluate the available PBT categories against generated logic: path construction is checked with expected-location round-trip properties; stateful cache/refresh behavior remains N/A for local PBT because it belongs to external Polaris/Iceberg state; serialization and recursive logic remain N/A because no such local transform/algorithm was introduced; authorization uses a reference oracle. The repository does not contain a glossary mapping numeric PBT-02..06 identifiers to categories, so the source summary records this traceability limit rather than assigning invented meanings.
- [x] Add independent source assertions for all current catalog/bucket mappings and expected `bucket/catalog/db/table` paths; no live object changed.
- [x] Keep tests source-only in Code Generation; none were executed.

### Step 6 — Resiliency scope and failure-validation handoff

- [x] Add documented per-stage Polaris timeouts and a finite pool; preserve health check, fail-closed authorization/fallback behavior, and no mutation replay. One-safe-read retry is not newly implemented; default retry behavior must be inspected in Build and Test.
- [x] Keep management endpoints unpublished and document container-local readiness diagnostics; no monitoring service or public management route added.
- [x] Record production-only HA/DR/scale/SLA/rollout and formal change/incident controls as N/A for the local proof-of-concept.
- [ ] Record deferred resiliency scenarios and owner; platform operator is named, but a scheduled validation date remains to be set before the separate validation activity.
- [ ] The source artifacts refer to RESILIENCY-01 through RESILIENCY-15 without defining each ID's requirement text. Summary records the available control coverage and this traceability gap; exact per-ID mapping needs the originating extension glossary.

### Step 7 — Extend focused live verification code and document operations

- [x] Extend `verify_role_matrix.py` to verify actual existing role operations and expected table location; refresh behavior and unauthorized environment checks remain live validation.
- [x] Preserve existing isolated probe identifiers and cleanup behavior; no deletion/reset/identity/grant changes.
- [x] Keep JWT/temporary storage credentials out of output and diagnostics.
- [x] Document container-local management readiness diagnostics; no host/user-network management route or metrics service added.

### Step 8 — Record traceability and generation boundary

- [x] Create the implementation summary with generated files, pinned-version documentation evidence, test inventory, compatibility gaps, and US-04/05/06 traceability.
- [x] Update completed plan items and `aidlc-state.md` to distinguish generated artifacts from unexecuted tests and unverified runtime behavior.
- [x] Do not run tests, build images, prepare runtime files, restart services, or mutate provider state during Code Generation; all remained untouched for Build and Test after code review.

## Review and approval gate

This plan incorporates the answered PBT, Resiliency, and CI-provider clarifications. The user approved the plan on 2026-10-28 and the listed Unit 3 source/test/CI/documentation artifacts have been generated. Test execution, runtime preparation/restart, provider identity or grant changes, new analyst identity creation, data/catalog/bucket resets, version upgrades, deployment, and public management exposure remain out of scope. Build and Test is the next gate after generated artifacts are reviewed.
