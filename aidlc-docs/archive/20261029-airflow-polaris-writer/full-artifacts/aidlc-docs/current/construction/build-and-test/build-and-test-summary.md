# Build and Test Summary

## Status

- **Stage status:** Complete and approved by the user; handoff is in progress.
- **Build:** Passed.
- **Automated tests:** Passed within the approved verification scope.
- **Local service readiness:** Airflow services were already healthy; production and UAT DAG IDs were registered.
- **Main production E2E:** The designated run passed against the then-current `main` Bundle version `8dcda2d`. A later retry against `da070b6` initially stopped at container creation because the configured image was absent. On 2026-10-29 at 21:40Z, the user reported building the image and successfully executing the updated main DAG. The run ID and Bundle revision were not provided and could not be independently retrieved in the current Airflow context.
- **UAT runtime:** Initially deferred; the user subsequently reported that the UAT DAG completed successfully on 2026-10-29 at 21:40Z. Run ID and revision were not provided and could not be independently retrieved in the current Airflow context.
- **Concurrency and resilience:** Explicitly deferred; unverified.

## Initial environment observations

- The infrastructure workspace has no Git metadata.
- `opensource-lakehouse` started clean on `main` at `8dcda2d`; validated changes were committed and pushed as `da070b6`.
- Docker and Compose V2 are available.
- Local Maven is not installed; the Spark runtime Dockerfile uses a Maven builder image.
- Airflow and core services were already running and healthy before this stage. They were not started or stopped during this stage.

## Results

### Builds and static checks

- `docker compose -f docker-compose.yml -f docker-compose.airflow.yml --profile airflow config -q` — passed with the environment prepared as in `scripts/lakehouse.sh`.
- `docker build -t local/lakehouse-spark-runtime:3.5.5_1.10.2 -f infra/spark-runtime/Dockerfile .` — passed; the Maven builder compiled the provider and assembled the runtime image.
- Airflow and token-broker image builds — passed (`local/lakehouse-airflow:3.3.2`, `local/lakehouse-airflow-token-broker:1.0.0`).
- Spark runtime smoke check — passed; `spark-submit --version` reported Spark 3.5.5 and Java 17.
- Workload Python compilation — passed.
- `scripts/code_quality.sh all` — passed (Ruff, Black, Flake8, Bandit).

### Automated tests

- Infrastructure: `PYTHONPATH=infra/jupyter/hub python3 -m pytest -q -rs` — **86 passed, 1 skipped, 5 subtests passed**. The skipped live role-matrix test requires `LAKEHOUSE_LIVE_ROLE_MATRIX=1`; it remains outside this intent's approved scope.
- Workload: `python3 -m pytest -q` — **48 passed**.
- Focused deployment and writer-token tests — **15 passed**.
- The workload test fixtures had references to the prior `init_environment.py` name; they were updated to test the current `test_environment.py` entrypoint and sample-table overwrite contract.

### Runtime verification

- Airflow reported both `lakehouse-main:main-init_environment` and `lakehouse-uat:uat-init_environment` as registered.
- The DAG processor reported one import error in the UAT Bundle at `notebooks/workload/count_sample_rows.py`. No UAT run was attempted, consistent with the approved scope.
- Main production run `aidlc-writer-verification-20261029T2059Z` — **success**. All seven task instances succeeded, including validation, Spark container creation, all three workload submissions, success verification, and cleanup.
- Sanitized task logs confirmed the sample-table write completed. The Spark container was removed after the run. The configured broker issues the writer-service token; identity values are intentionally not logged.
- The workload changes are published on `main` as commit `da070b6`.
- After publication, a manual retry (`manual__2026-10-29T20:57:44.348759+00:00`) loaded Bundle commit `da070b6` but failed in `create_cluster` with Docker `ImageNotFound`: `local/lakehouse-spark-runtime:3.5.5_1.10.2` was not present on the Docker daemon. `validate_environment` passed; no Spark container or workload task started. The successful designated run above used Bundle version `8dcda2d`.
- **Subsequent user-reported execution:** The user reported the Spark runtime image was built and the main DAG executed successfully, and that the UAT DAG also finished correctly. This report is recorded as user-provided; run IDs and revisions were not supplied. A check in the currently available CLI context did not find the image tag, and the connected scheduler did not have either DAG in its Airflow metadata table, so the later runs could not be independently verified from this session.

### Version reconciliation

- The approved Application Design answer to Question 5 selected upgrading Iceberg to a version with the public `AuthManager` API. The implemented runtime and provider use Iceberg **1.10.2** with Spark **3.5.5** (`local/lakehouse-spark-runtime:3.5.5_1.10.2`); earlier Unit 2 plan and implementation-summary text incorrectly retained 1.8.1 and has been corrected.
- The approved two-Bundle contract (`lakehouse-main`/`main` and `lakehouse-uat`/`uat`) remains unchanged. The sibling repository’s separate three-Bundle guide is not the active v2 contract.

## Explicitly unverified

- UAT runtime success is user-reported but not independently verified here; an import error had been observed in the earlier Airflow context.
- Concurrent workload, resiliency, and live role-matrix testing.
- The production log does not print identity claims; successful Polaris-backed table writes are evidence of authorization, while the configured service identity is established by the broker/runtime configuration.
