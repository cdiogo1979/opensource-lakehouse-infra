# Current Application Design — Open Source Lakehouse Infrastructure

## Purpose and scope

This repository describes a local Docker Compose lakehouse proof of concept built from Hive Metastore, PostgreSQL, RustFS, Spark, JupyterHub, Airflow, Jenkins, and optional StarRocks. Workload DAGs and notebooks live in the separate `opensource-lakehouse` repository and are delivered to Airflow through the `lakehouse-main` and `lakehouse-uat` DAG bundles. The local stack is not a production availability or security guarantee.

## Components and boundaries

- **Hive Metastore and PostgreSQL** provide the Iceberg catalog metadata service and its backing database.
- **RustFS** provides S3-compatible object storage. The approved access target uses `lake` for production, `lake-dev` for development, and `lake-uat` for UAT.
- **Spark** reads and writes Iceberg data through the Hive catalog and RustFS. Direct S3 permissions are the data-plane boundary for Spark; a StarRocks SQL grant does not constrain direct Spark access.
- **JupyterHub** starts isolated Spark notebook containers. The approved identity direction uses FreeIPA-backed login and per-user authorization; Unit 4 isolated checks passed, while production identity cutover was not completed.
- **Airflow** schedules workload DAGs from the existing Git bundles and launches Spark work. Existing reported UAT and production DAG executions belong to the separate workload repository.
- **StarRocks OSS** is the analytical SQL endpoint. It reads Iceberg through Hive Metastore and RustFS. The tested native-RBAC direction maps FreeIPA LDAP groups to StarRocks roles; Ranger is not part of the approved target.
- **FreeIPA and Kerberos** provide the approved central identity direction. The existing MIT KDC remained authoritative; a production cutover was not completed.
- **Jenkins** runs the pipeline maintained by `opensource-lakehouse`; this repository does not duplicate the workload source.

## Approved access model

- `developer-user` may read all environments and write only to development.
- `analyst-user` may read production and may not write to any environment.
- `write-service-account` may read and write all environments and may manage environment-scoped StarRocks materialized views.
- Existing `admin` privileges are preserved.
- StarRocks roles are mapped to FreeIPA groups. A direct StarRocks writer-role exception is needed for materialized-view refresh; group removal alone does not revoke that direct role or terminate existing SQL sessions.
- Production data and existing writer S3 credentials are to be preserved during any future cutover.

## Verification and deployment status

Unit 1 isolated FreeIPA checks and Unit 3 direct Spark/RustFS role checks passed with documented limits. Unit 2 closed with a scoped waiver for actual FreeIPA membership-variant testing. Unit 4 isolated JupyterHub authentication and authorization checks passed; the expected denied-spawn path surfaces as HTTP 500. Unit 5 native StarRocks LDAP/RBAC checks passed on disposable services.

The overall intent was closed with a user-approved verification waiver. Production LDAP-to-StarRocks account binding is unresolved; the production group provider and grants were not applied; production identity migration, RustFS policy changes, MIT KDC cutover, and post-deployment verification remain incomplete. A production FreeIPA container became healthy and an identity bootstrap was invoked, but completion/readback was not confirmed before all Docker containers were stopped. No production deployment is authorized by this closure.

## Operations and lifecycle

The original `opensource-lakehouse-infra` directory is retained as a reference. The `.runtime` directory was removed from `opensource-lakehouse-infra-v2` at the user's request; its local credentials, state, and cached bundle data are therefore absent from this copy. Runtime recreation and production cutover require a separately reviewed operational plan.
