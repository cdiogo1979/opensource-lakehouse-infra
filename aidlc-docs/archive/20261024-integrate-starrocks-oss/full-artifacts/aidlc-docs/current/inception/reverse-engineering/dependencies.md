# Dependencies and Integration Map

## Service Dependencies

- Hive Metastore depends on PostgreSQL, KDC, and RustFS availability.
- Spark workload depends on Hive Metastore, RustFS, and Kerberos credentials.
- JupyterHub depends on the KDC, Hive Metastore, RustFS, Docker socket, and single-user image.
- Airflow's sample DockerOperator task depends on the sibling project image, Docker socket, and external `iceberg-poc-net`.
- Proposed StarRocks FE and BE/CN depend on each other and require network access to Hive Metastore and RustFS.

## Proposed StarRocks Catalog Dependencies

StarRocks Iceberg external catalog supports HMS and S3-compatible storage per current upstream documentation. Integration must confirm the selected StarRocks build, Iceberg v2 features used by the tables, Hive 3.1.3 compatibility, RustFS endpoint/signing behavior, and Kerberos credential lifecycle. No code-level StarRocks dependency has been added.

## Security Dependencies

Kerberos authentication to HMS, RustFS S3 credentials/policies, Hive metastore authorization, StarRocks SQL authorization, and Spark authorization are separate mechanisms. Ranger may be evaluated later; no Ranger services or plugins exist in the current project.
