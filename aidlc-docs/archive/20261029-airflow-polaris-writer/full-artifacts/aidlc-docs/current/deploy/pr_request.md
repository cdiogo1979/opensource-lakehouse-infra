# Proposed PR: Run Airflow Spark jobs with renewed Polaris writer tokens

## Problem

Airflow production and UAT workloads need to access Polaris as the existing `write-service-account` / `role-default-writer` identity without exposing the client secret to Spark, while preserving the deployed Git Bundle setup.

## Solution

Use an Airflow-owned token broker to issue run-scoped access tokens and renew them for Spark through a private, TLS-verified endpoint. A shared Spark 3.5.5 / Iceberg 1.10.2 runtime provides a JVM Iceberg `AuthManager`, with separate Jupyter-user and Airflow-writer renewal adapters. The writer secret remains in Airflow; Polaris continues to vend scoped object-storage credentials.

## Main changes

- `opensource-lakehouse-infra-v2/infra/airflow/`, `docker-compose.airflow.yml`, and broker configuration: Airflow services and the token-broker lifecycle.
- `opensource-lakehouse-infra-v2/infra/spark-token-provider/` and `infra/spark-runtime/`: shared token-renewal provider and Spark runtime image.
- `opensource-lakehouse/dags/dag_factory.py` and `notebooks/common/job_runtime.py`: per-run Spark container lifecycle and writer token integration.
- `opensource-lakehouse/tests/`: workload contract tests aligned with the current workload entrypoint and token integration.
- The active v2 deployment retains exactly two Bundles: `lakehouse-main` tracking `main` and `lakehouse-uat` tracking `uat`.

The workload repository changes are already pushed to `main` as `da070b6`. No PR was created as part of this work.

## Verification

- Builds, static checks, infrastructure tests, workload tests, and focused deployment/token tests passed; see `../construction/build-and-test/build-and-test-summary.md`.
- The designated main E2E run `aidlc-writer-verification-20261029T2059Z` passed all seven tasks using Bundle version `8dcda2d`.
- A later retry using Bundle commit `da070b6` initially failed at `create_cluster` because Docker could not find `local/lakehouse-spark-runtime:3.5.5_1.10.2`. The user subsequently reported building the image and successfully running the main DAG and UAT DAG. Run IDs/revisions were not supplied, and the runs could not be independently verified in the current CLI context.
- Concurrency, resilience, and live role-matrix testing were not performed; none is represented as passing or waived.

## Deployment

Operational steps are required to make the Spark runtime image available to Airflow and verify the updated main Bundle. Follow [`deploy_instructions.md`](deploy_instructions.md). This document is a handoff only; no deployment or new DAG run is authorized by its preparation or approval.

## Risks and limitations

- The previous main DAG retry was blocked by the missing local Spark image; the user reports this was remedied and the main DAG then succeeded.
- An earlier UAT Bundle import error was recorded in `notebooks/workload/count_sample_rows.py`; the user reports a later successful UAT DAG run.
- User-reported main/UAT run IDs and revisions are not yet recorded. Concurrent workloads, resilience, and live role-matrix behavior remain unverified.
- The approved production test overwrites the configured sample table. No rollback procedure for that data operation is documented; confirm the target is appropriate before any authorized rerun.
- The local image uses Iceberg 1.10.2 (the approved design selected an Iceberg upgrade for the `AuthManager` API), not 1.8.1 as earlier Unit 2 documents stated.
- Missing release owner, target deployment environment, maintenance window, and data recovery procedure are required inputs for a separately authorized production release.
