# Application Components — Airflow Polaris Writer Identity

## Components

| Component | Responsibility | Trust boundary / identity |
|---|---|---|
| Airflow control plane | Selects the approved Git Bundle, schedules `main-init_environment`, and coordinates the Spark container lifecycle. | Airflow Compose network; holds no writer credential outside its configured secret integration. |
| Airflow writer token broker | Owns/accesses the Keycloak confidential-client secret, obtains writer tokens, registers per-run renewal state, serves protected HTTPS renewals, and revokes run capabilities. | Private Airflow/Spark network; writer service identity only. |
| Shared Spark runtime and token provider | Runs Spark 3.5.x-compatible workloads and integrates Iceberg REST auth with a common token-provider interface and replacement-token lifecycle. | Ephemeral workload container; receives only the initial access token and run-scoped renewal capability. Never receives the client secret. |
| JupyterHub user token broker | Returns a current token bound to the authenticated, active JupyterHub user and applies current admission checks. | JupyterHub user network; human OIDC identity. |
| Jupyter single-user Spark environment | Runs interactive Spark using the shared runtime/provider while retaining the logged-in user's identity. | Per-user isolated container; receives that user's Hub broker credential, never the Airflow writer capability. |
| Keycloak | Issues OIDC access tokens for the writer service client and human JupyterHub clients. | Identity provider; writer client has the approved one-hour access-token override. |
| Polaris | Validates the current bearer token and role, exposes Iceberg REST operations, and vends scoped RustFS credentials. | Data access service; grants remain unchanged. |
| RustFS | Stores Iceberg data and metadata addressed by catalog/database/table locations. | Object store; Spark uses credentials vended by Polaris. |
| Git Bundle source | Supplies the two approved DAG bundles and their existing selection contract. | `opensource-lakehouse` repository; `lakehouse-main` tracks `main`, `lakehouse-uat` tracks `uat`. |

## Shared runtime boundary

The Spark runtime definition pins Spark, Iceberg, Java, and the shared auth-provider package once for both interactive Jupyter and Airflow workloads. The auth provider shares token parsing, expiry tracking, refresh scheduling, safe error handling, and Spark/Iceberg integration. It delegates identity-specific token acquisition and renewal to separate adapters:

- Jupyter adapter: calls the JupyterHub broker with the active server's Hub API token; the broker resolves and refreshes the authenticated user's OIDC state.
- Airflow adapter: presents the DAG-run-scoped capability to the Airflow writer broker; the broker issues a replacement token using the writer client secret it controls.

The provider must not treat these adapters or identities as interchangeable. No writer credential or run capability is made available to a Jupyter user container.

## External interfaces

- Keycloak OIDC token endpoint: client-credentials request for `write-service-account`; secret remains in the Airflow boundary.
- Airflow broker registration/revocation API: authenticated Airflow-only operations, scoped to a unique DAG run.
- Airflow broker renewal API: HTTPS request from that run's Spark container, authorized by its capability, returning only a replacement access token and expiry.
- JupyterHub broker token API: existing HTTPS user-bound token endpoint.
- Polaris Iceberg REST API: bearer-authenticated requests from Spark, with catalog realm and vended-credential delegation headers as configured.
- RustFS S3 API: accessed directly by Spark using the temporary credentials returned by Polaris.
