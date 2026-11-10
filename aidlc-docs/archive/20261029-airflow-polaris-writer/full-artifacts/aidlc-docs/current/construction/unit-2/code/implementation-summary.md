# Unit 2 Implementation Summary — Shared Spark Token Provider

## Implemented

- Added `LakehouseTokenAuthManager`, an Apache Iceberg 1.10.2 `AuthManager` that refreshes the current broker token before expiry and attaches the replacement bearer token to each Iceberg REST request.
- Added independent Jupyter and Airflow renewal adapters selected by `LAKEHOUSE_TOKEN_PROVIDER`.
- Jupyter adapter requests renewals from `/api/v1/token` with `JUPYTERHUB_API_TOKEN`; Airflow adapter calls `/v1/runs/token` using the run handle and run capability.
- The plugin validates the broker TLS certificate using the provided CA, disables redirects, limits requests to five seconds, retries at most three times with bounded waits, and suppresses broker response bodies in errors.
- Added a common Spark 3.5.5 / Iceberg 1.10.2 runtime image containing the plugin, and wired both the Jupyter single-user image and Airflow Spark image to it.
- Updated workload `start_spark_job` to configure the Polaris catalogs with the shared provider and remove the legacy Airflow Kerberos keytab login.

## Verification status

- Source review only. No image build, automated test, provider startup, Airflow startup, or DAG run has been performed in this code-generation stage.
- The implementation must pass the designated Build and Test stage before the main production DAG is committed/pushed and executed.
- UAT runtime, concurrent workload, and resilience checks remain deferred as approved.
