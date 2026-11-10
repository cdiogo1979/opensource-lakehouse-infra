# Code Structure — Jenkins / Keycloak

## Existing files (candidates for change)
- `infra/jenkins/Dockerfile` — Jenkins LTS (jdk21, digest-pinned) plus pinned Python 3.10; no plugins and no configuration as code.
- `docker-compose.yml` — the v2 services; no Jenkins service yet.
- `docker-compose.deferred.yml` — the deferred inventory entry `jenkins: unsupported-pending-migration`.
- `infra/keycloak/bootstrap-realm.py`, `infra/keycloak/realm-contract.json` — client and mapper bootstrap pattern (JupyterHub, Airflow, RustFS clients; guarded callback reconciliation; ID/access-token group mappers).
- `scripts/prepare-lakehouse-runtime.py` — protected credential creation and mount staging.
- `scripts/lakehouse.sh` — operator entry points (`start`, `start-airflow`, and others).
- `Jenkinsfile` (root) — this repository's pytest pipeline; never wired to a job.
- `README.md` — lists Jenkins as deferred.
- `tests/keycloak/*_client_contract.py` — client contract test precedent.

## Sibling repository
- `../opensource-lakehouse/Jenkinsfile` — the workload CI pipeline Jenkins runs (out of this workspace; not to be edited by this intent unless approved).

## Patterns to reuse
- Additive, fail-closed Keycloak client bootstrap with exact URIs.
- Protected secret files with read-only mounts.
- Loopback-only published ports.
- Pinned images.
- Contract tests for Compose and Keycloak clients.
