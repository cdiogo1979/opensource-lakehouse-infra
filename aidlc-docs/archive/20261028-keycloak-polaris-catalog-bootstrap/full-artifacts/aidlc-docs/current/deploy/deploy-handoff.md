# Deploy Handoff — Default Lakehouse Product Bootstrap

## Handoff decision

The local Docker Compose implementation and default-product bootstrap are ready for operator review. This handoff does not run a deployment or claim production readiness. The user accepted a verification waiver for the remaining Unit 2 gaps: the human PKCE callback flow and a subset of reconciliation failure-path diagnostics remain unverified. Continue with a local development deployment only.

## Intended environment

- One developer machine running Docker Engine and Docker Compose V2.
- Python 3 available on the host.
- Loopback-only published services; this is a local single-node stack, not a production or HA deployment.
- No migration from legacy FreeIPA/Hive state. The supported project uses Keycloak, Polaris, RustFS, and Spark for the bootstrap journey.

## Ordered operator steps

From the project root:

```sh
cp .env.example .env
./scripts/lakehouse.sh start
./scripts/lakehouse.sh status
scripts/bootstrap-default-product.sh
./scripts/lakehouse.sh status
```

The bootstrap creates missing runtime credentials without printing or replacing existing files, starts the core providers, provisions the Keycloak realm/groups and owner identity, creates the approved buckets/catalogs/namespaces and grants, reconciles membership, verifies writer auth, and runs the Spark smoke-table check. It preserves existing bucket contents and is safe to rerun.

Stop services while preserving named volumes and RustFS objects:

```sh
./scripts/lakehouse.sh stop
```

Do not use `docker compose down -v` unless intentionally deleting the provider and object-store state. Back up `.runtime/credentials/` separately using encrypted storage.

## Verified evidence

- U1 core services start healthy; service ports bind to loopback; normal stop/start preserves provider state.
- U2 writer authentication, role resolution, wrong issuer, invalid signature, wrong audience, expired token, and Keycloak outage/reconciliation behavior were exercised. During an IdP outage, new token issuance and group reconciliation fail; already-issued unexpired tokens remain usable at Polaris until expiration.
- U3 bucket verification and scoped RustFS STS checks passed.
- U4 end-to-end bootstrap, smoke-table create/write/read in prod/dev/UAT, scoped credential vending, safe rerun, and four-role positive/negative access matrix passed.
- Test reports: `construction/unit-1/build-test-report.md`, `construction/unit-2/build-test-report.md`, `construction/unit-3/build-test-report.md`, and `construction/unit-4/build-test-report.md`.

## Open items and operating limits

- Human PKCE browser flow is not verified. Supply the actual owner username and application callback URI before enabling it; the current `lakehouse-cli` client has no callback URI.
- Duplicate/missing-user, unsupported-group, and incomplete-Polaris-update reconciler diagnostics have not all been tested.
- The reconciler uses the protected local Keycloak bootstrap administrator. Replace it with a least-privilege identity before any shared deployment.
- `polaris.realm-context.require-header=false` is approved only while `lakehouse` is the sole configured realm. Restore strict realm-header enforcement or fix/upgrade Iceberg header propagation before adding realms.
- Airflow, JupyterHub, Jenkins, and StarRocks integrations are deferred and unsupported by this handoff.
- The configuration has only been verified on the local `linux/arm64` Docker engine. No production TLS, HA, backup restore drill, or multi-host test is included.

## Pull request draft

**Title:** Bootstrap the default lakehouse product with Keycloak and Polaris

**Summary:** Replace the active FreeIPA/Hive bootstrap path with a local Keycloak + Polaris + RustFS setup. Add idempotent bootstrap for the three environment buckets/catalogs/namespaces, four role groups and grants, and Spark smoke tables. Keep runtime secrets protected and preserve existing object data on reruns.

**Verification:** U1–U4 reports document Compose health, identity and token checks, RustFS scoped STS behavior, end-to-end Spark table operations, role matrix, and safe rerun. U2 remains partially verified; see open items above.

No pull request was opened; this repository copy has no Git metadata available in the workspace.

## Final closure gate

The user accepted closure with the Unit 2 verification gaps recorded above. The waiver is not a production pass or deployment authorization.
