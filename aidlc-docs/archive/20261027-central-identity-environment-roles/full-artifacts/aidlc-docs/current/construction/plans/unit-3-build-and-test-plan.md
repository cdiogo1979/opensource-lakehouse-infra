# Unit 3 Build and Test Plan — Hive Metastore and Direct Spark Authorization

## Purpose and Gate

Verify explicit environment locations and direct Spark object authorization using the pinned Hive 3.1.3, Spark 3.5.5, Iceberg 1.8.1, and RustFS 1.0.0 stack. The user accepts cross-environment metadata visibility. The hard security assertion is that Spark reads/writes use the caller's own RustFS identity and RustFS denies data access outside that role's bucket scope.

**Boundary:** HMS metadata confidentiality and metadata DDL authorization are not established by this plan. Do not claim analyst DDL is denied. If analyst metadata mutation must be prevented, stop and request a separate architecture decision. Do not add an authorizer/gateway, switch identity authority, or proceed to cutover under this plan.

This plan requires review and approval before running tests or changing runtime state. Code Generation did not run tests. No production database, object, identity, credential, or policy is a test fixture.

## Preconditions and Safety

- Confirm which Compose services are already running and their pinned image versions using read-only inspection. Do not restart or recreate services as part of preflight.
- Confirm the active KDC remains MIT and FreeIPA remains isolated. Do not alter KDC aliases, principals, groups, keytabs, or authority routing.
- Confirm the exact Kerberos principal and RustFS identity pairing for `developer-user`, `analyst-user`, `write-service-account`, and `admin`. Do not substitute `user_a`/`user_b` or the HMS service identity and call them the new roles. The user's explicit 2026-10-27 direction authorizes additive creation of the missing developer/analyst test principals in the active MIT KDC and matching named RustFS identities with the already-approved role policies. Do not change existing identities, rotate any existing credentials, or cut over authority.
- Confirm RustFS policy readback already reflects the Unit 2 approved developer/analyst/writer matrix. Do not reconcile or edit live IAM policies here. If the policy does not match, stop and return to Unit 2 or request a separately approved isolated endpoint.
- Generate a unique run ID and use only newly created disposable metadata names and object prefixes clearly marked for this test. Database names must be unique because all environments share one HMS namespace.
- Capture read-only before/after metadata and bucket/object inventory sufficient to prove that production locations and objects did not change. Do not read object contents or use production objects as probes.
- Do not remove all lakehouse data. The optional cleanup offer is not needed; the approved design preserves production. Cleanup may target only resources created by this test run after their exact names and prefixes are verified.
- Keep credentials in existing protected per-identity files and private ticket caches. No secret values in Compose overrides, command arguments, logs, or test output.
- At plan approval, the ETL helper's new namespace-location syntax and catalog readback had not yet been executed. They were subsequently verified as recorded in Steps 2–4 below.

## Test Matrix and Execution Sequence

### Step 1 — Preflight and no-mutation checks

- [x] Confirm role identity/credential pairs, expected RustFS policies, internal service reachability, pinned versions, and available disk/runtime capacity. The initially missing developer/analyst pairs were additively provisioned under the approved scope update.
- [x] Confirm the active production inventory and determine safe test-only database names, using unique run-ID namespaces.
- [x] Confirm no target namespace or probe prefix already exists. Every probe used a fresh unique identifier.
- [x] Save redacted before-state metadata/location and inventory evidence.

### Step 2 — Environment and location validation

