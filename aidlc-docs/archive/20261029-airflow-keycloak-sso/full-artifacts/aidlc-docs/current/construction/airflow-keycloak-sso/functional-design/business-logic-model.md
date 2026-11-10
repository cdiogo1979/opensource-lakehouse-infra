# Business Logic Model — Airflow Keycloak SSO

## Overview
The Airflow web UI authenticates end users through Keycloak OIDC. The design is intentionally limited to the browser login flow and uses the existing `lakehouse` realm. The Airflow login flow resolves the user identity from Keycloak, validates group membership, and applies the approved role mapping before granting web UI access.

## Core process
1. User navigates to the Airflow web UI on the local loopback host.
2. The login page offers Keycloak OIDC as the normal login and a separate local administrator sign-in as the break-glass option.
3. For Keycloak login, Airflow redirects the browser to Keycloak; Keycloak authenticates the user and returns the browser to the Airflow callback.
4. Airflow exchanges the authorization response for tokens and retrieves the authenticated user claims.
5. Airflow resolves the Keycloak identity and reads the approved `groups` claim.
6. Airflow maps every recognized approved group to its Airflow role; unknown groups do not grant roles.
7. If no approved group maps to an Airflow role, the OIDC login is rejected and no default-role access is granted.
8. For local break-glass login, Airflow validates the existing FAB database credentials and accepts only the configured local administrator account.
9. A failed local credential check or a non-administrator local username is rejected. Local login does not alter Keycloak identity or group mappings.

## Business logic rules
- The only supported login method for this unit is Keycloak OIDC for the browser UI.
- The user must belong to an approved Keycloak group in the configured mapping matrix.
- The Airflow login page must keep both Keycloak OIDC and the local break-glass administrator login available.
- The local password route is limited to the configured Airflow administrator account; it is not a general local registration or alternate user-provisioning path.
- The Airflow local admin account remains available as a break-glass fallback and is not disabled by this design.
- The project does not alter API auth or service-account behavior outside the web UI SSO boundary.

## Actors and responsibilities
- Browser user: starts the Airflow web login and completes the OIDC challenge.
- Keycloak: authenticates the user, issues tokens, and provides group claims.
- Airflow web UI: enforces role mapping and access decisions.
- Local admin: operational recovery path outside the standard OIDC login route.

## Decision table
| Condition | Result |
|---|---|
| Valid Keycloak login + approved group mapping | Access granted according to mapped Airflow role |
| Valid Keycloak login + no approved group mapping | Minimal/default access only; no broader grant |
| Keycloak discovery/token/group claim unavailable | Authentication fails closed |
| Local admin fallback required | Admin can recover through existing local admin route |
| API/service-account auth requested | Unchanged; no scope expansion |
