# Security Test Instructions — Airflow Keycloak SSO

## Automated authorization checks

Run the Airflow SSO and Keycloak client contract tests listed in `contract-test-instructions.md`. Verify that:

- OAuth users without an approved group, with a malformed group claim, or with a username matching `AIRFLOW_ADMIN_USERNAME` are rejected before FAB user provisioning.
- Multiple approved groups assign all distinct mapped roles; unknown groups add no role.
- The local password route authenticates only the configured admin username through FAB database authentication.
- The OIDC client secret is read from the protected Docker secret file, is mounted read-only to the API server only, and is absent from the realm contract and logs.
- The Airflow API server is not published beyond the existing loopback binding.

## Tooling and limits

No vulnerability scanner is configured in this workspace's Jenkins pipeline. Do not add a scanner or perform penetration testing as part of this stage. No interactive auth flow or persistent realm mutation is authorized; those checks remain unverified.
