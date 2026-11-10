# Component Inventory — Jenkins / Keycloak

## Application Packages
- `jenkins` (target v2 service; not present yet).
- `keycloak` (existing).
- Legacy `hive-dremio-rustfs-jenkins-1` (exited; outside v2).

## Infrastructure Packages
- `infra/jenkins/` — image definition.
- `infra/keycloak/` — realm bootstrap and contract.
- `docker-compose.yml`, `docker-compose.deferred.yml`.
- `scripts/` — runtime preparation and operator entry points.

## Shared Packages
- `.runtime/credentials/` — protected credentials.

## Test Packages
- `tests/keycloak/` — client contract tests.

## Total Count
- **Total Packages**: 8 relevant
- **Application**: 3
- **Infrastructure**: 4
- **Shared**: 1
- **Test**: 1
