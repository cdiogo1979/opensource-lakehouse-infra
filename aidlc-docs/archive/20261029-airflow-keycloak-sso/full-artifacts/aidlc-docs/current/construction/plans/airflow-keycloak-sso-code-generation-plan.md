# Code Generation Plan — Airflow Keycloak SSO

## Unit Context
- Intent ID: `20261029-airflow-keycloak-sso`
- Unit: `airflow-keycloak-sso`
- Project type: Brownfield infrastructure integration.
- Scope: Browser-only Airflow web UI login through a dedicated `airflow` OIDC client in the existing Keycloak `lakehouse` realm.
- Explicit exclusions: Airflow API/service-account auth redesign, changes to the JupyterHub OIDC client, MFA policy changes, interactive login verification, persistent Keycloak realm mutations, and production deployment.
- Requirements source: `aidlc-docs/current/inception/requirements/requirement-verification-questions.md`. The expected narrative `requirements.md` is absent; the approved answers and functional-design artifacts are the available baseline.
- Functional-design source: `aidlc-docs/current/construction/airflow-keycloak-sso/functional-design/`.
- Runtime boundary: Airflow is published on loopback at port `8085`; callbacks are the exact `localhost` and `127.0.0.1` URLs for FAB's mounted `/auth/oauth-authorized/keycloak` route.
- Existing fallback: Keep the protected local FAB administrator bootstrap unchanged and usable.

## Traceability and Dependencies

| Requirement | Generation coverage |
|---|---|
| Human Airflow web UI login via Keycloak `lakehouse` realm | Steps 2–4 |
| Dedicated confidential Airflow OIDC client and exact callback | Steps 2–3 |
| Only approved groups receive mapped Airflow roles | Steps 2–3 and 5 |
| First successful authorized login provisions the Airflow user | Step 3 |
| Protected local admin remains the break-glass path | Step 4 |
| Existing API and service-account behavior stays unchanged | Steps 1, 4, and 5 |
| No secret values in logs or documentation | Steps 2, 4, and 5 |
| Verification stays within approved automated checks and non-mutating local Compose validation | Step 5 |

Dependencies:
- Airflow `3.3.2` uses `FabAuthManager`.
- Keycloak bootstrap and the existing JupyterHub client have contract tests under `tests/keycloak/`.
- `scripts/provision-airflow-secrets.sh` already provisions `keycloak-airflow-client-secret`; this plan treats that as existing work and does not add another secret-generation path.
- `scripts/lakehouse.sh start-airflow` prepares Airflow secrets before bootstrapping the Keycloak realm and starting Airflow.
- User stories and units-generation artifacts were skipped by the approved execution-plan scope; the approved requirements are used for traceability.

## Detailed Generation Plan

### Step 1: Reconcile the approved contract and validate the pinned integration surface
- [x] Use the approved requirements answers and functional design as the source of truth; do not infer requirements from the missing `requirements.md`.
- [x] Confirm the FAB OIDC configuration and authorization hook supported by the pinned Airflow/FAB versions. Airflow constraints pin `apache-airflow-providers-fab==3.9.0` and `flask-appbuilder==5.2.2`; the FAB documentation supports OAuth through `webserver_config.py`, `FabAirflowSecurityManagerOverride`, and `get_oauth_user_info`.
- [x] Resolve the functional-design wording about unmatched groups against the explicit rule that only approved groups receive access. The approved interpretation is to reject login when no approved group maps to an Airflow role; no default role grants access.
- [x] Confirm how multiple approved group claims are handled. The approved interpretation is to assign roles for all matched approved groups and ignore unknown groups.
- [x] Resolve the local password fallback conflict: the user selected simultaneous Keycloak OIDC and local password login, with the local password path restricted to `AIRFLOW_ADMIN_USERNAME`.
- [x] Confirm the pinned FAB extension points support a custom security manager and custom OAuth view. FAB uses Flask's configured Jinja loader and does not provide an extra template-folder option; the user approved rendering the two small login pages inline with `render_template_string` rather than adding loader plumbing.

### Step 2: Add the dedicated Airflow client and group-claim contract
- [x] Modify `infra/keycloak/bootstrap-realm.py` to define a confidential `airflow` OIDC client using Authorization Code flow, with direct grants and service accounts disabled.
- [x] Restrict redirect URIs to the exact loopback callbacks `http://localhost:8085/auth/oauth-authorized/keycloak` and `http://127.0.0.1:8085/auth/oauth-authorized/keycloak`; do not reuse or alter the JupyterHub client.
- [x] Add an idempotent group-membership mapper for the `groups` claim and reject conflicting pre-existing Airflow client or mapper configuration rather than silently broadening it.
- [x] Read the Airflow client secret from the existing protected credential file without printing its value.
- [x] Update `infra/keycloak/realm-contract.json` to describe the dedicated client, callback, and group claim without storing any secret.
- [x] Add `tests/keycloak/test_airflow_client_contract.py` covering client flags, exact callback, group mapper claims, idempotency, and conflict rejection.

