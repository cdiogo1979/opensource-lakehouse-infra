# End-to-End Test Instructions — Airflow Keycloak SSO

## Status

An interactive browser flow is relevant to this feature, but the approved requirements restrict this stage to automated tests and non-mutating local/configuration validation. Therefore, no browser E2E test is authorized or reported as passing.

## Deferred scenario

After separate authorization for runtime verification, test a user with each approved group through Keycloak, confirm the callback and Airflow role assignment, verify that an unapproved user is denied, and verify that the local administrator can still sign in through the separate password route. Do not execute this scenario during the current Build and Test stage.
