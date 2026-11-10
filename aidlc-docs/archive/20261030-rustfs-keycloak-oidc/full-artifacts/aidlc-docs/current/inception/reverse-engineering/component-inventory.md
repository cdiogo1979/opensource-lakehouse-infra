# Component Inventory — RustFS / Keycloak Authentication

## Application Packages
- `rustfs` service — object storage, STS, and console (RustFS 1.0.4 image).
- `keycloak` service — identity provider (Keycloak 26.8.1).
- `polaris` service — consumer of RustFS STS; must remain unaffected.

## Infrastructure Packages
- `docker-compose.yml` — Compose definitions.
- `infra/keycloak/` — realm bootstrap and contract.
- `infra/rustfs/` — bucket bootstrap.
- `scripts/` — runtime preparation, secret provisioning, operator entry points, STS verification.

## Shared Packages
- `.runtime/credentials/` — protected credential store (not source).

## Test Packages
- `tests/keycloak/` — client contract tests (Unit).
- `tests/polaris/` — Compose/runtime contract tests including RustFS references (Unit/property-based).

## Total Count
- **Total Packages**: 9 relevant
- **Application**: 3
- **Infrastructure**: 4
- **Shared**: 1
- **Test**: 2 (relevant directories)
