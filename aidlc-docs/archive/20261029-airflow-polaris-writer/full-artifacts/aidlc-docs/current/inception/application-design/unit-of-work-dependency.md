# Unit of Work Dependency Matrix — Airflow Polaris Writer Identity

| Unit / activity | Unit 1: Airflow writer identity and broker | Unit 2: Shared Spark runtime and identity adapters | Existing platform / workload | Build and Test |
|---|---|---|---|---|
| Unit 1: Airflow writer identity and broker | — | Publishes the versioned API, capability rules, token response, and TLS contract consumed by the Airflow adapter. | Requires Keycloak writer client, v2 Compose/Docker access, existing Polaris endpoint and role. DAG integration uses existing Bundle paths and workload declarations. | Contract checks before Unit 2 integration; no production E2E until Unit 2 is ready. |
| Unit 2: Shared Spark runtime and identity adapters | Consumes Unit 1 API contract for Airflow renewal. Does not consume writer client secret. | — | Requires existing JupyterHub user broker, Keycloak user identity, Polaris REST, and vended RustFS credential behavior. Workload repo consumes pinned runtime image. | Runtime compatibility checks and adapter checks; test only approved main job end to end. |
| Integration | Unit 1 service, Compose network, and DAG orchestration must be available. | Shared provider and both adapters must be built and pinned. | Existing Bundle contract remains unchanged. | Runs after both units; validates main E2E and UAT source/config only. |

## Required sequence

1. **Unit 1 contract first:** define and verify API schemas, capability format/entropy, max-run expiry, registration/revocation semantics, TLS trust, and safe errors.
2. **Unit 1 implementation:** deliver Airflow broker and DAG lifecycle integration against that contract.
3. **Unit 2 implementation:** select the exact compatible Spark/Iceberg pin, implement the common provider and separate identity adapters, publish the immutable runtime, and update Jupyter/Airflow consumers.
4. **Cross-unit integration:** run source/config and Bundle contract checks, then the production `main-init_environment` end-to-end workflow.

## External dependencies

- Keycloak's existing confidential `write-service-account` and writer-only one-hour lifespan configuration.
- Existing Polaris `role-default-writer` and catalog policy; no grant changes are planned.
- Existing Polaris token validation and RustFS credential vending.
- Docker network/TLS certificate distribution between Spark, the Airflow broker, and Polaris.
- `opensource-lakehouse` repository's two deployed Bundles and existing `main-init_environment` workflow.

No dependency requires a UAT runtime test, concurrent workload, or resilience test in this intent.
