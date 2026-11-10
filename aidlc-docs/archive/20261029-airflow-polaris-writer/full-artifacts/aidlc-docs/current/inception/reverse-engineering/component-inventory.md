# Component Inventory

| Component | Location | Status | Responsibility |
|---|---|---|---|
| Airflow deployment support | infra/airflow and scripts | Retained, services deferred | Image, validation, admin and secret setup |
| Git Bundle workload source | sibling opensource-lakehouse repository | Active external dependency | DAGs, environment config, Spark job source |
| Keycloak | infra/keycloak and active Compose | Active | Identity, service client, group/role claims |
| Polaris | infra/polaris and active Compose | Active | Iceberg REST, authorization, credential vending |
| RustFS | infra/rustfs and active Compose | Active | S3-compatible object storage |
| Spark bootstrap | infra/spark-bootstrap | Active for local bootstrap/testing | Spark/Iceberg runtime |
| Jenkins | archive and sibling repository | Not active in v2 Compose | CI for workload source |

Testing UAT/production requires active Airflow, fetched Bundles, Spark jobs, Keycloak, Polaris, and RustFS.
