# Build Instructions

## Scope and prerequisites

- Workspace: `opensource-lakehouse-infra-v2` plus the authorized sibling `opensource-lakehouse` checkout.
- Tools: Python 3 with pytest and the sibling repository's pinned development tools; Docker Desktop with Compose V2.
- The Spark token provider is built with Maven inside the `infra/spark-runtime/Dockerfile` builder stage; a local Maven installation is not required for that image build.
- Use the existing local runtime configuration. Do not display or copy secret values.

## Build steps

1. Validate the merged Airflow Compose model using the environment preparation performed by `scripts/lakehouse.sh`.
2. Build the shared Spark runtime image:

   ```bash
   docker build -t local/lakehouse-spark-runtime:3.5.5_1.10.2 -f infra/spark-runtime/Dockerfile .
   ```

3. Build the Airflow and token-broker images:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.airflow.yml --profile airflow build \
     airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer airflow-token-broker
   ```

4. If builds succeed, `scripts/lakehouse.sh start-airflow` prepares local secrets/certificates, starts the approved local Airflow profile, and verifies both configured Bundles without triggering a DAG.

## Build evidence

Record command, outcome, image tags, and any deviation from the approved Spark/Iceberg versions in `build-and-test-summary.md`. Do not report a production runtime result unless the authorized main workflow is actually run and verified.
