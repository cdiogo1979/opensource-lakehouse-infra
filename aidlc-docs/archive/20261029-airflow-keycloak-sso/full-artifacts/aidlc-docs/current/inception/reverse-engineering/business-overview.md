# Business Overview — Airflow / Keycloak SSO

## Business context

The lakehouse platform uses Airflow for scheduled and manually triggered workload orchestration. Keycloak is the platform identity provider, already used for human JupyterHub OIDC and service identities. This intent concerns enabling human users to authenticate to the Airflow web UI through Keycloak; it does not yet define the desired authorization mapping or service/API authentication behavior.

## Relevant business transactions

- **Airflow web access:** A user visits the local Airflow UI. Current code authenticates against Airflow's FAB-managed local user store; a bootstrap task creates a configured local administrator.
- **JupyterHub web access:** A human user authenticates through Keycloak using the `jupyterhub` OIDC Authorization Code client with PKCE S256. JupyterHub checks mapped group membership before admitting the user.
- **Airflow workload execution:** Airflow schedules DAG work and obtains writer tokens through the separate Airflow token broker. This machine-to-machine writer identity is not human web SSO.

## Business terms

- **SSO:** A human authenticates with the central Keycloak identity provider and accesses an application without a separate Airflow-local password prompt.
- **Airflow role:** An Airflow authorization role governing UI/API permissions; distinct from Keycloak realm/client roles and Polaris data roles.
- **OIDC client:** A Keycloak relying-party registration including client type, callback URI, allowed flow, and claims.
- **Writer service identity:** The existing `write-service-account` confidential client used for DAG execution; not an interactive user account.

## Text flow

Browser → Airflow web login → Airflow FAB authentication integration → local Airflow user/role store today.

Browser → JupyterHub → Keycloak OIDC → group-based JupyterHub admission today.

Keycloak is not yet configured as an Airflow web-login provider in the inspected realm contract.
