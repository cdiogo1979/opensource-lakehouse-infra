# Component Inventory

## Active Project Services

- KDC — Kerberos authentication service.
- PostgreSQL metastore DB — Hive metadata persistence.
- Hive schema init and Hive Metastore — catalog services.
- RustFS and bucket initializer — S3-compatible data storage.
- Spark — workload/notebook compute.
- JupyterHub and single-user notebook image — interactive access.
- Identity provisioner — local principal, role, and S3 identity setup.
- TPCH generator and loader — optional sample data workload.
- StarRocks — absent; proposed query engine for this intent.

## Adjacent Project

- `airflow-spark-jenkins` — Airflow, PostgreSQL, Jenkins, and Dockerized Spark job image. It currently targets Nessie and a shared external network.

## Project Type

- **Applications/services**: containerized data platform services.
- **Infrastructure**: Docker Compose, Dockerfiles, KDC, object store, metastore DB.
- **Workload code**: Python and shell ETL/identity tooling.
- **Tests**: no discovered StarRocks integration tests.