- [x] Run the ETL's non-destructive configuration validation for missing/unknown environment and missing/duplicate/malformed database names; each must fail before Spark/HMS mutation. Helper-level checks passed for missing/unknown environment and missing/duplicate/malformed names.
- [x] On disposable databases only, verify new namespaces are created with exact roots: prod `s3a://lake/warehouse/<database>/`, dev `s3a://lake-dev/warehouse/<database>/`, and UAT `s3a://lake-uat/warehouse/<database>/`.
- [x] Read back HMS namespace locations. The three test namespaces matched their explicit bucket roots; the recognized existing production `.db` path remained unchanged in the metadata comparison.
- [x] Verify mismatched bucket, invalid scheme, external bucket/host, dot segments, cross-environment path, implicit/default location, prefix escape, and conflicting existing location fail closed. ETL helper probes rejected external-bucket and external-host database/table locations.
- [x] Verify existing table locations outside their database root fail before workload writes. Helper-level out-of-root rejection passed; the direct Spark probe tables were created under the selected database roots.
- [x] Verify environment-specific target names do not collide in the shared HMS. Unique names were created and cleaned; no existing database was renamed or moved.

### Step 3 — Identify enforcement layers

- [x] Confirm the configured Kerberos principal/keytab and RustFS key pair for each tested Spark role without exposing credentials. The probes exercised each principal with its matching RustFS identity.
- [x] Confirm the HMS request authenticates through the existing Kerberos-SASL endpoint. Role-specific Spark reads reached HMS; unauthorized data reads then failed at RustFS with 403.
- [x] Confirm direct RustFS object authorization with disposable prefixes and matching role credentials. Raw S3 probes isolated IAM allow/deny; Spark/Iceberg probes showed HMS metadata visibility followed by RustFS object denial.
- [x] Verify there is no fallback to writer, admin, or HMS service credentials when required identity files are missing or when invalid RustFS credentials are supplied. The missing-keytab launcher exited before Spark start; invalid S3 credentials returned 403 without a success marker. Expired-ticket behavior is recorded separately in Step 6.

### Step 4 — Metadata visibility characterization

- [x] Confirm database/table metadata may be visible across environments; this is accepted and is not a pass/fail authorization result.
- [x] Verify metadata visibility does not cause Spark to access or return table data without the caller's RustFS authorization.
- [x] Avoid analyst database/table/partition create, alter, or drop operations. The current HMS configuration does not guarantee these are denied.

### Step 5 — RustFS object allow/deny and combined Spark operations

- [x] Developer: read all three disposable environment prefixes; Spark append succeeds only under dev (RustFS raw object write/delete probes also passed).
- [x] Analyst: real Spark/Iceberg read from populated prod test data succeeded; reads from populated dev and UAT test data failed with RustFS 403. Spark writes to all three buckets failed with RustFS 403 (RustFS raw object write/delete probes also passed).
- [x] Writer: Spark read/append passed in all three test prefixes. Airflow ETL integration remains unverified.
- [x] Admin: existing admin mapping remained unchanged; read/write probes passed across all three disposable environment paths. No admin credential or policy was changed.
- [x] Verify table read, append, overwrite, and delete behavior on disposable data, including readback after allowed overwrite/delete. Analyst overwrites were denied in every bucket; developer overwrite/delete passed only in dev; writer overwrite/delete passed in all three buckets.
- [x] Verify multipart and all connector-required list/head actions independently on disposable data. The RustFS role matrix covered bucket/head, list, object head/get/put/delete, multipart initiate/list/parts/abort where permitted.
- [x] Verify an object denial fails the complete Spark query even when HMS returns the table metadata.

### Step 6 — Failure, revocation, and diagnostics

- [x] Confirm an expired Kerberos ticket fails closed. A one-minute TGT was followed by a six-minute wait; `klist` reported no valid cache and the subsequent HMS query failed with GSS “No valid credentials.” A separate query shortly after local expiry succeeded while `klist` reported the cache expired, so the exact expiry grace was not characterized and no TTL/SLA is claimed.
- [x] Exercise missing Kerberos ticket, invalid S3 credentials, HMS unavailable, RustFS unavailable, malformed/ambiguous locations, and denied authorization. Missing credentials and service outages failed closed; the unavailable-HMS and unavailable-RustFS probes ended promptly without fallback.
- [x] Measure policy revocation with a temporary RustFS-only identity scoped to a unique `lake-dev` prefix. A persistent S3 client was denied on its first read 0.006 seconds after policy detach. A long-lived Spark session using the platform's Iceberg `S3FileIO` read its probe before detach and received `AccessDenied` on its first read afterward. FreeIPA group-membership revocation and Hive catalog metadata caching were not separately tested.
- [x] Confirm finite request timeouts in the outage probes (HMS connection refusal in 7 seconds; RustFS connection refusal in 12 seconds) and no retry under another identity.
- [x] Review test output for credential/keytab/ticket values and object contents. Probe logs contain role/outcome/error evidence only; expected denials contain RustFS 403 details.
- [x] For the temporary revocation test, remove only its user and policy and clean its unique test object. RustFS returned success for both removals, and the test prefix is empty.

