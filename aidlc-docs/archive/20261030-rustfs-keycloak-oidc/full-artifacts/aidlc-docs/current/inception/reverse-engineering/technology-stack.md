# Technology Stack — RustFS / Keycloak Authentication

## Programming Languages
- Python 3 — bootstrap, provisioning, verification scripts and tests.
- Bash — operator entry points.

## Frameworks
- RustFS — 1.0.4 — S3-compatible object store with native OpenID identity support.
- Keycloak — 26.8.1 — OIDC provider.
- Apache Polaris — 1.8.0 — Iceberg REST catalog; RustFS STS consumer.

## Infrastructure
- Docker Compose — local single-host runtime, loopback-only published ports.
- PostgreSQL 17 — Keycloak and Polaris state (not RustFS).

## Build Tools
- Docker Compose V2 — service orchestration.

## Testing Tools
- pytest — contract tests.
- Hypothesis — property-based tests in some suites (`tests/requirements-pbt.txt`).
