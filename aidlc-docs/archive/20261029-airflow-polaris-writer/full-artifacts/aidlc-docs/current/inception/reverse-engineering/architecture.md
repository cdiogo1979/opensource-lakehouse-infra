# System Architecture

## System Overview
Active v2 Compose contains Keycloak, Polaris, RustFS, Spark bootstrap tooling, and JupyterHub; Airflow is deferred and absent from the active stack. v2 retains a pinned Airflow image, credentials/bootstrap tooling, a validator for the main/UAT Bundle contract, and a DAG-registration verifier. The sibling opensource-lakehouse repository owns current DAG/Spark sources and documents three Git Bundles: dev, UAT, and production. The user authorized changing only dags/dag_factory.py there; Bundle configuration and the rest of the source stay unchanged. Main/production is the only requested end-to-end test target. The archived intent 20261026-integrate-airflow-jenkins-spark contains an earlier Airflow/Jenkins/Spark Compose implementation and design and serves as historical reference only.

## Component Boundaries
- Airflow control plane: absent from active Compose; local reintroduction versus external deployment is undecided.
- Bundle/DAG source: sibling opensource-lakehouse. Only dags/dag_factory.py may change; preserve Bundle setup, DAG declarations, configs, and notebook workload files.
- Spark workload: sibling repository's DAG factory currently provisions containers using a Kerberos keytab contract.
- Identity: Keycloak has confidential client write-service-account and writer group.
- Authorization/storage: Polaris validates identity and role claims and vends RustFS credentials.

## Target Transaction Flow (to confirm)
Airflow selects a pinned Bundle; the main/production job is the only end-to-end test target. It starts Spark with environment config; Spark authenticates as the writer client; Spark calls Polaris; Polaris validates writer permissions and vends scoped storage credentials; Spark reads/writes permitted RustFS objects and reports completion. UAT job behavior is an intended outcome but testing is limited to main unless clarified.

## Open Architecture Questions
Airflow deployment location; token handoff achievable within the one-file dag_factory.py authorization; whether non-DAG workload runtime changes are needed; production-only test approach versus UAT acceptance evidence; handling of the current Kerberos and RustFS credential mounts.
