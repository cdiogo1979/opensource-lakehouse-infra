# Unit 1 Business Rules — JupyterHub Foundation and OIDC Admission

## Authentication rules

1. Authenticate through browser-based OIDC Authorization Code flow against Keycloak realm `lakehouse`.
2. Do not collect the user's Keycloak password in JupyterHub and do not use Resource Owner Password flow.
3. Validate OIDC response correlation and token identity before accepting a Hub session. Any missing, invalid, expired, or mismatched required value denies login.
4. Keep OAuth token state encrypted in Hub-owned storage. Do not send refresh tokens to user servers or persist client secrets in user homes.

## Admission rules

1. Admit only users in `role-default-developer` or `role-default-analyst`.
2. Membership in both approved groups is allowed. Both roles are retained, and Polaris applies the union of their grants. Given current grants, the effective data permission is read production/UAT/dev and write dev only.
3. Membership in owner/writer groups does not by itself admit a user to JupyterHub.
4. Missing group data, unresolved identity, or Keycloak group-query failure is a denial; do not infer membership from a username or cached client-supplied value.
5. Re-evaluate eligibility before a new user server spawn.

## Server and home rules

1. Each admitted Hub identity is associated with one default Jupyter/Spark server and one separate persistent home.
2. Duplicate requests during server startup do not create a second server for the same user.
3. Only the owning user's server can access their home. One user's server cannot access another user's home or runtime state.
4. Hub is the only component allowed to control the container engine. User servers do not receive the Docker socket.
5. Stopping, restarting, or failing to start a server does not delete the home volume or place credentials in it.
6. A failed or partial spawn must be cleaned up before retry; the persistent home remains available to the same user identity.

## Membership change rules

1. If an approved group is removed while a user's server is running, stop the server at the next Hub auth-state/admission revalidation.
2. If no automatic revalidation event is available, require an operator to stop the server; do not claim immediate revocation.
3. After ineligibility is observed, deny future starts. Re-admission requires current approved group membership.
4. Membership in both groups follows the explicit union behavior; removing one group leaves the remaining group's access, subject to revalidation and Unit 3 Polaris grants.

## Failure and audit rules

- Authentication, eligibility, auth-state persistence, and server lifecycle failures fail closed.
- Do not log access tokens, refresh tokens, client secrets, or other secret material. Log only validated identity and safe failure metadata.
- Distinguish authentication denial, group admission denial, auth-state failure, and spawn failure without exposing credentials.
- This unit does not implement the Spark broker, Polaris authorization, or temporary storage credentials; those rules belong to Units 2 and 3.
