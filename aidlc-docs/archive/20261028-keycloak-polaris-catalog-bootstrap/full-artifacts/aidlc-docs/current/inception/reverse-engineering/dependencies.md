# Dependency and Integration Map

- Hive Metastore depends on `metastore-db`; Spark and optional StarRocks depend on Hive for Iceberg metadata.
- Spark and StarRocks depend on RustFS for table objects and credentials/policies appropriate to their execution identity.
- JupyterHub creates user notebook containers; Spark within them currently uses Hive, RustFS, and per-user Kerberos/S3 configuration.
- Airflow obtains DAGs from Git bundles and launches Spark work through Docker; its own PostgreSQL metadata store is independent of Hive metadata.
- MIT KDC supplies Kerberos identities used by service/workload paths. FreeIPA validation is isolated and is not the active KDC.
- Jenkins runs workload-repository CI; it is not the DAG source of truth.

## Migration dependencies
1. Stand up Polaris with durable metadata storage and bootstrap catalogs/namespaces.
2. Configure RustFS S3 access and Polaris credential vending/authorization for Spark and StarRocks.
3. Migrate Spark/Iceberg clients and test create/read/write operations in all three catalogs.
4. Migrate StarRocks external catalog and test reads/materialized-view use.
5. Replace JupyterHub LDAP auth with Keycloak OIDC and validate group-to-user policy.
6. Decide how Kerberos-protected components and keytabs are handled; do not assume OIDC covers them.
7. Only then remove Hive, its schema-init job, and Hive-only metadata database/configuration.

A dependency scan of all external workload bundle contents is outside this repository and is not complete.
