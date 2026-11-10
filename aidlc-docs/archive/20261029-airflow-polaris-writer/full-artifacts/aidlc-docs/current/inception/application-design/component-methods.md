# Component Methods — Airflow Polaris Writer Identity

These are design-level contracts. Concrete classes, endpoint paths, request schemas, and the exact Iceberg extension API are fixed in Functional Design after checking the selected compatible dependency versions.

## Airflow writer token broker

| Method / operation | Inputs | Outputs | Behavior |
|---|---|---|---|
| `issue_initial_token()` | Writer client configuration and secret reference | Access token plus absolute expiry | Uses Keycloak client credentials. The secret is read inside the Airflow trust boundary and never returned. |
| `register_run(run_id, capability_hash, expires_at)` | Unique DAG run ID, hash of a high-entropy capability, max run expiry | Registration result | Creates idempotent renewal state bounded by the DAG run's maximum duration. Store only a verifier/hash of the capability. |
| `renew(run_id, capability)` | Run ID and bearer capability over verified HTTPS | Replacement access token plus expiry | Constant-time verifies the run capability, rejects expired/revoked runs, obtains a new writer token, and emits no secret or sensitive upstream body. |
| `revoke_run(run_id)` | Unique DAG run ID | Revocation result | Idempotently invalidates renewal state on normal completion, failure, timeout, or cleanup. |

## Shared Spark token provider

| Method | Inputs | Outputs | Behavior |
|---|---|---|---|
| `initialize(identity_adapter, initial_credential)` | Adapter selection and initial access token (or Jupyter broker bootstrap credential) | In-memory token state | Validates token shape/expiry and starts a per-Spark-application refresh lifecycle. Never writes bearer values to logs. |
| `get_current_token()` | None | Current access token | Returns the current usable token; coordinates concurrent refresh attempts within one Spark application. |
| `refresh_if_needed()` | None | Updated in-memory token state | Refreshes before expiry through the selected identity adapter and atomically replaces the token used for subsequent Polaris requests. |
| `close()` | None | None | Stops refresh activity and clears in-memory references where practical when the application exits. |

## Identity adapters

- `JupyterUserTokenAdapter.refresh()`: calls the existing user-bound JupyterHub broker using that active server's Hub API token and verified broker CA.
- `AirflowWriterTokenAdapter.refresh()`: calls the private Airflow broker over verified TLS with the DAG-run capability.

Both return the same internal `Token(access_token, expires_at)` value to the shared provider. Neither returns a client secret or changes the authenticated principal.

## Airflow orchestration

- `create_run_auth(dag_run)`: obtains/receives initial writer token, generates a run capability, registers its verifier and bounded expiry with the broker, and makes only the per-run data available to the Spark container.
- `start_spark_container(bundle, run_auth)`: starts the ephemeral Spark runtime with the approved Bundle, identity-specific adapter configuration, initial token, capability, and private network access.
- `submit_workload(container, entrypoint, environment)`: invokes the unchanged workload entry point and preserves Bundle-specific environment selection.
- `cleanup_run_auth(dag_run, container)`: stops/removes Spark and revokes run auth in an all-outcomes cleanup path.

## Polaris and storage operations

- Spark's Iceberg catalog client obtains the current bearer from the shared token provider for REST requests.
- Polaris validates role authorization and returns scoped storage credentials.
- Iceberg's S3 client uses the vended credentials for RustFS; those credentials are distinct from OAuth access tokens and require their own refresh/expiry behavior.
