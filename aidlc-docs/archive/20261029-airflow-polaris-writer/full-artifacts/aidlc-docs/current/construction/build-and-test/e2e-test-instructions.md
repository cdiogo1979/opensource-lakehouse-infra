# End-to-End Test Instructions

## Approved scope

Run only the main/production `main-init_environment` workflow after build, unit, contract, and local readiness checks pass and the implementation is confirmed available from the `main` Bundle. This workflow overwrites its configured sample table. UAT execution is excluded.

## Evidence

Record the exact Bundle/ref and DAG run ID, terminal status, and sanitized evidence that Spark used `write-service-account` authorized as `role-default-writer`, completed the configured Iceberg table operation, and used Polaris-vended RustFS credentials. Do not include tokens, secrets, or raw credential-bearing logs.

If any prerequisite is unresolved or the run cannot be completed, mark the E2E result blocked or unverified; do not substitute a different workflow or branch.
