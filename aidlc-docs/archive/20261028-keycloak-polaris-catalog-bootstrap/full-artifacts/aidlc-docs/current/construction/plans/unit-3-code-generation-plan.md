# Unit 3 Code Generation Plan — RustFS Storage

## Approved scope

Implement the approved storage contract from the Application Design and Unit of Work: create or validate `bucket-default`, `bucket-default-dev`, and `bucket-default-uat`; prepare protected server-side RustFS STS credentials for Polaris; and provide a reproducible policy-scope verifier.

## Boundaries

- Preserve existing bucket contents and the RustFS data volume.
- Do not distribute static RustFS credentials to Keycloak users or Spark.
- Keep catalog creation and Polaris-generated credential validation with U4.
- Avoid adding a long-running service or dependency for bucket provisioning.
- Never print keys, session credentials, tokens, or secret-bearing provider responses.

## Implementation result

Generated `infra/rustfs/bootstrap-buckets.py` and `scripts/verify-rustfs-sts.py`; updated `scripts/prepare-lakehouse-runtime.py` to supply the protected S3 signing credential only to Polaris; documented operator flow and limits. The parent request to proceed through completion authorizes this implementation against the already-approved product and storage contracts.

## Status

**IMPLEMENTED.** Source compilation, Compose validation, live bucket checks, and a live RustFS 1.0.4 STS allow/deny test passed. See `construction/unit-3/code/code-summary.md` and `construction/unit-3/build-test-report.md`.
