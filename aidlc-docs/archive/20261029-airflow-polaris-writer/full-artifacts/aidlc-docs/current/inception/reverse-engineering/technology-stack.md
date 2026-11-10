# Technology Stack

## Active Platform
At intent intake, the active project files used Docker Compose, Python 3, Bash; Keycloak 26.4.2; Apache Polaris 1.8.0; Spark 3.5.5 with Iceberg 1.8.1; RustFS; and JupyterHub. As approved in Application Design Question 5 and implemented for this intent, the shared Spark runtime now uses Spark 3.5.5 with Iceberg 1.10.2 to provide the public `AuthManager` API.

## Airflow Support
Apache Airflow 3.3.2 on Python 3.10, image pinned by digest. Git, Docker, FAB, and Postgres providers are installed under Airflow constraints. Active v2 deployment is currently absent.

## Workload Source
Sibling repository contains Python DAG/Spark sources and YAML configs. Its documented runtime uses a writer Kerberos keytab; the requested Keycloak/Polaris OIDC workload flow is not implemented there.
