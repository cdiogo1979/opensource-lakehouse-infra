# Business Logic Model — Unit 1 Airflow Writer Identity and Broker

**Status:** Final for Unit 1 Functional Design review.

## Actors

- **Airflow run coordinator:** starts the writer-auth flow for one DAG run, passes only per-run credentials to its Spark application, and revokes broker state during terminal cleanup.
- **Airflow writer token broker:** owns the writer client secret, obtains Keycloak access tokens, validates run capabilities, and controls renewal state.
- **Spark token provider:** starts with the run's initial JWT and uses the run capability to obtain replacement JWTs before expiry.
- **Keycloak:** issues access tokens for `write-service-account` through the client-credentials grant.
- **Polaris:** validates each bearer JWT and applies the existing `role-default-writer` authorization.

## Core lifecycle

### 1. Open the DAG-run authorization

1. Airflow derives a stable run key from the DAG ID and Airflow run ID. Task retry number is not part of the authorization identity.
2. Airflow asks the broker to create/register authorization for that run. The request is authenticated as an Airflow control-plane operation and is idempotent for the same run key.
3. The broker obtains a Keycloak client-credentials JWT for the writer service client, creates a cryptographically strong opaque capability, stores a verifier for that capability plus a short-lived encrypted in-memory replay record for the initial response, and records the run's maximum expiry.
4. The broker returns the initial access token, its absolute expiry, and the opaque run capability to Airflow. Airflow keeps the capability in protected run state so retries can reuse it; neither value is written to logs.
5. Airflow makes the initial token and capability available only to the matching ephemeral Spark container through the protected per-run handoff.

### 2. Use Polaris and renew the access token

1. Spark's shared provider validates the initial token's expiry and selects the Airflow writer adapter explicitly.
2. The provider uses the current token for Polaris Iceberg REST requests.
3. When five minutes or less remain, the provider requests a replacement from the Airflow broker using the run key and run capability.
4. The broker verifies the capability against the registered run and its expiry/revocation state, then requests a fresh client-credentials token from Keycloak.
5. The provider atomically replaces the in-memory token and uses it for subsequent Polaris requests. It never switches to a Jupyter/user identity.
6. Polaris authorizes using its existing role mapping and returns scoped RustFS credentials for object I/O. Those storage credentials have an independent lifecycle from the OAuth JWT.

### 3. Retry and close the run

- Airflow task retries within the same DAG run reuse the same registered run capability. An idempotent registration request with the same `(dag_id, run_id)` key returns that same capability with a fresh initial JWT; it must not create another capability or invalidate the active one.
- If Airflow loses the initial registration response, its retry uses the same idempotency key. The broker's encrypted in-memory replay record recovers the capability; the broker issues a fresh JWT. The replay record is deleted on run revocation or expiry.
- Each Spark process has its own in-memory token cache. A retry that starts a new process obtains a fresh initial JWT through the run broker operation while retaining the same run capability.
- When the DAG run reaches a terminal state, cleanup stops/removes its Spark container and revokes broker authorization, regardless of task success or failure.
- If cleanup cannot reach the broker, registration expires automatically at the configured maximum run duration.
- Revoking renewal state prevents further refreshes; it does not retroactively invalidate an already-issued self-contained JWT. That JWT can remain valid at Polaris until its one-hour expiry. Cleanup therefore also stops/removes the Spark container.

## Renewal retry behavior

A failed renewal request is retried at most twice after the initial request, with waits of one second and two seconds. A retry is not started if the current access token has 60 seconds or less remaining. If the replacement token is not acquired before the current token becomes unusable, the Spark provider fails the operation with a sanitized authentication error. It never sends an expired token as a fallback.

## State-loss behavior

The broker's run registration is short-lived in-memory state. After broker restart, an already-issued JWT may remain usable until expiry, but the broker no longer recognizes the run capability and cannot renew it. The affected Spark run fails closed when renewal becomes necessary, and Airflow performs terminal cleanup. Durable broker-state recovery and broker-restart resilience tests are deferred by the approved scope.

## Identity separation

The common Spark provider and refresh algorithm may be shared with Jupyter, but Unit 1 defines only the Airflow writer adapter contract. The Jupyter adapter remains bound to the authenticated active user's Hub credential and broker. The writer capability and client secret are never shared with Jupyter.

## Requirement traceability

| Requirement | Unit 1 functional contribution |
|---|---|
| FR-1 | Broker and Airflow run lifecycle are part of the Airflow control plane; Compose deployment details remain in Infrastructure Design. |
| FR-2 | DAG run resolves only the existing Bundle selection; names and refs are preserved. |
| FR-3 | Broker requests the writer service token; Unit 2's provider supplies it to Polaris, which applies the existing writer role. |
| FR-4 | Broker issues the initial token and run capability to Airflow for protected delivery; client secret remains broker-side. |
| FR-5 | One-hour writer JWT and run-bounded refresh capability; Unit 2 performs token refresh. |
| FR-6 | Unit 1 supplies renewable writer tokens; Unit 2 attaches bearer tokens to Polaris calls and uses vended storage credentials. |
| FR-7 | Airflow keeps the existing `main-init_environment` workflow and configured overwrite behavior. |
| FR-8 | DAG and workload changes remain in the workload repository and are committed/pushed to `main` as approved. |
