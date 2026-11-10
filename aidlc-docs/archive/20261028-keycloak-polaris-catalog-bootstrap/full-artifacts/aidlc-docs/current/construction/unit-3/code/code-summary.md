# Unit 3 Code Generation Summary — RustFS Storage

- Added `infra/rustfs/bootstrap-buckets.py`, a dependency-free SigV4 helper that creates only the approved missing buckets and preserves existing objects.
- Added `scripts/verify-rustfs-sts.py`, which requests a temporary 15-minute STS session with a single dev probe object policy, verifies dev allow/production deny, and deletes only its unique test object.
- Updated `scripts/prepare-lakehouse-runtime.py` to place protected RustFS STS signing credentials in the Polaris server's protected application properties and read-only mount. The values are not part of Spark client config or output.
- Documented the product storage map, credential path, limits, and operator commands in `README.md`.
- No persistent RustFS objects were deleted; the temporary verification object was removed. The three approved buckets were verified and preserved.

## Build/test handoff

See `construction/unit-3/build-test-report.md`. RustFS bucket and inline session-policy behavior passed. Polaris-created catalog storage configuration, Iceberg REST vended credentials, Spark, and the complete access matrix remain U4 integration checks.
# U4 continuation update — 2026-10-28

- Added `infra/polaris/bootstrap-default-catalogs.py` to create or verify the three approved S3 catalogs and namespaces idempotently, conflict-check existing storage mappings, and preserve data.
- Updated runtime preparation to create a protected initial `platform-admin-password`. Keycloak bootstrap now provisions a dedicated `platform-admin` if absent, forces a password change, and assigns product-owner membership.
- Added `infra/spark-bootstrap/create_smoke_tables.py` and `scripts/run-bootstrap-smoke-spark.sh` for the writer OIDC Spark job, read-only secret mounts, Polaris catalog requests, and smoke-table verification.
- Live checks passed for all three bucket names, all catalogs/namespaces, four Polaris principal roles and catalog grants, Keycloak owner membership, and Keycloak-to-Polaris reconciliation.
- Spark integration remains blocked by Iceberg 1.8.1 dropping `Polaris-Realm` during RustFS STS credential refresh. The partial production smoke table remains as created by the failed attempt; no cleanup or destructive retry was performed.
