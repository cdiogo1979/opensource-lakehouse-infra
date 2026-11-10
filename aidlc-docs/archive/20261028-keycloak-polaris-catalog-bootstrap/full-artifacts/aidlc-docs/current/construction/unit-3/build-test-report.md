# Unit 3 Build and Test Report — RustFS Storage

**Status: STORAGE PRIMITIVES VERIFIED; POLARIS/SPARK INTEGRATION DEFERRED TO U4.**

> Follow-up: U4 later completed the Spark smoke-table create/write/read and vended-credential checks in production, dev, and UAT. See `unit-4/build-test-report.md`. The original U3 execution notes below record the state at the time of that unit's test run.

## Checks completed

- Python compilation passed for `infra/rustfs/bootstrap-buckets.py`, `scripts/verify-rustfs-sts.py`, and the runtime configuration generator.
- `scripts/prepare-lakehouse-runtime.py` staged protected RustFS keys into Polaris's protected application-properties configuration; credential values were not printed.
- Polaris was recreated to load the new config and returned to healthy status. Container-side checks confirmed both STS credential properties are present without displaying their values. All five core services are healthy.
- `infra/rustfs/bootstrap-buckets.py` verified `bucket-default`, `bucket-default-dev`, and `bucket-default-uat`. The buckets already existed after the approved fresh-storage bootstrap and were preserved; no objects were removed.
- `scripts/verify-rustfs-sts.py` passed against the pinned RustFS 1.0.4 service. RustFS issued temporary STS credentials with a dev-only inline policy. Dev bucket listing and write under a unique `default_lhdev/` probe key succeeded; production bucket listing and write were denied. The exact dev probe object was removed with the temporary session.
- `docker compose config --quiet` passed.

## Limits and remaining checks

- RustFS enforces a minimum 900-second STS session lifetime. The policy is location/operation scoped, but an issued session can outlive a five-minute Keycloak token. Polaris/Spark refresh and post-revocation behavior require U4 integration checks.
- The check proves RustFS's AssumeRole and inline session-policy behavior, not that Polaris 1.8.0 generated exactly the expected policy or Spark received/refreshed it. No catalog or table was created in U3.
- U4 created all three Polaris catalogs and namespaces and applied the role grants. The Spark proof is blocked by an Iceberg 1.8.1 defect: the S3 vended-credential refresh call omits custom `Polaris-Realm`, and Polaris correctly rejects the request because `polaris.realm-context.require-header=true`. A Spark attempt created only the production smoke-table metadata before the storage write failed; the dev and UAT smoke tables are absent. The exact production table name is `lakehouse.default_lh.bootstrap_smoke_test`.
- The first Spark attempt also confirmed that the cached Spark image has a stale default catalog at `http://rest:8181`; the job now overrides it to the approved Polaris catalog. This issue is fixed in the script.
- The safe fix options are to use an Iceberg runtime with a reviewed header-propagation fix, or obtain explicit approval to make `lakehouse` the default realm by disabling the realm-header requirement. The latter was rejected by automatic approval review in this run and was not applied. No alternate path was used to bypass that rejection.
- Bucket provisioning currently uses the protected RustFS root identity. It remains an operator-only local bootstrap input; ordinary human and writer clients do not receive it. Replacing it with a least-privilege RustFS provisioning principal is a future hardening item.
- The Polaris server holds a protected RustFS STS signing credential. Confirm the supported production credential-delivery/rotation method before shared deployment.

## Conclusion

U3's bucket and RustFS STS primitives passed on the running `lakehouse-local` stack. End-to-end data-product completion still requires U4 catalog creation, Polaris-vended credentials, Spark smoke tables, role matrix checks, and safe reruns.
