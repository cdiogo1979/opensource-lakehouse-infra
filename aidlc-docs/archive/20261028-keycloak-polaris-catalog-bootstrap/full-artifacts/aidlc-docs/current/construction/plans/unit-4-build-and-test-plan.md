# Unit 4 Build and Test Plan — Default Product Bootstrap

## Scope

Create and verify the approved three catalogs/namespaces, role grants, Keycloak owner identity, and Spark smoke tables without removing buckets or existing objects.

## Checks

- [x] Compile U4 Python helpers and validate Compose configuration.
- [x] Provision the protected initial `platform-admin` identity and owner group membership.
- [x] Verify the three approved RustFS buckets without changing their contents.
- [x] Create or verify the three Polaris catalogs with exact bucket/prefix mappings.
- [x] Create or verify the three requested namespaces.
- [x] Create and verify the four Polaris product principal roles and catalog grants.
- [x] Reconcile the current Keycloak groups into Polaris principals.
- [x] Obtain a Keycloak writer token and verify the Polaris principal/role resolution.
- [x] Create, write, and read `bootstrap_smoke_test` in all three environments through Spark.
- [x] Verify the positive/negative read/write access matrix for developer, analyst, owner, and writer across prod, dev, and UAT with temporary identities.
- [x] Verify a clean rerun after all tables exist.

## Result

**U4 bootstrap and Spark checks passed, including the four-role access matrix.** The three buckets, catalogs, namespaces, grants, owner identity, and Keycloak group reconciliation were verified. The user explicitly approved setting `polaris.realm-context.require-header=false` for this single configured `lakehouse` realm because Iceberg 1.8.1 omits `Polaris-Realm` during vended-credential refresh. Spark created, wrote, and read `bootstrap_smoke_test` in prod, dev, and UAT, verifying scoped locations and vended RustFS credentials. Temporary Keycloak service identities carried the expected role claims, reconciled to the expected Polaris roles, and passed allowed/denied Spark read/write checks across all environments. The harness removed the temporary clients, Polaris principals, and uniquely tagged probe rows; readback confirmed the original single row in each smoke table. The documented end-to-end bootstrap rerun and final smoke-table verification also passed. Bucket contents were preserved. Invalid-signature token rejection passed. This configuration treats the one configured realm as the default; restore strict enforcement or fix/upgrade the client before adding another realm.

## Configuration decision

Resolved by user approval: make the configured single `lakehouse` realm the default with `polaris.realm-context.require-header=false`. Revisit before adding another Polaris realm; prefer strict realm-header enforcement with a client/runtime fix that preserves `header.*` during vended-credential refresh.