### Step 7 — Preservation, cleanup, and result

- [x] Capture read-only after-state inventory and compare production object inventory with before-state. Bucket counts and metadata hashes match exactly; the existing HMS snapshot was also unchanged by the Spark probe cleanup sequence.
- [x] Clean up only the run-ID-scoped disposable tables, namespaces created by this run, and object prefixes after confirming their exact names and locations. No production or unrelated resource was removed.
- [x] Save redacted evidence from the initial metadata visibility probe; see the execution record below. That observed visibility is accepted under the user's revised requirement.
- [x] If any production inventory changed unexpectedly, stop cleanup, preserve evidence, and report the exact mutation for recovery review. No difference was found.

## Acceptance Criteria

Unit 3 passes only if all environment-location checks pass, Spark uses the matching user's RustFS credentials without fallback, object read/write role matrix passes for real disposable Spark/Iceberg operations, failure behavior is fail-closed, and before/after production inventory is unchanged. Cross-environment metadata visibility is accepted. This plan does not claim that analyst HMS metadata mutations are denied; if that is required, Unit 3 cannot pass without a separately approved HMS authorization design. Missing role credential pairs are a blocked prerequisite and must not be worked around with legacy users or service identities.

## Scope Exclusions

- No production data or database deletion, relocation, or rewrite.
- No FreeIPA provisioning, existing role membership change, existing keytab or S3 key rotation, general RustFS reconciliation, or authority cutover. Only the specifically authorized additive `developer-user` and `analyst-user` identities and policies, the approved writer-policy expansion, and creation of missing `lake-dev`/`lake-uat` buckets are in scope.
- No new service, plugin, gateway, HiveServer2, package, image, version, port, or network exposure.
- No Jupyter user mapping or authentication changes (Unit 4), StarRocks/Ranger changes (Unit 5), or cutover (Unit 6).

## Execution Record — 2026-10-27

**Approval**: The user approved this Build and Test Plan and requested continuation.

**Read-only preflight**: Docker inspection found the pinned Spark 3.5.5/Iceberg 1.8.1, Hive Metastore 3.1.3, RustFS 1.0.0, and MIT KDC services running and healthy. Protected runtime credential filenames include `user_a.keytab`, `user_b.keytab`, `admin.keytab`, `write-service-account.keytab` and the corresponding legacy `user-a`, `user-b`, writer, and admin RustFS credentials. No `developer-user` or `analyst-user` Kerberos keytabs or matching runtime RustFS access/secret pairs are present. Unit 2 test-only developer/analyst RustFS secret files exist under `.runtime/identity-provisioning/test-credentials`, but they have no matching Kerberos credential pair for the active HMS test path and cannot satisfy this plan's identity-binding prerequisite. Secret contents were not read or recorded.

**Initial outcome**: `blocked-prerequisite`. Stopped at preflight as required. Did not substitute `user_a`/`user_b`, create databases or objects, run test workloads, or alter production data. The user subsequently authorized creation of the missing role users; the bounded scope update below records that instruction.

**Original current gate**: Reconcile the writer policy and run the disposable test sequence; the original metadata privacy requirement was later relaxed by the user as recorded below.

## Scope Update — 2026-10-27

**User Direction**: The user directed creation of missing users as needed. This explicitly supersedes the Build and Test Plan's no-identity-provisioning precondition for the two missing human roles only.

