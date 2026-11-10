# Functional Design Plan — Airflow Keycloak SSO

## Unit context
- Unit name: `airflow-keycloak-sso`
- Project: `opensource-lakehouse-infra-v2`
- Scope: browser-only Airflow web UI SSO via the existing `lakehouse` Keycloak realm
- Requirements baseline: approved requirement set for the Airflow Keycloak SSO intent
- Boundary: local loopback deployment; no API auth redesign; local Airflow admin remains as break-glass fallback

## Functional design checklist
- [x] Confirm the browser-only auth boundary and authorized user persona model
- [x] Define the dedicated Airflow OIDC client and callback contract
- [x] Define Keycloak group-to-Airflow-role mapping and deny-by-default behavior
- [x] Specify first-time user provisioning and fallback behavior
- [x] Capture security, failure, and verification constraints for the local environment

## Detailed plan
### Step 1: Confirm unit boundary and scope
- [x] Validate the unit is limited to browser UI login for Airflow and not the Airflow REST API or service-account model.
- [x] Confirm the Airflow local admin fallback remains active and outside the Keycloak login path.

### Step 2: Define the OIDC web login contract
- [x] Specify the dedicated Keycloak client for Airflow under the `lakehouse` realm.
- [x] Define the browser callback URLs for both supported loopback hosts using FAB's `/auth/oauth-authorized/keycloak` route.
- [x] Confirm the flow uses the existing local Keycloak issuer pattern and Access/ID token exchange model for FAB OIDC.

### Step 3: Define authorization and role mapping
- [x] Document the approved group mapping matrix for Airflow roles.
- [x] Define the deny-by-default rule when a user has no approved group mapping or no valid Keycloak claims.
- [x] Define how Airflow resolves role assignment when groups are absent or mismatched.

### Step 4: Define user provisioning behavior
- [x] Specify how first-time successful Keycloak login creates or resolves the Airflow user identity.
- [x] Define how group membership drives the Airflow role when the user first logs in.
- [x] Specify preservation of the local admin fallback and admin-only recovery path.

### Step 5: Define failure and security rules
- [x] Document client-secret handling and local trust-boundary constraints.
- [x] Document how discovery, token, and group claim failures fail closed.
- [x] List the invariant that other Airflow auth models and service-account flows remain unchanged.

### Step 6: Build design artifacts
- [x] Create `business-logic-model.md` for the browser login and role assignment process.
- [x] Create `business-rules.md` for the OIDC / group-mapping constraints.
- [x] Create `domain-entities.md` for user, role, realm, and claim entities used by the login flow.

### Step 7: Validate design completeness against requirements
- [x] Check that the approved requirement answers are mapped to the design artifacts.
- [x] Verify no scope expansion beyond the approved browser-only SSO contract.
- [x] Present the completed design for user review and approval.

## Traceability to approved requirements
- Browser-only Airflow web UI SSO: covered by Steps 1-2 and 6.
- Existing `lakehouse` realm and dedicated client: covered by Step 2.
- Group-to-role mapping: covered by Step 3.
- Break-glass local admin fallback: covered by Steps 1 and 4.
- Loopback-only deployment: covered by Step 2.
- Preserve API auth behavior: covered by Steps 1 and 5.

## Status
- [x] Functional design plan and artifacts prepared
- [x] Original functional design approved by the user on 2026-10-30
- [x] Combined OIDC and local-admin login behavior added after the approved design was found incompatible with FAB OAuth-only login
- [x] Revised combined-login Functional Design approved by the user on 2026-10-30; Code Generation planning may resume
