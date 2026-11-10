# Unit 4 Build and Test Report — Default Product Bootstrap

**Status: Bootstrap, Spark verification, and four-role access matrix passed.**

## Verified

- `scripts/bootstrap-default-product.sh` completed successfully end to end and passed on a second run.
- Keycloak contains the platform owner identity and the four product groups; Polaris reconciliation completed.
- The three RustFS buckets were verified without deleting or replacing their contents.
- Polaris catalogs, namespaces, and product role/grant configuration were created or verified for production, dev, and UAT.
- Writer OIDC authentication and role resolution passed. An authenticated writer's privileged management operation was denied with HTTP 403; an invalid-signature token was rejected with HTTP 401.
- Spark created, wrote, read, and validated `bootstrap_smoke_test` in all three namespaces. Each table had the expected single row and an environment-scoped location. RustFS vended-credential access passed.
- The second full bootstrap run verified the existing tables without duplicate rows.
- Temporary Keycloak service identities carried each expected group role and reconciled to the corresponding Polaris principal role.
- Live Spark read/write checks passed for developer, analyst, owner, and writer across all three environments, including expected denials.
- The harness removed all temporary Keycloak clients, Polaris principals, and uniquely tagged probe rows; it verified each smoke table returned to its original single row.
- A final `scripts/run-bootstrap-smoke-spark.sh` run passed after cleanup.

## Approved single-realm behavior

The Spark 3.5.5 / Iceberg 1.8.1 vended-credential refresh path omits the custom `Polaris-Realm` header. The user approved `polaris.realm-context.require-header=false` for the one configured `lakehouse` realm. This setting makes that realm the default. Restore strict header enforcement or use a client/runtime fix before adding another realm.

## Remaining checks

- U2 human PKCE callback, token audience/expiry, and outage behavior remain partially verified.

No pre-existing bucket objects or original smoke rows were deleted. Credential values and tokens were not included in output or this report. These local checks do not establish production readiness.

The role probes inserted and then deleted unique rows through Iceberg. The current table snapshots contain only the original smoke rows. No bucket-level object cleanup or snapshot expiration was run, so files retained by Iceberg's historical snapshots may remain until the configured retention/maintenance process removes them.
