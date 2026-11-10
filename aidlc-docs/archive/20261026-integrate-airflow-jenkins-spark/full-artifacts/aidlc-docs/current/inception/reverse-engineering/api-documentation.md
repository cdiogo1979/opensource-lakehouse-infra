# API Documentation

## REST APIs

No project-owned REST endpoint was found in the inspected integration code.

## Internal APIs

### Airflow DAG factory
- **Interface**: `create_spark_dag(dag_name, workloads, schedule)`.
- **Workload fields**: `task_name`, `entrypoint_file`, optional `runs_after` task names.
- **Behavior**: Validates the selected environment config and workload dependency graph; creates one Spark container with the current bundle mounted read-only; executes each job with `spark-submit`; removes the container during cleanup.
- **Runtime settings**: Spark image, master, Docker URL, Docker network, bundle source/target, environment, and AWS-compatible region.
- **Current credential gap**: Factory container creation passes region/environment and bundle mount; target Kerberos keytab/cache and writer RustFS credential files are not mounted or initialized.

### Spark job contract
- **Entrypoint**: Python module under `notebooks/workload/` in the selected bundle.
- **Invocation**: `/opt/spark/bin/spark-submit --master <configured-master> ...`.
- **Inputs**: Environment config distributed by Spark; bundle-level Python modules on `PYTHONPATH`.
- **Output**: Iceberg metadata through Hive Metastore and object data in RustFS under the selected environment path.

### Target Lakehouse interfaces
- **Hive Metastore**: Thrift endpoint `hive-metastore:9083`; Kerberos SASL enabled.
- **RustFS**: S3-compatible endpoint `http://object-store:9000`; path-style access required.
- **Kerberos principal**: Existing ETL identity form `write-service-account@LAKEHOUSE.LOCAL`, from a keytab protected under ignored runtime credentials.
- **StarRocks SQL**: Native SQL username `write_service_account` is a separate identity and should not be confused with the Kerberos writer principal.

## Data Models

### Bundle workload declaration
- **Fields**: Task name; Python entrypoint basename; optional predecessor task names.
- **Relationships**: Airflow tasks depend on create-container, configured predecessor tasks, and cleanup task.
- **Validation**: Unique task names, entrypoint is a Python filename in the workload folder, dependency references exist, and graph is acyclic.

### Environment configuration
- **Fields**: `storage_path`, `database_name`, and currently supported arbitrary nested values.
- **Validation**: Environment must be one of dev/uat/prod; required fields are checked by the bundle config loader; no fallback between environments.

