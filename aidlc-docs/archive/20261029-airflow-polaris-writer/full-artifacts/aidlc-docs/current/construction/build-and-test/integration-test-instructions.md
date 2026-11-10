# Integration Test Instructions

## Contract and configuration checks

- Validate the Airflow Compose overlay using the environment values prepared by `scripts/lakehouse.sh`.
- Run the repository pytest suites for the broker API, token renewal clients, Compose configuration, Bundle contract, and Spark runtime configuration.
- Build the Spark runtime and Airflow/broker images.

## Local service readiness

Only after image builds succeed, use `scripts/lakehouse.sh start-airflow`. This provisions local development materials and starts the local platform and Airflow profile. Confirm service health and the production/UAT Bundle parse checks. Do not trigger a DAG during readiness verification.

## Production end-to-end boundary

The only approved runtime target is the main/production `main-init_environment` DAG. Its configured sample table is overwritten by the workload. Before execution, verify that the local Airflow Bundle still points to `main` and that the implementation source is committed and available on `main`. Verify the resulting writer identity, Polaris authorization, successful Iceberg operation, and Polaris-vended RustFS credentials from sanitized evidence. Do not run UAT.

## Cleanup

Use the repository's documented Airflow stop command only if this stage started the local services, and preserve provider data, Airflow metadata, and Bundle checkouts. Do not remove named volumes or reset platform data.