### Step 3: Configure Airflow FAB OIDC login and role assignment
- [x] Create `infra/airflow/webserver_config.py` using the supported configuration surface confirmed in Step 1.
- [x] Configure the Keycloak issuer/endpoints, client ID, protected client-secret file, callback behavior, user identity mapping, and role synchronization.
- [x] Configure FAB with a custom OAuth view that offers the Keycloak option and a separate local administrator sign-in route.
- [x] Add a local password form using FAB database authentication, restricted to `AIRFLOW_ADMIN_USERNAME`; do not expose general local-user registration.
- [x] Render the OAuth login page with a local-admin link and the admin-only password form inline from the custom FAB view; do not add standalone templates or a custom Jinja loader.
- [x] Map `role-default-owner` and `role-default-developer` to `Admin`, `role-default-analyst` to `User`, and `role-default-writer` to `Viewer`.
- [x] Provision a user on first successful login only when at least one approved group maps to a recognized Airflow role; reject an unmatched or missing group claim without granting a default role.
- [x] For multiple approved group claims, assign the roles corresponding to every matched group; do not grant roles for unknown groups.
- [x] Create `infra/airflow/airflow_oauth_security_manager.py` extending `FabAirflowSecurityManagerOverride` to reject login when no approved groups are present and to avoid default-role access.
- [x] Create `infra/airflow/airflow_sso_roles.py` with dependency-free group-to-role mapping helpers so the role and deny-by-default contract can be unit tested without loading Airflow.
- [x] Keep local FAB database login independent of OAuth role synchronization so the local administrator retains its break-glass role.
- [x] Add `tests/airflow/test_keycloak_sso_contract.py` for settings, claim handling, role mappings, deny-by-default behavior, first-login provisioning, and the admin-only local login path.

### Step 4: Wire secrets and preserve existing Airflow behavior
- [x] Modify `docker-compose.airflow.yml` to make OIDC configuration available to the Airflow API server and mount the Airflow client secret read-only into the API server and the short-lived initialization service, because FAB's admin-user CLI loads the same webserver configuration.
- [x] Connect only the Airflow API server to the existing `core` network and make it depend on healthy Keycloak so server-side OIDC calls can reach the identity provider; do not add a network or expose Airflow beyond loopback.
- [x] Ensure OIDC settings and client credentials are not unnecessarily exposed to scheduler, DAG processor, triggerer, or token broker containers.
- [x] Modify `infra/airflow/Dockerfile` to install or copy only configuration/helper files required by the approved design; do not add dependencies unless the pinned image lacks the supported FAB OIDC integration.
- [x] Modify `scripts/lakehouse.sh` so Airflow-specific client bootstrap receives the exact approved callback and secret path after Airflow secret provisioning, without changing ordinary Keycloak/JupyterHub startup behavior.
- [x] Preserve `infra/airflow/bootstrap-airflow-admin.py`, existing API/JWT configuration, the writer-token broker client, and all JupyterHub OIDC behavior.
- [x] Retain the existing `scripts/provision-airflow-secrets.sh` client-secret entry; no secret values are displayed.

### Step 5: Validate generated files without mutating runtime state
- [x] Run focused unit/contract tests for the Airflow client, group mapper, FAB config, access rejection, role mapping, and local-admin preservation.
- [x] Run existing `tests/keycloak/test_jupyterhub_client_contract.py` to verify the JupyterHub client remains unchanged.
- [x] Validate Python syntax and the merged Airflow Compose configuration, including callback and secret mount paths.
- [x] Do not start services, perform browser login, or persist Keycloak realm changes in Code Generation; runtime verification boundaries are governed by the approved requirements and Build and Test stage.
- [x] Confirm no test output, generated documentation, or logs contain secret values.

### Step 6: Record the generation summary
- [x] Create `aidlc-docs/current/construction/airflow-keycloak-sso/code/code-summary.md` listing created/modified files, role mapping, preserved boundaries, and tests to run in Build and Test.
- [x] Update this plan and `aidlc-docs/current/aidlc-state.md` after each approved generation step; do not start generation until the plan approval gate is passed.

## Expected Files

Application/configuration and tests:
- Modify `infra/keycloak/bootstrap-realm.py`
- Modify `infra/keycloak/realm-contract.json`
- Modify `docker-compose.airflow.yml`
- Modify `infra/airflow/Dockerfile`
- Modify `scripts/lakehouse.sh`
- Create `infra/airflow/webserver_config.py`
- Create `infra/airflow/airflow_oauth_security_manager.py` for the approved group validation and role mapping
- Create `infra/airflow/airflow_auth_views.py` for the combined login view and admin-only local route
- Create `infra/airflow/airflow_sso_roles.py` for dependency-free role mapping and authorization decisions
- Create `tests/keycloak/test_airflow_client_contract.py`
- Create `tests/airflow/test_keycloak_sso_contract.py`
- Retain `scripts/provision-airflow-secrets.sh` as already containing the client-secret provisioning entry; no secret values are included in source or docs
- Retain `infra/airflow/bootstrap-airflow-admin.py` unchanged

Workflow documentation:
- Create `aidlc-docs/current/construction/airflow-keycloak-sso/code/code-summary.md`

## Generation Completion Criteria
- Airflow browser SSO uses a dedicated confidential Keycloak client and exact loopback callback.
- Only the approved group-role matrix can grant Airflow web UI access; missing/unapproved group claims do not fall back to a default role.
- First-login provisioning and mapped role synchronization are covered by focused tests.
- Local admin fallback, API authentication, token-broker behavior, and JupyterHub OIDC remain unchanged.
- Compose and configuration checks pass without starting services or mutating a persistent realm.
- All code-generation steps are checked off and generated code is presented for explicit review before Build and Test.

## Approval Gate
The earlier version of this Code Generation Part 1 plan was approved, but its approval was superseded when FAB OAuth-only login was found to omit the local password form. The revised Functional Design and this revised plan were explicitly approved by the user on 2026-10-30. The user subsequently approved inline template rendering after source verification showed that FAB does not add the repository template folder to its Jinja loader. Code Generation Part 2 is authorized to proceed in the listed order.

References:
- Apache Airflow FAB authentication documentation: https://airflow.apache.org/docs/apache-airflow-providers-fab/stable/auth-manager/webserver-authentication.html
- Airflow 3.3.2 Python 3.10 constraints: https://raw.githubusercontent.com/apache/airflow/constraints-3.3.2/constraints-3.10.txt
