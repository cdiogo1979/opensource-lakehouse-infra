# Business Overview

## Business Context
The platform operator wants Airflow-orchestrated lakehouse jobs to run against UAT and production data with the intended writer identity. Airflow selects versioned DAG/workload code; Spark executes it; Polaris enforces catalog permissions using Keycloak identity and role claims; RustFS stores table data and receives scoped credentials through Polaris.

## Business Transactions
1. Run a UAT job from the approved UAT Bundle/configuration; Spark accesses Polaris/RustFS as the authorized writer identity.
2. Run a production job from the approved production Bundle/configuration; Spark accesses Polaris/RustFS as the authorized writer identity.
3. Reject a job when service authentication is invalid or writer authorization is absent; report failure to Airflow without falling back to privileged static storage credentials.

## Business Dictionary
- Git Bundle: Airflow 3 versioned source package for DAGs and workload files.
- Writer service identity: Existing Keycloak client-credentials identity write-service-account, associated with role-default-writer.
- Polaris role: Catalog authorization used to permit or deny Iceberg operations.
- UAT / production: Separate workload configuration and catalog/storage targets.
