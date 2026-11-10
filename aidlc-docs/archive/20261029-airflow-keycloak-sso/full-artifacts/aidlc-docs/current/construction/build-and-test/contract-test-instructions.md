# Contract Test Instructions — Airflow Keycloak SSO

## Run contract suites

```bash
python3 tests/keycloak/test_airflow_client_contract.py
python3 tests/keycloak/test_jupyterhub_client_contract.py
python3 tests/airflow/test_keycloak_sso_contract.py
```

## Contracts verified

- The dedicated client is confidential, uses Authorization Code flow, disables direct grants and service accounts, and has only the approved callback.
- The group mapper exposes the `groups` claim to the access token and user-info endpoint; conflicting mapper configuration is rejected and an identical mapper is idempotent.
- Approved Keycloak groups map only to their specified Airflow roles; missing, malformed, and unapproved groups do not authorize a login.
- The local administrator username is kept out of OAuth role synchronization, and local password authentication is available only through the dedicated admin-restricted route.
- The pre-existing JupyterHub client contract remains unchanged.

These are local automated contract tests. They do not call Keycloak or mutate a realm.
