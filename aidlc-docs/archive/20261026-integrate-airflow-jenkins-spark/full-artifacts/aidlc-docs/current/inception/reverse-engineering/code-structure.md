# Code Structure

## Build System

- **Type**: Docker Compose, Python/PySpark, Jenkins pipeline, Airflow Git DAG Bundles.
- **Configuration**: Target `docker-compose.yml`, `infra/spark/spark-defaults.conf`, `infra/tpch-loader/`; sibling `docker-compose.yml`, `Dockerfile*`, `spark/spark-defaults.conf`, `dags/`, `jobs/`; the versioned bundle checkout contains a shared `dags/dag_factory.py`, environment configs, Spark workload modules, Jenkinsfile, and bundle docs.
- **Source-of-truth note**: `.airflow-dag-bundles/` is a runtime checkout/cache, not a canonical source folder. Its tracking repository is a local bare clone of a separate Git project. Do not copy generated bundle cache/version directories wholesale.

## Key Modules and Existing Files Inventory

### Target files
- `docker-compose.yml` — lakehouse services, shared network, Spark/Jupyter/StarRocks services, writer keytab and RustFS secret mounts for TPCH loader.
- `infra/spark/spark-defaults.conf` — Hive-backed `iceberg` catalog, S3FileIO endpoint/path-style config, Hive SASL and service principal.
- `infra/tpch-loader/run-workload.sh` — kinit with writer keytab, ticket cache lifecycle, and Spark submit entry point.
- `infra/tpch-loader/load_tpch.py` — TPCH ETL using Spark, catalog, and RustFS identity validation.
- `scripts/start.sh`, `scripts/provision-identities.sh` — target platform startup and identity provisioning.
- `README.md` — target service operations and user/identity documentation.

### Sibling Airflow/Jenkins files
- `airflow-spark-jenkins/docker-compose.yml` — legacy local Airflow/metadata DB/Jenkins setup, bundle configuration, Docker socket mounts, and external network connection.
- `airflow-spark-jenkins/Dockerfile` — Airflow image and providers.
- `airflow-spark-jenkins/Dockerfile.jenkins` — Jenkins image customization.
- `airflow-spark-jenkins/Dockerfile.spark` — Spark job image copied with the legacy Nessie Spark config and demo workload.
- `airflow-spark-jenkins/spark/spark-defaults.conf` — legacy Nessie catalog and sample object-store config; incompatible with target Hive catalog until replaced.
- `airflow-spark-jenkins/dags/test_ephemeral_spark.py` — legacy single-task DockerOperator example.
- `airflow-spark-jenkins/jobs/test_spark_job.py` — legacy Spark test that creates/writes a Nessie-backed sample table.

### Bundle checkout files
- `dags/dag_factory.py` — shared Airflow DAG factory, per-run Spark container creation, read-only bundle bind mount, spark-submit execution, task dependencies, and cleanup.
- `dags/dag_defaults.py` — bundle-name-to-environment/DAG identity.
- `dags/*.py` — bundle-specific DAG workload declarations.
- `configs/dev.yml`, `uat.yml`, `prod.yml` — environment storage paths and database names; examples currently target the bundle repository's own lakehouse namespaces.
- `notebooks/common/` and `notebooks/workload/` — shared config parsing and Spark workloads.
- `Jenkinsfile` — CI checks only in the inspected bundle repo.
- `AIRFLOW_BUNDLES.md` — Git bundle layout, versioning, branch selection, Docker mount, and runtime settings contract.

## Design Patterns

### Run-pinned Git bundle
- **Location**: Airflow `dag_factory.py` and bundle configuration.
- **Purpose**: Ensure DAG, config, helper modules, and workload code correspond to one commit.
- **Implementation**: Airflow supplies its versioned checkout path; Docker mounts it read-only into one per-run container.

### Per-DAG-run reusable Spark container
- **Location**: Airflow `dag_factory.py`.
- **Purpose**: Run one or more Spark applications with shared run-scoped environment and bundle mount.
- **Implementation**: Container is created once, each workload is invoked with `spark-submit`, then cleanup executes even on task failure.

### Writer identity in target ETL
- **Location**: Target TPCH loader Compose service and `run-workload.sh`.
- **Purpose**: Separate Spark writer credentials from admin/user credentials.
- **Implementation**: Read-only keytab, private ticket cache in tmpfs, RustFS writer credentials as Docker secrets.

## Critical Dependencies

- **Apache Airflow 3.3.2 and Git/Docker providers** — DAG parsing, Git bundle handling, and Docker Engine API.
- **Spark 3.5.5 / Iceberg 1.8.1** — job runtime consistent with target lakehouse image.
- **Docker Engine API/socket** — required to create, bind-mount, and remove ephemeral Spark containers.
- **Hive Thrift + Kerberos** — target catalog and authenticated metadata operations.
- **RustFS S3-compatible API** — Iceberg object storage; writer identity is distinct from Hive identity.
- **Git provider and bundle configuration** — fetches versioned DAG/workload files; credentials belong in Airflow connection/secrets backend.

