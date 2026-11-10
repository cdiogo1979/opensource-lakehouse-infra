# Functional Design Plan — environment-reset-bootstrap-users

## Verified Findings (2026-10-31, read-only)
| # | Topic | Finding |
|---|---|---|
| R1 | Polaris roles | Polaris principal-role names equal the Keycloak group names. `reconcile-keycloak-groups.py` maps the four `role-default-*` groups to same-named principal roles. Catalog grants exist only for those four roles. |
| R2 | Polaris token roles | `bootstrap-realm.py` assigns the `polaris` client role of the same name to each group (`add_client_role_to_group`) and adds a client-role mapper per client (`ensure_mapper`). Tokens carry `resource_access.polaris.roles`. |
| R3 | JupyterHub | Admits only `role-default-developer` and `role-default-analyst` (`APPROVED_GROUPS`). Owners are not admitted. |
| R4 | Airflow | `airflow_sso_roles.GROUP_ROLE_MAPPING` and `webserver_config.AUTH_ROLES_MAPPING` both list groups. |
| R5 | Jenkins / RustFS | Jenkins: the configuration-as-code `globalMatrix`. RustFS: group-named policies in `bootstrap-policies.ACCESS_MATRIX`. |
| R6 | Writer broker | `_issue_token` uses `client_credentials`. `_jwt_expiry` checks the issuer, `azp == KEYCLOAK_WRITER_CLIENT_ID`, the `role-default-writer` Polaris role, and a lifetime of at most 3605 s. |
| R7 | Writer consumers | `create_smoke_tables.py`, `run-bootstrap-smoke-spark.sh`, `verify-polaris-keycloak-auth.py`, `verify-keycloak-outage.py`, and `verify-polaris-oidc-negative-cases.py` (principal `service-account-write-service-account`) all depend on the writer identity. |
| R8 | Bundle path | Only `lakehouse.sh`, `provision-airflow-secrets.sh`, `validate-bundle-config.py`, and the `docker-compose.airflow.yml` environment use `LAKEHOUSE_PROJECT_ROOT`. Bundles clone from GitHub. |
| R9 | Reset inventory | All v2 containers carry the Compose label `com.docker.compose.project=lakehouse-local`. Per-run containers carry `lakehouse-local.role=*`. Jupyter homes are named `lakehouse-jupyter-home-*`. Volumes and networks use exact `lakehouse-local_*` names. |

## Plan Steps
- [x] Verify the current mappings, writer flow, Bundle path, and reset inventory (R1–R9)
- [x] Design questions: none. Requirements answers Q1–Q13 and C1–C3 settle every decision.
- [x] Define domain entities, business rules, and business logic model
