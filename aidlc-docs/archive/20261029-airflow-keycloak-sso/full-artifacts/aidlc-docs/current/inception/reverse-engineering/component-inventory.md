# Component Inventory — Airflow / Keycloak SSO Scope

## Relevant applications and services

| Component | Type | Current authentication responsibility |
|---|---|---|
| Airflow API server/UI | Application | FAB auth manager; local Airflow user login |
| Airflow initialization | Bootstrap task | Creates local Airflow admin and Git connection |
| Airflow metadata PostgreSQL | Database | Airflow/FAB users, roles, and application metadata |
| Keycloak lakehouse realm | Identity provider | Human OIDC for JupyterHub and service identity tokens |
| Airflow writer token broker | Internal service | Issues run-scoped writer tokens; not browser login |
| JupyterHub | Application | Human Keycloak OIDC login using its own client and admission logic |

## Scope note

This is a focused authentication-boundary inventory rather than a full inventory of the lakehouse platform. Existing Polaris, RustFS, Spark, and workload Bundles are downstream or adjacent components and are not changed by the stated SSO intent unless requirements expand scope.
