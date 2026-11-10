# Dependencies

## Runtime Chain
- Airflow depends on Git for pinned Bundle checkout and Docker Engine for Spark containers.
- Spark needs the Bundle-mounted configuration and workload source.
- Target OIDC flow requires Spark or its launcher to obtain a Keycloak client-credentials token.
- Spark/Iceberg calls Polaris using the writer bearer token.
- Polaris depends on Keycloak issuer/JWKS for token validation and RustFS S3 for object access.
- Airflow task state depends on Docker task exit and Spark result propagation.

## Project Contracts
- Airflow validator constrains names/refs and path settings.
- Keycloak realm contract/bootstrap creates writer service client/group.
- Polaris OIDC config and bootstrap define identity mapping and grants.
- Current Airflow secret provisioning does not provision or mount a writer client secret.

## External Dependency
opensource-lakehouse is the authoritative DAG, configuration, Spark code, and Bundle source. It remains a read-only boundary pending requirements approval.
