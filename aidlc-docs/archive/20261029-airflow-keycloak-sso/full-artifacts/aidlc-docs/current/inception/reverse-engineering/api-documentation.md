# Authentication Interfaces — Existing State

## Airflow web application

- **Method:** Browser navigation and form-based local authentication today.
- **Path:** Airflow UI served by API server at `http://127.0.0.1:${AIRFLOW_HOST_PORT:-8085}` on the host.
- **Authentication:** Airflow FAB auth manager backed by Airflow's metadata database. A local `Admin` account is bootstrapped.
- **Keycloak callback:** None is configured for Airflow in the inspected code.

## Existing Keycloak OIDC client

- **Client:** `jupyterhub` in realm `lakehouse`.
- **Flow:** Confidential OIDC Authorization Code with PKCE S256; direct access grant and service accounts disabled.
- **Callback:** `http://jupyterhub.localhost:8000/hub/oauth_callback` by default; bootstrap script can reconcile the local Hub port.
- **Claims:** Group claim `groups`; role claim mapping `resource_access.polaris.roles`.
- **Not an Airflow client:** This callback and admission mapping are specific to JupyterHub.

## Keycloak discovery and protocol endpoints

- **Issuer:** `http://keycloak.localhost:8080/realms/lakehouse` for browser-visible/local clients.
- **Internal service URL:** `http://keycloak:8080` inside Compose for service-to-service calls.
- **Standard OIDC endpoints:** Realm discovery, authorization, token, userinfo, JWKS, and logout endpoints are available through Keycloak's OIDC protocol; an Airflow client and its redirect URI are not currently declared.

## Machine identity endpoint

- The writer token broker uses the Keycloak token endpoint with client-credentials grant for `write-service-account`.
- This is a machine identity for DAG workload execution, not a human browser SSO interface.