**Bounded Scope**: Create new `developer-user@LAKEHOUSE.LOCAL` and `analyst-user@LAKEHOUSE.LOCAL` principals/keytabs in the active MIT KDC, plus matching RustFS identities and exact approved `lakehouse-developers`/`lakehouse-analysts` policies. Create the already-approved `lake-dev` and `lake-uat` buckets only if absent; preserve all existing bucket objects. The previously approved role matrix also authorizes updating only the existing writer policy to cover all three buckets. Preserve all existing credentials and identities. No admin changes, role membership changes, FreeIPA changes, authority cutover, or production object/database mutation.

**Progress**: Both new MIT principals were created and their keytabs were issued to the ignored `.runtime/credentials/keytabs/` directory with mode `0600`; both successfully obtained and destroyed tickets against the active KDC. Runtime key files for the corresponding RustFS identities were generated under `.runtime/credentials/` with mode `0600`. RustFS accounts/policies were created and read back as exact. Disposable S3 role probes passed for developer and analyst across the three buckets and removed their temporary objects. The writer policy was updated to the approved three-bucket scope without credential change; writer write/readback probes then passed on all buckets and removed their temporary objects.

**Bucket Readiness Finding**: The active RustFS instance lacked `lake-dev` and `lake-uat`. The existing bucket initializer was extended and run; `lake` was confirmed present and preserved, and only the missing `lake-dev` and `lake-uat` buckets were created.

## Unit 3 Execution Update — Authorization Gate — 2026-10-27

**Identity Setup**: Created `developer-user@LAKEHOUSE.LOCAL` and `analyst-user@LAKEHOUSE.LOCAL` in the active MIT KDC, issued distinct mode-`0600` keytabs, and verified both could obtain and destroy tickets. Generated matching RustFS secret files and access-key ID files with mode `0600`. Created the two named RustFS identities and exact approved developer/analyst policies. No existing principal, keytab, or human-role membership was changed.

**Bucket and Writer Setup**: The existing RustFS bucket initializer was changed to ensure `lake`, `lake-dev`, and `lake-uat`; it preserved existing `lake` and created only missing `lake-dev`/`lake-uat`. The existing `lakehouse-writer` policy was updated to the approved all-three-bucket scope after a probe returned `403` for `lake-dev`. The writer identity and secret were not changed.

**Object Authorization Results**: Disposable RustFS probes passed developer read/list across all buckets, write/delete only in `lake-dev`, and analyst read/list only in `lake` with writes/deletes denied. A writer probe passed write/readback on all three buckets after policy update. Each probe used unique temporary objects and removed them. No existing object contents were read.

**Location/Metadata Setup**: A read-only Spark baseline recorded five existing namespaces and their locations/table names. Created only three unique test namespaces: `aidlc_u3_20261027_prod` at `s3a://lake/warehouse/aidlc_u3_20261027_prod`, `aidlc_u3_20261027_dev` at `s3a://lake-dev/warehouse/aidlc_u3_20261027_dev`, and `aidlc_u3_20261027_uat` at `s3a://lake-uat/warehouse/aidlc_u3_20261027_uat`. Writer readback matched all three locations. No tables or object data were created in these namespaces.

**Original metadata probe**: An isolated Spark client authenticated as `analyst-user` ran `SHOW NAMESPACES IN iceberg`; HMS returned dev, UAT, and other namespaces. Under the original design, this failed the metadata confidentiality gate. The user subsequently confirmed that cross-environment metadata visibility is acceptable provided unauthorized data queries fail.

**Preservation**: No existing database/table/partition location or object was changed. No admin or writer credential was rotated. Existing production namespace `default_lhuat` remains at its pre-existing `s3a://lake/warehouse/default_lhuat.db` location; it was observed only and not corrected.

**Runtime Artifact Note**: Three Docker volumes with the `opensource-lakehouse-infra_` prefix were created by Compose `run --no-deps` while resolving the Compose project. Read-only inspection found no containers attached to them; the actual service containers remained unchanged. They were not used for service data.

