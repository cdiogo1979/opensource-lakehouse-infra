# Personas — JupyterHub Developer and Analyst Access

## Platform Operator

**Role:** Operates the lakehouse platform and provisions access to JupyterHub.

**Goals**

- Provide a stable JupyterHub sign-in experience backed by the existing Keycloak realm.
- Admit only people assigned to approved Keycloak role groups.
- Keep each user's Jupyter and Spark runtime isolated and operational.
- Diagnose login, token renewal, and access failures without exposing bearer tokens.

**Responsibilities and boundaries**

- Configures the Keycloak OIDC client, JupyterHub callback, role admission, and supported user environment.
- Ensures Hub auth state is encrypted and that the token broker binds calls to the requesting user's own JupyterHub server.
- Does not grant data rights by bypassing Polaris role policies or use the shared writer identity for interactive users.
- Uses operational logs that identify users and outcomes without recording access-token or refresh-token values.

## Developer

**Role:** Builds and explores data products through notebooks and Spark.

**Goals**

- Sign in to JupyterHub with the Keycloak account already assigned to `role-default-developer`.
- Start Spark sessions using the developer's own identity at Polaris.
- Read approved production, UAT, and development data; write only to approved development paths.

**Responsibilities and boundaries**

- Works in an isolated per-user Jupyter/Spark container.
- Receives only their own current access JWT for a Spark session; does not receive the Hub-stored refresh token, RustFS root keys, or Polaris bootstrap credentials.
- Cannot use Spark to write production or UAT data under the developer role.

## Analyst

**Role:** Uses notebooks and Spark to query approved production data.

**Goals**

- Sign in to JupyterHub with the Keycloak account already assigned to `role-default-analyst`.
- Query production data through Spark and Polaris using the analyst's own identity.

**Responsibilities and boundaries**

- Works in an isolated per-user Jupyter/Spark container.
- Receives only their own current access JWT for a Spark session; does not receive the Hub-stored refresh token, RustFS root keys, or Polaris bootstrap credentials.
- Cannot read UAT or development data and cannot write to any environment under the analyst role.
