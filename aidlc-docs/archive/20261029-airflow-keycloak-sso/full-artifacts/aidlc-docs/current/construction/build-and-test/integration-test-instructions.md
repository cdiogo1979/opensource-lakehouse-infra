# Integration Test Instructions — Airflow Keycloak SSO

## Purpose and verification boundary

This intent is limited to automated tests and non-mutating local/configuration validation. Do not start Airflow or Keycloak, perform a browser login, or persist client/mapper changes in a realm during this Build and Test run.

## Non-mutating integration checks

1. Validate the merged Compose configuration using the placeholder values in `build-instructions.md`.
2. Build the `airflow-api-server` image without starting services.
3. Run the complete repository pytest suite. The live provider-mutating role-matrix test must remain skipped.
4. Confirm the Airflow API server alone receives the Keycloak secret and joins the existing `core` network; scheduler, DAG processor, triggerer, and token broker must not receive the Airflow client secret.

## Deferred live integration scenarios

The following scenarios require separate approval because they start services or change persistent Keycloak state:

- Keycloak discovery/token/user-info exchange using the Airflow client.
- Browser redirect and callback round trip at `http://localhost:8085/auth/oauth-authorized/keycloak` (or `http://127.0.0.1:8085/auth/oauth-authorized/keycloak` when Airflow is opened through that host).
- First-time Airflow user provisioning and role synchronization against a running metadata database.
- Combined browser display of Keycloak SSO and local administrator password login.

Do not perform these as part of this stage. Record them as unverified, not as passing integration tests.