## Authorization Boundary Revision — 2026-10-27

**User Decision**: Cross-environment database/table visibility is acceptable. The required Jupyter/Spark outcome is that users can query only data their RustFS role permits. This supersedes the former requirement that out-of-scope HMS metadata be hidden.

**Reclassified result**: Analyst enumeration of dev/UAT metadata is accepted behavior, not an authorization failure. The observation and evidence are retained. Unit 3 acceptance now requires real Spark/Iceberg reads and writes to be enforced by per-user RustFS credentials: analyst can read production and is denied data reads from dev/UAT; developer reads all and writes only dev; writer reads/writes all. No human session may fall back to the writer identity.

**Known limitation**: This approach does not guarantee denial of Hive metadata DDL (create/alter/drop). Analyst DDL must not be used; if preventing metadata mutation is required, request a separate HMS authorization design. The three test namespaces remain empty and preserved. The principal Spark/Iceberg read/append matrix passed; at that checkpoint, supplementary Unit 3 checks remained open and are recorded below.

## Direct Spark/RustFS Verification — 2026-10-27

**Method**: Used the pinned Spark 3.5.5/Iceberg 1.8.1 image with the same `start-session.sh`, Kerberos configuration, Spark catalog settings, and per-role keytab/RustFS credential mounts used for notebook sessions. Ran isolated one-shot driver containers on the existing internal Compose network; no persistent service was restarted or reconfigured.

**Disposable setup**: The ETL writer created one uniquely named Iceberg table with a single probe row in each of the three existing empty Unit 3 test databases. The table paths were confined to each test database's approved bucket root. The role matrix was then exercised with actual Spark SQL reads and appends.

**Results**: Analyst read from prod succeeded; reads from dev/UAT and writes to all buckets returned RustFS 403. Developer reads across all environments succeeded; append succeeded in dev and was denied in prod/UAT. `write-service-account` read and append succeeded across all three environments. The expected denied Iceberg writes generated Spark/AWS stack traces containing S3 403 request IDs but no credentials or key material. This confirms Spark used each session's mounted RustFS identity; raw RustFS role probes had independently passed earlier.

**Cleanup**: The writer ran `DROP TABLE ... PURGE` for exactly the three test table names; a follow-up HMS table-existence check confirmed all were absent. The three empty test namespaces remain as evidence. No pre-existing production database/table/object was used or changed.

**Remaining Unit 3 verification after initial Spark matrix**: At that point, path validation, overwrite/delete semantics, admin behavior, no-fallback, outage, revocation/cache, and full inventory comparison remained open. Subsequent results are recorded below. JupyterHub's actual login/mapping for `developer-user` and `analyst-user` remains Unit 4; these tests validate the notebook runtime/auth path but not JupyterHub authentication or spawner mapping.

## Additional Unit 3 Verification — 2026-10-27

**Location/config helper checks**: Ran 24 read-only checks against the ETL validation helpers with PySpark schema stubs (no Spark session or service connection). Passed explicit prod/dev/UAT bucket selection; rejection of missing/unknown environment, empty/duplicate/malformed database names, non-S3A schemes, missing bucket, external bucket/host, dot segments, repeated separators, query/fragment suffixes, default/implicit database locations, and cross-environment existing database locations; acceptance of the known legacy production `.db` location; and table path containment, external-host/bucket, and prefix-escape checks. This is helper-level evidence; invalid-location cases were not exercised as live ETL writes.

**Spark overwrite/delete results**: Recreated only the three named disposable probe tables. Actual Spark/Iceberg `INSERT OVERWRITE` and `DELETE` with readback passed for developer in dev and `write-service-account` in prod/dev/UAT. Analyst overwrite attempts and developer overwrite attempts in prod/UAT failed with RustFS 403. The probe restored the original single test row after each allowed delete. Analyst delete and direct denied `DeleteObject` calls for developer in prod/UAT were not separately issued; wrong-scope writes were denied through Spark overwrite and raw `PutObject` checks. The later raw role matrix covers allowed per-bucket deletes, multipart, and list/head actions.

