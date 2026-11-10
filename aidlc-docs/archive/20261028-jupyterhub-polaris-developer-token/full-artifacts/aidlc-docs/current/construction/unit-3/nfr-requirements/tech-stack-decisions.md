# Unit 3 Technology Decisions — Polaris Authorization and RustFS Credential Vending

## Decisions

| Concern | Decision | Rationale / constraint |
|---|---|---|
| Authorization service | Retain the existing Polaris 1.8.0 deployment | Polaris remains the catalog authorization and credential-vending authority; no Ranger or additional policy service is introduced. |
| Identity contract | Use the approved Keycloak JWT contract: canonical issuer, explicit `polaris` audience, verified username, and allow-listed developer/analyst role claims | Preserves the existing principal/role mapping and user identity passed by Unit 2. |
| Storage credential mechanism | Use Polaris S3 credential vending to RustFS STS; no Spark root/bootstrap keys | Keeps direct object access temporary and scoped to the authorized user/resource. Confirm against the pinned RustFS implementation before claiming live success. |
| Vended credential duration | Target 3600 seconds; credential cache target 600 seconds | User-approved one-hour lifetime; cache remains shorter than validity. Validate actual Polaris 1.8.0 and RustFS 1.0.4 behavior in Build and Test. |
| Credential renewal | Use Iceberg REST credential refresh with pinned Iceberg 1.8.1/Spark 3.5.5 where supported | Avoids putting long-lived storage keys in Spark. Failure requires operation failure/new session, never static fallback. |
| Authorization model | Existing Polaris principal roles and per-catalog grants; dual approved roles use union-of-grants | No grant or catalog changes are part of NFR requirements. Operation and discovery semantics are defined in Unit 3 Functional Design. |
| Resilience | Bounded retry for safe reads only; no automatic replay of ambiguous mutations | Prevents unsafe duplicate writes and identity/policy fallback. |
| Audit/metrics | Safe structured decision events and aggregate bounded-label metrics | Supports access diagnosis while excluding bearer credentials and data payloads. |
| Deployment topology | Existing single local Compose Polaris and RustFS services | No HA, new service, database, queue, or external observability backend is added. |
| Property-based testing | Hypothesis, pinned as a test-only dependency | Supports structured Python strategies, shrinking, deterministic replay, and pytest integration. It is installed only in the test environment, not in service images. |

## Implementation constraints

- Preserve the existing catalog, bucket, namespace, role, and grant setup. This unit does not authorize access-control or data resets.
- Do not replace the end-user JWT with a Polaris bootstrap token or `write-service-account`.
- Do not pass root/bootstrap RustFS credentials into Spark containers.
- Avoid exact Polaris configuration keys in implementation until verified against the pinned image and its generated configuration reference.
- Treat latency and expiry values as requirements to measure; do not report them as achieved until tests demonstrate them.
- Property-based tests complement named example tests. Hypothesis failures must report a replayable seed and minimized counterexample; CI integration remains subject to the CI-provider clarification in Unit 3 Code Generation Planning.

## Deferred to NFR Design and Infrastructure Design

NFR Design will select the control points and patterns for authorization decision metrics, credential scope/refresh validation, safe retries, and failure reporting. Infrastructure Design will map Polaris/RustFS limits, health dependencies, configuration mounts, and observability to the local Compose stack. Any needed image/version change must be justified by a demonstrated compatibility gap and reviewed before implementation.
