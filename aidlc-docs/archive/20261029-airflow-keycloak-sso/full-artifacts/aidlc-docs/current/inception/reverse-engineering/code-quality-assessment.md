# Code Quality Assessment — Airflow / Keycloak Authentication

## Existing controls

- Airflow and Keycloak configuration is versioned as code.
- The Keycloak bootstrap reconciles declared client settings and fails closed on unexpected existing-client conflicts.
- The Airflow admin bootstrap reads its password from a mounted secret and suppresses CLI output.
- UI endpoints bind to loopback in the local Compose setup.
- Python tests cover existing Keycloak and JupyterHub OIDC contracts.

## Gaps relevant to this intent

- No Airflow OIDC client or Keycloak callback is declared in the inspected realm contract.
- Airflow's local admin is bootstrapped, but a documented human-user onboarding/role-mapping lifecycle for SSO is absent.
- No Airflow SSO callback, state/nonce validation, userinfo mapping, role synchronization, logout, or negative-auth tests are present in the inspected source.
- The README contains older text describing Airflow as deferred; canonical architecture has since recorded Airflow workload execution as supported. Documentation should be reconciled if the intent reaches implementation.

## Risk assessment

Authentication and authorization integration affects access to Airflow's scheduling interface, which can execute privileged workloads. Requirements should explicitly define allowed users/groups, Airflow roles, account provisioning, local fallback, and exposure boundaries before implementation.
