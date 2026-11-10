# Technology Stack

## Programming Languages
- Python 3 — Airflow DAG factory, PySpark workloads, identity/workload helpers.
- Bash — target ETL entrypoint and local startup/provisioning scripts.
- SQL — Spark SQL and Iceberg operations.
- YAML/JSON — Docker Compose and bundle environment/configuration.

## Frameworks and Runtime
- Apache Airflow 3.3.2 with Git, Docker, FAB and Spark providers in the sibling Airflow image.
- Apache Spark 3.5.5 and Apache Iceberg 1.8.1 in the target and sibling Spark image family.
- PySpark workloads run in `local[*]` in one per-run Spark container in the inspected bundle factory; this is not a Spark cluster master/worker deployment.
- Jenkins container for repository CI gates.
- Git DAG Bundles for versioned DAG, config, helper, and workload checkout.

## Infrastructure
- Docker Compose v2 and Docker Engine socket/API.
- Hive Metastore 3.1.3, PostgreSQL 16, MIT Kerberos, RustFS, StarRocks OSS.
- External Docker network `iceberg-poc-net` / target Compose network `iceberg_net`.
- Read-only run-pinned bundle bind mount into each ephemeral Spark container.

## Build and Testing Tools
- Docker image builds and Compose service configuration.
- Python unittest/pytest and Jenkins checks in the bundle source repository; target workload scripts.

## Configuration Notes
- The sibling root Spark defaults currently use Nessie and example static S3 credentials; those values must not be copied into the target runtime.
- The target defaults already use the Hive `iceberg` catalog and SASL principal but external workload containers still need writer identity initialization and writer S3 credentials.
- The sibling Compose bundle URL points to a separate Git repository; its local bundle cache is not itself a source-of-truth source folder.

