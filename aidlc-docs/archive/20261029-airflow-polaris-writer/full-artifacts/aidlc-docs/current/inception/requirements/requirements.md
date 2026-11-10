# Airflow Polaris Writer Identity Requirements

## Intent Analysis

- **User request:** Adapt the Airflow integration so its UAT and production jobs execute using the `write-service-account` identity, which is assigned the Polaris `role-default-writer` role. Preserve the existing Git Bundle setup.
- **Request type:** Brownfield integration enhancement.
- **Scope estimate:** Cross-system integration across the Airflow control plane in `opensource-lakehouse-infra-v2` and the workload/DAG source in `opensource-lakehouse`.
- **Complexity estimate:** Moderate. The work includes Keycloak token acquisition and renewal, secure token delivery to Spark, Polaris authorization, and a main-branch end-to-end run.
- **Success outcome:** Airflow can run the approved main/production job end to end with Polaris authorizing Spark as `role-default-writer`; the UAT job is configured to use the same service identity, with UAT runtime execution explicitly outside this intent's test scope.

## Scope and Boundaries

### In scope

- Re-enable the Airflow services in `opensource-lakehouse-infra-v2` Docker Compose and integrate them with the existing Keycloak, Polaris, RustFS, and Spark runtime.
- Preserve the deployed two-Bundle contract: `lakehouse-main` tracking `main` and `lakehouse-uat` tracking `uat`. Preserve their names, refs, and selection behavior; retain v2's matching validator.
- Adapt the Airflow DAG factory and make the smallest necessary Spark startup/configuration changes in `opensource-lakehouse` to use the per-run Polaris bearer token and renew it during long-running Spark applications.
- Configure a one-hour access-token lifespan for the `write-service-account` client only. Keep human JupyterHub token lifetimes unchanged.
- Keep the writer client secret in Airflow. Spark receives only short-lived access tokens; the secret must not be mounted into Spark or written to logs.
- Retain Polaris RBAC and scoped RustFS credential vending. Spark accesses RustFS using credentials vended by Polaris rather than long-lived root credentials.
- Run end-to-end verification only for the `main` branch / production Bundle, using the existing `main-init_environment` job and its configured sample-table overwrite behavior.
- Commit and push the required workload repository changes so Airflow's main-branch Bundle can observe them.

### Out of scope

- Runtime end-to-end execution of the UAT Bundle. The UAT identity/configuration contract may be verified from source and configuration, but runtime behavior remains unverified.
- Changes to Bundle definitions, names, tracking refs, directories, or selection behavior.
- Tests of branches other than `main`.
- Changes to JupyterHub human authentication or human token lifetimes.
- Broader Security Baseline or Resiliency Baseline work; those extensions were declined. The explicit authentication and secret-handling requirements in this document still apply.
- Concurrent workload and resilience testing unless added by a later approved scope change.

## Functional Requirements

### FR-1: Airflow deployment

The v2 Docker Compose deployment shall start the Airflow control-plane services needed to parse and execute the existing DAGs and shall connect them to the platform services required by the writer workflow.

### FR-2: Bundle contract

Airflow shall retain and validate exactly the approved two-Bundle contract for this deployment:

| Bundle | Tracking ref | Purpose |
|---|---|---|
| `lakehouse-main` | `main` | Production workload and the only runtime end-to-end test target |
| `lakehouse-uat` | `uat` | UAT workload; runtime execution is out of scope for this intent |

The Bundle definitions and their existing selection behavior shall remain unchanged.

### FR-3: Writer identity and authorization

For both UAT and production job configuration, Spark shall authenticate to Polaris as the Keycloak confidential client `write-service-account`, whose service account is assigned Polaris role `role-default-writer`. Polaris remains responsible for authorization and for vending scoped RustFS credentials.

### FR-4: Token acquisition and delivery

Airflow shall obtain a short-lived access token using the writer client's client-credentials grant. It shall keep the client secret within the Airflow trust boundary and pass the access token to the corresponding ephemeral Spark application through a protected per-run mechanism. Access tokens and client secrets shall not be logged.

### FR-5: Token lifespan and renewal

The access-token lifespan override shall be one hour for `write-service-account` only; human JupyterHub token lifetimes shall not change. Long-running Spark applications shall obtain replacement access tokens as needed through a private renewal endpoint reachable by the Spark application. The client secret remains in Airflow and is never delivered to Spark. Token renewal must not require restarting the Spark application or Jupyter session.

### FR-6: Spark/Polaris integration

Spark shall send its current writer access token in the HTTP Authorization header for Polaris REST API requests. When a token expires or is replaced, subsequent Polaris requests shall use the renewed token. Spark shall use the storage credentials returned by Polaris for RustFS access and shall not require long-lived RustFS root credentials for this workflow.

### FR-7: Production workflow

The existing `main-init_environment` DAG shall remain the production workflow under test. The test shall use the configured sample table and its normal overwrite behavior, as explicitly selected by the user. No additional production data cleanup or table migration is part of the requirement.

### FR-8: Release visibility

Changes made to the `opensource-lakehouse` workload source shall be committed and pushed to the repository's `main` branch so the Airflow Git Bundle can observe them. Bundle setup itself remains unchanged.

## Non-Functional Requirements

### NFR-1: Secret and token handling

- Keep the client secret in Airflow; do not put it in Spark container environment variables, mounts, images, or logs.
- Send only the per-run access token to Spark through a protected mechanism.
- Do not log access tokens, renewal responses, or client secrets.
- Keep the token renewal endpoint private to the Airflow/Spark runtime path and authenticate/authorize requests so arbitrary callers cannot obtain writer tokens.

### NFR-2: Least privilege

Use the existing `role-default-writer` assignment and Polaris authorization policy for writer access. Do not broaden catalog or storage grants as part of token plumbing.

### NFR-3: Compatibility

Preserve the approved two-Bundle names, refs, and selection behavior. Keep JupyterHub human-token behavior unchanged. Make only the smallest Spark startup/runtime changes needed for Polaris writer token use and renewal.

### NFR-4: Test scope and evidence

- Execute runtime end-to-end testing only against the `main` branch / production Bundle.
- Verify that the production job obtains and uses the writer identity, reads/writes through Polaris and RustFS, and completes the configured sample-table operation.
- Verify UAT configuration and identity wiring without executing the UAT Bundle; record UAT runtime behavior as unverified.
- Do not characterize skipped concurrent-workload or resilience checks as passing.

## Accepted Limitations

- UAT runtime execution is intentionally not part of the verification gate.
- Concurrent workload and resiliency checks are deferred.
- The main-branch end-to-end run performs the existing configured sample-table overwrite.

## Key Architectural Decision

Because Keycloak's client-credentials flow does not provide the Spark application a refresh token under the selected secret boundary, an Airflow-owned private renewal endpoint will mediate replacement tokens. The writer-only one-hour lifespan reduces renewal frequency while keeping the secret out of Spark and leaving human JupyterHub token lifetimes unchanged. Detailed endpoint and transport design will be produced during workflow/design planning.
