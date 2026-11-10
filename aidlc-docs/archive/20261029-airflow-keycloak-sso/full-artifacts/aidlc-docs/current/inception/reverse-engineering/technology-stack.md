# Technology Stack — Airflow / Keycloak SSO

## Runtime and identity

- Apache Airflow 3.3.2, Python 3.10 image.
- FAB auth manager selected through `AIRFLOW__CORE__AUTH_MANAGER`.
- Apache Airflow FAB, Git, Docker, and PostgreSQL providers installed under pinned Airflow constraints.
- Keycloak 26.8.1 with the `lakehouse` realm.
- PostgreSQL 17.11 for Airflow metadata.
- Docker Compose V2; host-published UI endpoints bind to loopback by default.

## Existing identity flows

- JupyterHub: Keycloak OIDC Authorization Code with PKCE S256 and group-based admission.
- Airflow UI: local FAB-backed account; an admin user is bootstrapped from a file-backed secret.
- Airflow DAG execution: separate writer client-credentials flow through the run-scoped token broker.

## Tooling and tests

- Python unit/contract tests under `tests/`.
- Compose validation and shell-based local lifecycle scripts.
- Infrastructure workspace has no Git metadata; workload source is a sibling repository.
