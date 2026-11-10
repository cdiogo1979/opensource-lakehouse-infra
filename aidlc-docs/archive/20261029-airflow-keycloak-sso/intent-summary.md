# Intent Summary: Airflow Keycloak SSO

## Intent
Airflow Keycloak SSO (`20261029-airflow-keycloak-sso`)

## Objective
Enable browser-based Airflow UI authentication through the existing Keycloak lakehouse realm while preserving API auth and a local administrator recovery path.

## Date
2026-10-30

## Scope
Local Compose Airflow UI OIDC integration, Keycloak Airflow client and group mapper, role authorization, local-admin fallback, automated checks, and operational handoff. No production deployment or PR creation.

## Units / workstreams
Airflow FAB Keycloak OIDC and combined local-admin login, Keycloak client, callback, and group authorization bootstrap, Build, automated tests, local startup, and Deploy handoff

## Major requirements
- Provide browser-only Airflow UI sign-in through a dedicated confidential OIDC client in the existing Keycloak lakehouse realm.
- Authorize only users in approved groups and preserve a separate local administrator recovery login.
- Preserve existing Airflow API authentication and loopback service exposure.

## Architecture and design decisions
- Map role-default-owner and role-default-developer to Airflow Admin, role-default-analyst to User, and role-default-writer to Viewer.
- Register exact FAB callback URLs for localhost and 127.0.0.1 on port 8085; do not use redirect wildcards.
- Use keycloak.localhost for browser authorization, Docker-internal keycloak for server requests and JWKS, and the explicit Keycloak issuer with RS256 validation.

## Implementation decisions
- Implement a custom FAB security manager, combined login views, group-to-role filtering, and protected client-secret loading.
- Bootstrap the dedicated client and group mapper additively and reconcile only known prior exact callback values.
- Keep Airflow published on loopback and limit Keycloak network access to the API server.

## Deviations
- Live user login failed before the JWKS correction because the discovered key URL resolved to Airflow's container loopback. The internal JWKS endpoint was configured and verified reachable, but a successful post-fix user login was not confirmed.
- The startup DAG verifier was aligned with the actual test_environment DAG names and Airflow Compose overlay.

## Verification
Automated tests passed (full suite 97 passed, 1 skipped, 10 Hypothesis subtests before final runtime corrections; focused post-correction Keycloak client contract tests 8 passed and Airflow SSO authorization tests 6 passed). Local Airflow and Keycloak services are healthy; UI/API smoke checks, exact loopback callback matching, JWKS retrieval, and production/UAT DAG registration passed. The successful interactive Keycloak login and role assignment after the JWKS correction remain unverified. The user explicitly accepted this limitation and authorized intent closure; it is a waiver, not a passing test.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md

## Superseded decisions
- The originally planned callback http://127.0.0.1:8085/oauth-authorized/keycloak was replaced by the observed FAB route callbacks http://localhost:8085/auth/oauth-authorized/keycloak and http://127.0.0.1:8085/auth/oauth-authorized/keycloak.

## Archived artifacts
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/aidlc-docs/current/compaction/20261029-airflow-keycloak-sso/manifest.json
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/infra/airflow/Dockerfile
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/infra/airflow/airflow_auth_views.py
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/infra/airflow/airflow_oauth_security_manager.py
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/infra/airflow/airflow_sso_roles.py
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/infra/airflow/webserver_config.py
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/infra/keycloak/bootstrap-realm.py
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/infra/keycloak/realm-contract.json
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/docker-compose.airflow.yml
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/scripts/lakehouse.sh
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/scripts/verify-airflow-environment-dags.sh
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/tests/airflow/test_keycloak_sso_contract.py
- aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/tests/keycloak/test_airflow_client_contract.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261029-airflow-keycloak-sso/full-artifacts/`
