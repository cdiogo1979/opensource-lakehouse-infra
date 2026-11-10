# Code Structure

## Build and Configuration

- `docker-compose.yml` — Hive, PostgreSQL, KDC, RustFS, Spark, JupyterHub, optional identity/workload profiles and shared network.
- `infra/hive/` — Hive image, rendered configuration templates, schema initialization.
- `infra/kerberos/` — KDC image and realm configuration.
- `infra/identity-provisioner/` — Kerberos, PostgreSQL and RustFS identity provisioning.
- `infra/spark/` — Spark entrypoint/defaults for Hive catalog access.
- `infra/jupyter/` — Hub, single-user image, per-session config and sample notebook.
- `infra/tpch-generator/`, `infra/tpch-loader/` — optional data generation and Spark ETL.
- `scripts/` — bootstrap, lifecycle, provisioning, cleanup and workload commands.
- `../airflow-spark-jenkins/docker-compose.yml` — sibling Airflow/Jenkins platform; Spark job image and sample DAG configuration.
- `../airflow-spark-jenkins/spark/spark-defaults.conf` — current Nessie catalog settings and placeholder S3 credentials.

## Current Data Flow

`TPCH input -> Spark writer identity -> Hive Metastore catalog + RustFS objects -> notebook Spark queries`

Proposed additional path: `SQL client -> StarRocks FE -> StarRocks BE/CN -> HMS metadata + RustFS table files`.

## Existing Tests and Quality

Compose configuration and image builds are the primary integration checks. Shell and Python helper scripts exist. There is no StarRocks-specific configuration, SQL bootstrap, test, or health check yet. Previous intent verification covered Compose/configuration/source syntax but explicitly waived live stack and ETL verification.
