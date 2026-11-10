# Build and Test Summary — Airflow Keycloak SSO

## Build Status

- **Build Tool**: Docker Compose V2 with the pinned Airflow 3.3.2 / Python 3.10 base image.
- **Build Status**: Success.
- **Build Artifacts**: Local `local/lakehouse-airflow:3.3.2` image.
- **Build Time**: Not measured.
- **Runtime state**: `scripts/lakehouse.sh start-airflow` completed successfully after explicit user authorization. Required services are running, and the Airflow OIDC client is configured in the existing Keycloak realm.

## Test Execution Summary

### Python Code Quality

- **Status**: Syntax checks passed.
- **Commands**: Python AST parse for changed Python files, realm-contract JSON parse, and `bash -n scripts/lakehouse.sh` passed.
- **Linting**: No repository `code_quality.sh`, `requirements-dev.txt`, or `pyproject.toml` is configured; no separate Ruff/Black/Bandit run was available.

### Unit Tests

- **Total**: 97 passed, 1 skipped, and 10 Hypothesis subtests passed.
- **Status**: Pass.
- **Command**: `PYTHONPATH=infra/jupyter/hub .venv-ci/bin/python -m pytest -q tests --hypothesis-seed=20261030`
- **Environment note**: The repository Jenkinsfile's test command initially failed locally because the test environment lacked pytest and the JupyterHub runtime packages/module path. The full suite passed after installing the existing test and Hub requirement manifests into a temporary virtual environment and setting the same Hub module path used by its container. No CI configuration was changed.
- **Focused SSO contracts**: Airflow client (8), Airflow authorization (6), and existing JupyterHub client (6) tests passed.

### Integration Tests

- **Non-mutating integration checks**: Merged Compose configuration passed; the Airflow API-server image built; isolated imports of the custom security manager and view against the pinned Airflow/FAB runtime passed.
- **Live service smoke test**: Airflow API version endpoint returned HTTP 200; the UI root returned HTTP 200; `/auth/login/keycloak` returned HTTP 302 to Keycloak. For both `localhost` and `127.0.0.1`, the actual FAB callback URI was exactly registered in Keycloak, and its authorize endpoint returned HTTP 200. Keycloak realm bootstrap confirmed the Airflow client and four groups.
- **OIDC token-validation correction**: A user login attempt reached the FAB callback but failed because Keycloak discovery advertised `keycloak.localhost` for JWKS requests; inside Docker that hostname resolves to the Airflow container's loopback. FAB now uses the configured Keycloak issuer, RS256 algorithm, and Docker-internal JWKS URL. The restarted runtime loaded this configuration and fetched the JWKS successfully.
- **DAG registration**: Verified `main-test_environment` from `lakehouse-main` and `uat-test_environment` from `lakehouse-uat`; no DAG was run.
- **Interactive OIDC login and callback**: A user attempt previously failed at ID-token validation. The JWKS resolution cause has been corrected and checked in the running FAB client; a successful post-fix browser login and group-based allow/deny behavior still await user retry.
- **Status**: Startup, redirect matching, and runtime JWKS retrieval passed; successful interactive authentication remains unverified.

### Performance Tests

- **Status**: Not applicable; no performance targets were specified.

### Additional Tests

- **Contract tests**: Pass.
- **Security/authorization contract tests**: Pass.
- **Vulnerability scanning**: Not run; the repository has no configured scanner in its Jenkins pipeline.
- **End-to-end browser tests**: Not run; the interactive login callback and authorization matrix still require user-driven verification.

## Overall Status

- **Build**: Success.
- **Automated tests and static checks**: Pass.
- **Live authentication behavior**: Service readiness, exact callback matching, and Keycloak signing-key retrieval were verified. A previous interactive attempt failed before identity provisioning; a successful post-fix login and role assignment remain unverified.
- **Ready for Deploy handoff**: The user accepted Build and Test as complete on 2026-10-30. Successful post-fix interactive login and role assignment remain unverified; this acceptance does not report them as passing.

## Next Steps

The Deploy handoff is prepared at `aidlc-docs/current/deploy/`. Local service startup and Airflow client bootstrap were separately authorized for testing; deployment and any further persistent changes require separate authorization.
