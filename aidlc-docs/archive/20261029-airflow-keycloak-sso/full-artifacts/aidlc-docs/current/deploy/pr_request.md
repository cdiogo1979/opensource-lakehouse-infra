# PR Request — Airflow Keycloak SSO

## Problem

Airflow's browser UI used only local FAB authentication, while operators need to sign in through the existing Keycloak `lakehouse` realm without changing Airflow API authentication.

## Solution

Add a dedicated confidential Keycloak OIDC client for Airflow and configure FAB for Keycloak login alongside the local administrator recovery path. Authorization is restricted to the approved Keycloak groups, mapped to Airflow roles. The browser authorization endpoint uses the host-reachable Keycloak URL, while server-side token, user-info, and JWKS requests use Docker networking.

## Main changes

- Add Airflow OIDC security manager, login views, role mapping, and FAB configuration under `infra/airflow/`.
- Add an additive Airflow client and group-claim bootstrap in `infra/keycloak/bootstrap-realm.py`; register only the exact `localhost` and `127.0.0.1` FAB callbacks.
- Wire the protected OIDC secret and Keycloak network access in `docker-compose.airflow.yml`.
- Update startup DAG verification and add Airflow/Keycloak contract tests.
- Document design, test evidence, and operations under `aidlc-docs/current/`.

## Verification

- Full automated suite: 97 passed, 1 skipped, and 10 Hypothesis subtests passed before the live-startup corrections.
- Focused current Airflow client contract tests: 8 passed.
- Focused current Airflow SSO authorization contract tests: 6 passed.
- Airflow and dependencies are running; UI and API smoke checks returned HTTP 200.
- Both exact FAB callbacks were verified against Keycloak. The running FAB OAuth client loaded the configured issuer and successfully fetched the RS256 JWKS through Docker networking.
- Production and UAT DAG registration checks passed; no DAG was run.
- **Not verified:** Successful interactive login after the JWKS correction, callback completion, and user role assignment have not yet been confirmed. Vulnerability scanning and performance testing were not run.

The user accepted Build and Test as complete on 2026-10-30. That acceptance does not turn the unverified interactive login into a passing test.

## Deployment

Ordered local deployment and validation steps are required; see [deploy_instructions.md](./deploy_instructions.md). This handoff does not authorize deployment or additional persistent changes.

## Risks and limitations

- A successful post-fix browser login remains a required operational check before relying on SSO.
- The Keycloak client and mapper are persistent realm configuration. The bootstrap is additive and no automated rollback for these realm entries exists.
- The Airflow service remains loopback-bound; the configured callbacks assume host port `8085`.
- The infrastructure workspace has no Git metadata, so this is a proposed PR description only; no PR was created.
