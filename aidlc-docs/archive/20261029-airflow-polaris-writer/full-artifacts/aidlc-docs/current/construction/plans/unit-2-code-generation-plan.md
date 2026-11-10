# Unit 2 Code Generation Plan — Shared Spark Token Provider

## Approved implementation boundary

- Use the approved shared Spark 3.5.5 / Iceberg 1.10.2 runtime and JVM `AuthManager` extension (the approved Application Design answer to Question 5 selected the compatible Iceberg upgrade).
- Keep identity adapters separate: JupyterHub's active-user broker endpoint and Airflow's run-scoped broker endpoint.
- Keep the Keycloak writer secret broker-only. Spark receives only an initial JWT, its broker URL and CA, and the relevant Hub server token or run-scoped capability.
- Retain Polaris-vended S3 credential behavior as a separate Iceberg mechanism.
- Do not change Polaris grants, RustFS policies, Bundles, UAT runtime scope, or the main-only E2E boundary.

## Code generation scope

- Add the shared JVM provider source and Maven descriptor under `infra/spark-token-provider/`.
- Add the common pinned Spark runtime build under `infra/spark-runtime/`; use it for both the Jupyter single-user image and Airflow's Spark runtime image.
- Configure Jupyter and the workload repository's shared `start_spark_job` to select the correct identity adapter and set all three Polaris REST catalogs to the custom provider.
- Remove the workload's Airflow keytab authentication path; Airflow writer authorization comes from the registered run token.
- Build the shared runtime before JupyterHub or Airflow startup.
- Keep build, test, image startup, and DAG execution pending for the designated Build and Test stage.

## Acceptance checklist

- [x] Both entry points use the same provider implementation and Spark/Iceberg version.
- [x] Jupyter renewal uses its existing HTTPS broker endpoint and the active Hub API token.
- [x] Airflow renewal uses `POST /v1/runs/token`, run handle in JSON, capability only in the HTTPS bearer header.
- [x] Token replacement occurs in memory immediately before Iceberg REST requests; no static token is configured as Iceberg catalog state.
- [x] No identity fallback is implemented; missing identity settings fail closed.
- [x] OAuth JWT renewal remains separate from Polaris-vended object-storage credentials.
- [x] Legacy keytab authentication was removed from the shared workload startup helper.
- [x] Runtime image builds and provider contract checks pass (Build and Test stage).
- [x] Main production `main-init_environment` workflow is executed and verified (Build and Test stage).
- [ ] UAT runtime, concurrency, and resilience checks remain deferred by user approval.

## Source locations

- `infra/spark-token-provider/`
- `infra/spark-runtime/Dockerfile`
- `infra/jupyter/singleuser/lakehouse_spark.py`
- `infra/jupyter/singleuser/Dockerfile`
- `scripts/lakehouse.sh`
- `../opensource-lakehouse/notebooks/common/job_runtime.py`
- `../opensource-lakehouse/dags/dag_factory.py`
