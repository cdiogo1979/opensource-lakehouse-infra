# Business Rules — Airflow Keycloak SSO

## Identity and authorization
1. Airflow web UI login is authenticated through Keycloak OIDC using a dedicated `airflow` client in the `lakehouse` realm.
2. The browser callback target is the exact local FAB auth route on either supported loopback host: `http://localhost:8085/auth/oauth-authorized/keycloak` or `http://127.0.0.1:8085/auth/oauth-authorized/keycloak`.
3. The JupyterHub OIDC client remains dedicated to JupyterHub and is not reused for Airflow.
4. Successful browser login resolves or creates the Airflow user record and then applies the group-driven role mapping.
5. Access is allowed only when the user is in one of the approved Keycloak groups and the mapped Airflow role is recognized by the approved matrix.
6. The local Airflow admin account remains available as the break-glass recovery route and is not disabled by this design.

## Role mapping
7. `role-default-owner` maps to `Admin`.
8. `role-default-developer` maps to `Admin`.
9. `role-default-analyst` maps to `User`.
10. `role-default-writer` maps to `Viewer`.
11. Unknown or unapproved groups do not grant additional privileges.

## Failure and safety
12. Missing, invalid, expired, or mismatched Keycloak claims fail closed and do not broaden access.
13. If the metadata discovery or token exchange fails, the SSO flow is rejected and no fallback identity is granted.
14. API and service-account behavior remain unchanged; the scope remains browser-only login for the Airflow web UI.
15. Local deploy and loopback constraints remain enforced; no remote or production hostnames are introduced.

## Operational constraints
16. The Airflow client secret is stored only in existing protected secret plumbing and is not exposed through logs or non-protected paths.
17. The design preserves the local admin fallback while keeping the Keycloak-based web SSO as the standard login pathway.
18. Design validation occurs only within the approved local environment and does not broaden the project scope beyond the Airflow web UI SSO use case.
19. The Airflow login page offers both Keycloak OIDC and a separate local break-glass administrator login.
20. Local password authentication accepts only the configured `AIRFLOW_ADMIN_USERNAME`; other local accounts are not exposed as an alternate login path.
21. Local administrator credentials are checked by the existing FAB database-authentication mechanism. OIDC group synchronization does not change the local administrator's password-authenticated role.
22. Failure of the local password check or use of a non-administrator local username rejects the local login.
