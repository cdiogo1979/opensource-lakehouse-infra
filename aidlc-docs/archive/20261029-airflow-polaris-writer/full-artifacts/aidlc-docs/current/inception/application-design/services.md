# Services and Orchestration — Airflow Polaris Writer Identity

## Airflow run lifecycle

1. Airflow resolves the DAG from the existing Bundle selection. The contract remains exactly `lakehouse-main` → `main` and `lakehouse-uat` → `uat`.
2. Before Spark starts, Airflow's trusted token-broker path obtains the initial `write-service-account` access token and creates a unique, high-entropy capability for this DAG run. The broker stores a verifier and a maximum expiry bounded by the run timeout.
3. Airflow starts one ephemeral Spark container on a private network reachable by Polaris and the Airflow broker. The container receives the initial token and run capability through the protected per-run handoff, plus a selector/configuration for the Airflow identity adapter. The Keycloak client secret is never mounted or passed to Spark.
4. Spark's shared token provider supplies bearer auth to Iceberg REST calls and refreshes before expiry through the Airflow broker. The broker authenticates each renewal with the run capability and returns only a replacement writer access token and expiry.
5. Polaris authorizes `role-default-writer` operations and vends scoped RustFS credentials. Spark performs the configured workload using those credentials.
6. Airflow's all-outcomes cleanup stops/removes the Spark container and revokes the run capability. Broker state expires automatically at the run's maximum lifetime if cleanup cannot complete.

## Jupyter session lifecycle using the same provider

1. JupyterHub authenticates a user through Keycloak and applies the configured group admission policy.
2. A user starts Spark from the single-user container. The shared provider uses the Jupyter adapter and existing Hub broker to obtain the active user's token.
3. The provider refreshes during the Spark application through the user-bound broker. It does not use the Airflow writer broker or writer client credentials.
4. Stopping the Spark application ends its local refresh lifecycle; JupyterHub session and human token policy remain governed by their existing lifecycle.

## Service failure behavior

- If Keycloak is unavailable before initial token acquisition, Airflow must fail the run before Spark starts.
- If renewal fails transiently, the provider may retry with bounded backoff only while the current token remains valid; it must fail the Spark operation safely before expiry rather than silently switch identities.
- If the capability is invalid, expired, or revoked, the broker rejects renewal. Spark fails with a sanitized authentication error.
- If Polaris rejects the token or role, the workload fails; it must not fall back to a privileged identity.
- If Spark exits, is cancelled, or times out, Airflow still executes container cleanup and broker revocation.
- If RustFS vended credentials expire, the storage client follows the Polaris/Iceberg vended-credential refresh contract; OAuth renewal alone does not refresh S3 credentials.

## Verification boundary

Runtime end-to-end verification remains production/main only through the existing `main-init_environment` workflow and its configured sample-table overwrite. UAT receives source/config contract checks only. Concurrent-workload and resilience checks remain deferred.
