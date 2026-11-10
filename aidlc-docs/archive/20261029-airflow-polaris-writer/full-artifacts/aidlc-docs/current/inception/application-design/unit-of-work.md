# Unit of Work — Airflow Polaris Writer Identity

## Decomposition principles

- Use the existing application component boundaries as unit boundaries.
- Keep the writer service identity separate from human Jupyter identities.
- Establish the broker contract before implementing its Spark consumer.
- The v2 infrastructure repository owns the canonical shared runtime/provider source and pinned build. The workload repository consumes that build and retains repo-specific DAG/Spark integration changes.
- Preserve the two approved Bundles. Verify runtime only for the main/production Bundle.

## Unit 1 — Airflow writer identity and broker

**Purpose:** Bring Airflow execution into the v2 platform and provide a private, run-scoped mechanism to issue and renew writer tokens for ephemeral Spark applications.

**Owning components:** Airflow control plane, Airflow writer token broker, and Bundle-to-Spark orchestration.

**Repository responsibilities:**

- `opensource-lakehouse-infra-v2`: Airflow Compose deployment, broker service, secret configuration, TLS/network boundary, health and operational configuration.
- `opensource-lakehouse`: DAG factory changes for run registration, Spark startup inputs, and all-outcomes cleanup/revocation. Keep Bundle definitions and workload entry points unchanged.

**Responsibilities:**

1. Define the broker contract before implementation: initial-token issuance, run registration, renewal, revocation, expiry, and sanitized failure responses.
2. Keep the Keycloak writer client secret inside the Airflow trust boundary.
3. Generate a high-entropy capability per DAG run, store only a verifier in broker state, bind it to the run, and cap its lifetime at the configured run maximum.
4. Make the initial writer access token and that run's capability available to only the matching ephemeral Spark application through a protected handoff.
5. Revoke the capability and remove the container on success, failure, cancellation, and timeout; rely on bounded expiry if active cleanup fails.
6. Preserve `lakehouse-main` → `main` and `lakehouse-uat` → `uat` exactly.

**Acceptance outcomes:**

- Broker/API contract is documented and contract-checked before Unit 2 consumes it.
- Writer client secret does not appear in Spark environment, mounts, image, logs, or broker responses.
- Renewal is private, TLS-verified, run-scoped, and rejects invalid, expired, or revoked capabilities.
- DAG cleanup is configured for all task outcomes.
- Bundle names, refs, directories, and selection behavior remain unchanged.

**Out of scope:** Polaris grant changes, RustFS root credentials, UAT runtime execution, concurrent-workload and resilience testing.

## Unit 2 — Shared Spark runtime and identity adapters

**Purpose:** Provide one pinned Spark/Iceberg runtime and common Spark-side renewal provider while preserving distinct human-user and service-writer identities.

**Owning components:** Shared Spark runtime, common token provider, Jupyter user adapter, and Airflow writer adapter.

**Repository responsibilities:**

- `opensource-lakehouse-infra-v2`: canonical runtime definition, auth-provider source, immutable pinned image build, and Jupyter image integration.
- `opensource-lakehouse`: Airflow Spark image/runtime reference, Spark startup/configuration integration, and repository-specific tests or checks. Changes needed for Airflow visibility are committed and pushed to `main` as required.

**Responsibilities:**

1. Select and pin a Spark/Iceberg combination compatible with Spark 3.5 and the public Iceberg auth-provider extension approach; preserve current workload compatibility.
2. Implement one shared provider for token expiry tracking, refresh scheduling, concurrency control, atomic token replacement, redaction, and safe errors.
3. Provide identity-specific adapters: Jupyter calls its existing user-bound broker; Airflow calls its writer broker using the active run capability.
4. Reject missing or conflicting identity selection. Never fall back from a user identity to the writer identity or vice versa.
5. Keep bearer tokens in memory or protected per-run storage and never write credentials to logs.
6. Keep Polaris-vended RustFS credential handling distinct from OAuth token renewal.

**Airflow adapter handoff for Unit 2:** the scheduler sets `LAKEHOUSE_TOKEN_PROVIDER=airflow`, `LAKEHOUSE_INITIAL_ACCESS_TOKEN`, `LAKEHOUSE_TOKEN_BROKER_URL`, `LAKEHOUSE_TOKEN_BROKER_CA`, `LAKEHOUSE_RUN_HANDLE`, and `LAKEHOUSE_RUN_CAPABILITY` in the per-run Spark container. Unit 2 must consume the initial token, renew through `POST /v1/runs/token` with `run_handle` in JSON and the capability only in the HTTPS bearer header, and replace the active token in memory. The API schema is pinned at `infra/airflow-token-broker/openapi.yaml`.

**Acceptance outcomes:**

- Both Jupyter and Airflow Spark consume the same pinned runtime/provider build.
- Jupyter continues to act as the authenticated human user; Airflow acts as `write-service-account` with existing `role-default-writer` authorization.
- Spark can refresh its Polaris bearer without restarting the Spark application or Jupyter session.
- The client secret is never delivered to Spark; human Jupyter token policy and Polaris grants remain unchanged.

**Out of scope:** Keycloak role changes, Polaris grant expansion, RustFS policy changes, changing Bundle definitions, UAT runtime execution, concurrent-workload and resilience checks.

## Integration and verification

After both units are implemented, integrate the Airflow broker, shared Spark provider, Compose networks, Keycloak writer client, Polaris, RustFS, and existing Bundle source. Verify the Bundle contract, source/config contracts for UAT, and the production `main-init_environment` workflow end to end. The configured sample-table overwrite is expected. Record skipped UAT runtime, concurrent workload, and resilience checks as unverified/deferred.
