# Component Inventory — Reset and Identity Bootstrap

- **Application**: keycloak, polaris, rustfs, jupyterhub, jenkins, airflow (optional overlay).
- **Infrastructure**: `docker-compose.yml`, `docker-compose.airflow.yml`, `scripts/`, `infra/keycloak/`, `infra/polaris/`.
- **Shared**: `.runtime/credentials/`, `.runtime/container-mounts/`.
- **Test**: `tests/keycloak/`, `tests/jenkins/`, `tests/rustfs/`, `tests/polaris/`, `tests/integration/`.
