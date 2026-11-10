# API Documentation — Identity Bootstrap

- **Keycloak Admin REST** (`/admin/realms/lakehouse/...`): users (create with `credentials[{type: password, value, temporary}]`, `requiredActions`), groups, and group membership (`PUT /users/{id}/groups/{gid}`). These are already used by `bootstrap-realm.py` through its `KeycloakAdmin` helper.
- **Polaris principals**: created by `infra/polaris/reconcile-keycloak-groups.py` for members of the four product groups.
- **Docker CLI**: `docker compose down`, `docker volume rm`, `docker rm`, `docker network rm`, with label filters for the per-user containers and volumes.
