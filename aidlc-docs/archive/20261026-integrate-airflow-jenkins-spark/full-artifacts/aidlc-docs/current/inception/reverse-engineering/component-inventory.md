# Component Inventory

## Application Packages
- Target lakehouse Spark/Jupyter workloads — Spark access to Hive Iceberg and RustFS.
- Airflow Git bundle workload source — versioned Spark DAGs, common config loader, and workload applications.
- Airflow DAG factory — validates declarations/config and orchestrates per-run Spark containers.

## Infrastructure Packages
- Target Docker Compose platform — Hive Metastore, PostgreSQL, Kerberos, RustFS, Spark, JupyterHub, and StarRocks.
- Sibling Airflow Docker Compose platform — Airflow components, Airflow PostgreSQL, Jenkins, bundle cache, and Docker socket access.
- Spark job image — Spark/Iceberg runtime used by Docker-created workload containers.

## Shared Packages
- Bundle environment configuration and common Python workload CLI/config helpers.
- Target identity provisioner and writer keytab/RustFS credential provisioning.

## Test Packages
- Jenkins pipeline checks in the bundle tracking repository.
- Target platform TPCH workload and its runtime verification scripts.
- Legacy sibling `test_ephemeral_spark` DAG/job; a demo, not the current bundle contract.

## Total Count
- **Total logical components**: 8
- **Application**: 3
- **Infrastructure**: 2
- **Shared**: 1
- **Test/validation**: 2

