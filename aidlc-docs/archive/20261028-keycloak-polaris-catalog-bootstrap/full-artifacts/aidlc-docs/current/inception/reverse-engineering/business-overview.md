# Business Overview — Existing Lakehouse Infrastructure

## Current purpose
This brownfield repository runs a local, containerized Iceberg lakehouse for development and evaluation. RustFS stores Iceberg data; Hive Metastore backed by PostgreSQL stores catalog metadata; Spark, JupyterHub, Airflow, Jenkins, and optional StarRocks provide processing, notebook, orchestration, CI, and SQL access. Workload DAGs/notebooks are maintained in the separate `opensource-lakehouse` repository and delivered to Airflow through Git bundles.

## New intent boundary
The new intent proposes a full bootstrap with Keycloak replacing FreeIPA and Apache Polaris replacing Hive Metastore, while removing the old FreeIPA/Hive setup. Initial named resources requested are catalogs `lakehouse`, `lakehouse-dev`, `lakehouse-uat`; databases `default_lh`, `default_lhdev`, `default_lhuat`; RustFS buckets `bucket-default`, `bucket-default-dev`, `bucket-default-uat`; and four role/group labels `role-default-developer`, `role-default-analyst`, `role-default-owner`, `role-default-writer`. This document records the proposal only; it does not authorize deleting existing services or data.

## Initial design recommendations for requirements review
- Model each requested “database” as a Polaris namespace within its matching catalog: `lakehouse.default_lh`, `lakehouse-dev.default_lhdev`, and `lakehouse-uat.default_lhuat`. Confirm whether users expect database/schema semantics or an additional namespace hierarchy.
- Preserve the intended access semantics from the previous design as a starting point: developer reads all and writes dev; analyst reads production only and cannot write; writer service account reads/writes all; owner administers data access. Keep “owner” separate from Keycloak realm-admin and RustFS root credentials.
- Use Keycloak groups for people/group membership, but provision corresponding Polaris principals, principal roles, catalog roles, and grants. Do not assume Keycloak alone replaces Polaris authorization state.
- Keep a service identity for non-interactive Spark/Airflow access. Human Keycloak login and S3 object-store credentials are separate concerns; evaluate RustFS OIDC/STS support for each client before removing service credentials.
- Keycloak is not a Kerberos KDC replacement. Determine whether the standalone MIT KDC and keytabs remain, or whether workloads migrate to OAuth end-to-end.
- Treat Polaris as an Iceberg REST catalog, not a Hive Thrift drop-in. Migrate and verify Spark, StarRocks, and any other Hive clients. Retain StarRocks unless a later approved requirement removes it.
- Give Polaris its own metadata persistence database/schema. Do not reuse the Hive metastore schema. Airflow has an independent metadata database.
- Make bootstrap repeatable and non-destructive by default. Do not wipe RustFS volumes or existing data implicitly.

## Current limitations
This is a local Compose stack, not an HA production deployment. The v2 copy has no `.runtime` directory after prior closure; its ignored `.env` was not inspected.
