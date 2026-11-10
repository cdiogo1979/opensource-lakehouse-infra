# Code Generation Summary — Airflow Keycloak SSO

## Generated behavior

- Added a confidential Keycloak `airflow` Authorization Code client with exact `localhost` and `127.0.0.1` callbacks for FAB's `/auth/oauth-authorized/keycloak` route.
- Added a `groups` user-info mapper. Airflow denies OAuth login when the username is missing, matches the local administrator username, or has no approved group.
- Mapped Keycloak groups to Airflow roles: `role-default-owner` and `role-default-developer` to `Admin`, `role-default-analyst` to `User`, and `role-default-writer` to `Viewer`. Multiple approved groups contribute all distinct mapped roles; unknown groups contribute none.
- Added a combined login page with Keycloak sign-in and a separate FAB database-password route restricted to `AIRFLOW_ADMIN_USERNAME`. The local admin username is not accepted as an OAuth identity, keeping role synchronization away from the break-glass account.
- Configured the Keycloak issuer and RS256 JWKS endpoint for FAB ID-token validation. The browser-facing authorization URL uses `keycloak.localhost`; the server-side JWKS and user-info requests use Docker-internal `keycloak` DNS because `keycloak.localhost` resolves to loopback inside the Airflow container.
- Mounted the Airflow OIDC client secret read-only in the API server and short-lived initialization service; the latter needs it because FAB's admin-user CLI loads the shared webserver configuration. Only the API server joins the Keycloak network. The standard `start` flow does not request Airflow client bootstrap; `start-airflow` passes the protected secret file after provisioning it.

## Files created or modified

- Created `infra/airflow/airflow_auth_views.py`, `infra/airflow/airflow_oauth_security_manager.py`, `infra/airflow/airflow_sso_roles.py`, and `infra/airflow/webserver_config.py`.
- Modified `infra/airflow/Dockerfile`, `infra/keycloak/bootstrap-realm.py`, `infra/keycloak/realm-contract.json`, `docker-compose.airflow.yml`, and `scripts/lakehouse.sh`.
- Created `tests/airflow/test_keycloak_sso_contract.py` and `tests/keycloak/test_airflow_client_contract.py`.
- Updated the approved generation plan, state, and audit artifacts. The existing secret provisioning entry was retained; no secret values were copied to code or documentation.

## Code Generation verification

- Airflow Keycloak client contract tests: 5 passed.
- Airflow SSO authorization contract tests: 6 passed.
- Existing JupyterHub client contract tests: 6 passed.
- Python syntax, realm-contract JSON, and `scripts/lakehouse.sh` syntax checks passed.
- Merged Airflow Compose configuration validated successfully with non-secret placeholder values for required runtime variables.
- No services were started, no browser login was performed, and no persistent Keycloak realm changes were made.

## Build and Test handoff

Code Generation is complete. Review the generated code and this summary before authorizing Build and Test. Runtime service startup, interactive login checks, and persistent realm changes remain governed by the approved requirements and the next-stage plan.
