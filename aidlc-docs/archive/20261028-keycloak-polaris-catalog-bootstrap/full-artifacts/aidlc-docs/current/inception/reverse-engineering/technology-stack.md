# Technology Stack

| Area | Existing technology |
|---|---|
| Packaging/orchestration | Docker Compose, service-specific Dockerfiles and profiles |
| Object storage | RustFS 1.0.0, S3-compatible |
| Catalog | Apache Hive Metastore 3.1.3, Thrift |
| Catalog metadata DB | PostgreSQL 16.14 |
| Compute | Spark 3.5.5, Iceberg 1.8.1, local Kerberos-enabled image |
| Interactive notebooks | JupyterHub 5.3.0 and single-user Spark image |
| Orchestration | Airflow 3.3.2 LocalExecutor, Git DAG bundles |
| CI | Jenkins LTS local image |
| Optional SQL engine | StarRocks 4.1.6 |
| Identity | MIT Kerberos active; FreeIPA isolated validation and production overlay |
| Bootstrap tooling | Bash, Python, SQL, XML, YAML |

Proposed technologies are Keycloak (OIDC identity provider) and Apache Polaris (Iceberg REST catalog). Select and pin supported versions/digests during design, then verify the full client matrix. Keycloak replaces the directory/SSO functions only where integrations are implemented; it is not a Kerberos protocol service. Polaris replaces the catalog API, not the S3 object store.
