# API and Integration Documentation

## Existing Interfaces
- Airflow Git Bundle provider checks out refs using an Airflow Git connection.
- Airflow's Docker provider talks to Docker Engine; Docker socket access grants significant host control.
- Keycloak exposes an OIDC client-credentials token endpoint for write-service-account; Airflow job token acquisition/consumption is not implemented in active v2.
- Spark/Iceberg uses Polaris REST with bearer authentication; Polaris applies catalog authorization and returns temporary storage credentials.
- Polaris uses Keycloak issuer/JWKS and RustFS S3 for identity validation and object storage.

## Contracts and Mismatch
- Active realm contract defines write-service-account as confidential client credentials and assigns its service principal to role-default-writer.
- Active v2 bundle validator expects two bundles: lakehouse-main/main and lakehouse-uat/uat.
- Sibling workload repository documents three: lakehouse-dev, lakehouse-uat, lakehouse-prod; UAT tracks uat and production tracks main.
- Sibling Spark runtime currently uses Kerberos principal/keytab. The user has authorized only dag_factory.py in the sibling repository. Requirements must determine whether its current submission contract can hand the writer JWT to Spark without modifying job_runtime.py or other workload files.
- No custom Airflow token broker API exists in active v2.