**Cleanup**: The writer purged exactly the three probe tables after the mutation checks; all three cleanup operations reported success. The three empty Unit 3 test namespaces remain. The expected authorization-denial probes emitted Spark/AWS 403 stack traces to the local test output; no credentials or key material appeared.

**Status at this checkpoint**: The required per-role direct Spark read/write matrix and tested append/overwrite/delete cases passed. The supplementary checks below close most remaining items; their recorded limits supersede the earlier open-item list. JupyterHub authentication and role-to-spawner mapping remain Unit 4.

## Final Supplementary Checks — 2026-10-27

**RustFS role matrix**: Re-ran disposable raw S3 operations for developer, analyst, writer, and admin credentials. Bucket/head, list, object head/get/put/delete, and multipart initiate/list-uploads/list-parts/abort checks matched each role's approved bucket scope. Admin reads and writes passed in all three buckets; no admin policy, credential, or membership was changed.

**Spark failure paths**: Missing keytab failed before Spark launched. A valid developer Kerberos session paired with intentionally invalid S3 credentials could enumerate metadata but received RustFS 403 for the data operation, with no success marker. The HMS outage probe failed in approximately 7 seconds and the RustFS outage probe in approximately 12 seconds; both were connection refusals and neither fell back to another identity. The location helper also rejected implicit/default, cross-bucket, external-bucket, malformed, and prefix-escape database/table locations. A denied object read failed the complete Spark query.

**Policy revocation**: With user authorization, created unique temporary RustFS users and policies scoped to fresh `lake-dev` prefixes. A persistent S3 client could write/read before revocation and received `AccessDenied` on its first read 0.006 seconds after detach. In a separate long-lived Spark process, the platform's Iceberg `S3FileIO` wrote/read a probe object before detach and received `AccessDenied` on its first post-detach read. This verifies policy enforcement through Spark's persistent object client; the test did not involve Hive catalog metadata caching. Temporary users and policies were removed; their exact object prefixes were deleted with the root identity and verified empty. No existing account, membership, or policy was modified.

**Inventory and data scope**: A final read-only S3 inventory matched the before-test inventory exactly: `lake` 23 objects, `lake-dev` 1, and `lake-uat` 1, with identical per-bucket metadata hashes. Thus, although the user reported clearing bucket contents, the observed buckets were not empty at the time of this check; this test neither read object contents nor changed any pre-existing object. Synthetic table data and run-scoped object prefixes were removed. The metadata inventory from the cleanup sequence matched its before snapshot (26 records); the three empty namespaces created by the earlier Unit 3 run remain as evidence. This test did not use old table data as fixtures.

**Ticket expiry test method**: The captured-output test used a one-minute developer TGT followed by a six-minute wait. A separate attempt to collect an additional metadata-only snapshot via `spark-submit` failed with a GSS “No valid credentials” error and wrote no snapshot; it did not mutate HMS. Existing before/after inventory evidence remains the basis for the metadata preservation result.

**Ticket expiry result**: The one-minute TGT was acquired; after six minutes, `klist` reported the cache expired. `SHOW NAMESPACES IN iceberg` then exited 1 with `GSS initiate failed / No valid credentials provided`. No data query succeeded and no identity fallback occurred.

**Unit 3 result — pass with documented scope limits**: The approved acceptance checks passed, including the role matrix, fail-closed behavior, direct Spark object access, scoped policy revocation through Spark's persistent Iceberg object client, and unchanged before/after object inventory. This does not prove analyst Hive metadata DDL is denied, FreeIPA group-membership revocation timing, Hive catalog metadata-cache behavior, or an SLA. Airflow ETL integration remains unverified; JupyterHub login and spawner mapping are Unit 4 scope. The test used only synthetic table rows and run-scoped object prefixes; old table data was not used as a fixture.
