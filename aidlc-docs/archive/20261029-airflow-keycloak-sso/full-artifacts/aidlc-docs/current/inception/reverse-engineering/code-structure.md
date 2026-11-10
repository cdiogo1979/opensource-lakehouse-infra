# Code Structure — Airflow / Keycloak Authentication

## Relevant configuration and modules

- `docker-compose.airflow.yml` — Airflow services, FAB auth-manager selection, metadata database, initialization, local admin secret, and loopback web exposure.
- `infra/airflow/Dockerfile` / `infra/airflow/requirements.txt` — Airflow 3.3.2 Python 3.10 image and FAB provider installation under Airflow constraints.
- `infra/airflow/bootstrap-airflow-admin.py` — idempotent local administrator creation via Airflow CLI; suppresses captured output and does not pass password through OS arguments.
- `infra/airflow/airflow-entrypoint.sh` — validates Bundle configuration then starts the requested Airflow process.
- `infra/keycloak/realm-contract.json` — declared Keycloak realm/client/claim contract for existing lakehouse clients.
- `infra/keycloak/bootstrap-realm.py` — additive Keycloak realm and OIDC client reconciliation, including exact JupyterHub callback and PKCE config.
- `scripts/provision-airflow-secrets.sh` — provisions the protected local Airflow admin password and writer-broker credentials.
- `infra/airflow-token-broker/` — separate machine-to-machine writer token service, unrelated to browser UI login.

## Existing auth design patterns

- Secrets are file-backed Docker secrets under `.runtime/credentials/`, not stored in source.
- Keycloak client configuration is explicit and reconciled by the bootstrap script; conflicting existing settings fail rather than being silently overwritten.
- Airflow admin bootstrap is idempotent and only creates the local admin if absent.
- Airflow and Keycloak endpoints are currently loopback-published; internal service calls use Compose networks.

## Test locations

- `tests/keycloak/` covers realm/bootstrap client contracts.
- `tests/jupyterhub/` covers the existing human OIDC-to-JupyterHub integration.
- `tests/` includes Airflow and writer-token integration contract tests from the prior intent.
- No focused Airflow browser-SSO implementation or test exists in the inspected source tree.

## Likely change surface (not yet approved)

Potential areas include Airflow auth-manager/provider configuration, an Airflow FAB OAuth configuration module, Keycloak realm-client contract and bootstrap logic, local admin bootstrap/role synchronization, Compose mounts/environment, and focused tests. Final choices are deferred to requirements and design approval.
