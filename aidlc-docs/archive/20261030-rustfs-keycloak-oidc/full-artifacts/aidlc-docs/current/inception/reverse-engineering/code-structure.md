# Code Structure — RustFS / Keycloak Authentication

## Build System
- **Type**: Docker Compose (`docker-compose.yml`, `docker-compose.airflow.yml`); Python scripts run on the host; pytest contract tests (`pytest.ini`).
- **Configuration**: `.env.example` lists host port variables (`RUSTFS_S3_HOST_PORT`, `RUSTFS_CONSOLE_HOST_PORT`, `KEYCLOAK_HOST_PORT`).

## Existing Files Inventory (candidates for modification)
- `docker-compose.yml` — `rustfs` service definition (environment, secret mounts, ports, networks).
- `infra/keycloak/bootstrap-realm.py` — client/mapper bootstrap; holds the `jupyterhub` and `airflow` client patterns (`*_client_configuration`, `ensure_*_group_mapper`, guarded callback reconciliation).
- `infra/keycloak/realm-contract.json` — declarative contract of realm clients and claims; validated by tests.
- `scripts/prepare-lakehouse-runtime.py` — creates missing protected credentials and container mount copies.
- `scripts/provision-airflow-secrets.sh` — precedent for provisioning a per-application OIDC client secret.
- `scripts/lakehouse.sh` — operator `start/status/stop` entry points.
- `infra/rustfs/bootstrap-buckets.py` — idempotent bucket creation with root keys (hand-rolled SigV4).
- `tests/keycloak/test_airflow_client_contract.py`, `tests/keycloak/test_jupyterhub_client_contract.py` — client contract test precedents.
- `README.md` — operator documentation for endpoints and RustFS storage.

## Legacy files (not part of the supported runtime)
- `infra/identity-provisioner/reconcile-rustfs-roles.py`, `provision-rustfs-identities.py`, `rustfs-role-policy.json` — FreeIPA/LDAP-era RustFS IAM group reconciliation targeting retired buckets `lake`, `lake-dev`, `lake-uat`. Not wired into the current Compose stack.

## Design Patterns
### Additive, fail-closed bootstrap
- **Location**: `infra/keycloak/bootstrap-realm.py`, `infra/rustfs/bootstrap-buckets.py`
- **Purpose**: Safe reruns; never overwrite conflicting operator changes.
- **Implementation**: read current state, create only if missing, raise on conflict.
### Protected secret files
- **Location**: `.runtime/credentials/` (0600) with `.runtime/container-mounts/` read-only copies.
- **Purpose**: No secrets in source, environment listings, or output.
