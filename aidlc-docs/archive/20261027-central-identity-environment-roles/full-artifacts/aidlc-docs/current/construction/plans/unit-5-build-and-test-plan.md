# Unit 5 Build and Test Plan — StarRocks Native LDAP Roles

## Current direction (2026-10-28)

The user has superseded the Ranger architecture with StarRocks native roles and grants mapped to FreeIPA LDAP groups. No Ranger Admin, UserSync, policy database, or Ranger service is required for the current target. The existing Ranger-related progress below is retained as history only; it is not a current dependency or acceptance gate.

Implementation includes `infra/starrocks/ldap-access/bootstrap_roles.py`, `scripts/bootstrap-starrocks-ldap-roles.sh`, a disposable FE/BE Compose file, and test-only TLS/admin setup. The isolated test FE must publish no host ports; bootstrap and verification clients run through `docker exec`. Do not point the script at `iceberg-poc-starrocks-fe` or reuse its secrets/volumes.

### Current verification checklist

- [x] Start the dedicated disposable StarRocks 4.1.6 FE/BE and configure LDAP direct-bind authentication with the isolated FreeIPA CA; use only the isolated FreeIPA network and test-specific volumes, with no host ports or production KDC, HMS, RustFS, catalog, credentials, or volumes.
- [x] Prepare test-only mode-0600 StarRocks TLS keystore, admin option, user client options, and FreeIPA group-reader secret files in their required isolated directories.
- [x] Validate LDAP group results and LDAP DN matching for each synthetic account.
- [x] Use synthetic source databases `test_prod`, `test_dev`, and `test_uat` in the isolated FE's internal `default_catalog`; create internal MV output databases `default_lh`, `default_lhdev`, and `default_lhuat`. No external Hive catalog is configured in this FE, and no production data was used.
- [x] Create internal `default_catalog` output databases and apply the environment-scoped MV grants: writer create/alter/refresh/drop/select in all three, developer select in all three, analyst select in production only. Do not grant general database/table DDL.
- [x] Apply the bootstrap after the Docker target guard passes; read back provider/users/roles/grants and verify effective group mappings through LDAP logins.
- [x] Verify developer SELECT all and INSERT dev only; analyst SELECT prod only; writer SELECT/INSERT all. Both an unregistered username and a registered LDAP user with no mapped group were denied source data. The writer direct-role exception means removing its group does not remove its role.
- [x] Authenticate `write-service-account` over TLS. Create/drop and forced refresh of synthetic MVs passed in each output database. Developer/analyst MV read scopes and denied writes were tested earlier. The writer was denied `CREATE TABLE`, `CREATE VIEW`, `CREATE DATABASE`, `ALTER DATABASE`, `CREATE EXTERNAL CATALOG`, `CREATE ROLE`, `CREATE USER`, and role grants.
- [x] Verify writer account-disable behavior: new LDAP login was denied while an already-authenticated StarRocks session remained query-capable. Re-enabling restored new login. Full immediate revocation therefore also requires closing existing StarRocks sessions. Developer and analyst group-removal cache behavior was also verified after the 60-second cache interval; fresh sessions lost their mapped role and data access, then access returned after membership restoration and bootstrap reconciliation.
- [x] Inspect isolated container/network/volume metadata; FE/BE have no published ports and production services/data were not changed.
- [x] Test direct Spark/RustFS authorization separately; Unit 3's 2026-10-27 Build and Test evidence covers the same three principals, bucket matrix, direct S3 denials, and Spark/Iceberg reads/writes. Do not use the retained probe launcher for a repeat: it attaches to `iceberg-poc-net` and the production HMS/object-store aliases.
- [x] Validate access through an isolated Hive external catalog. Spark created synthetic Iceberg tables in a separate test HMS/RustFS stack; all 15 StarRocks external-catalog read/write authorization cases passed. No production Hive or RustFS service was connected.

The role groups must be mutually exclusive because StarRocks combines mapped roles. The bootstrap grants SELECT/INSERT on Iceberg source tables plus narrowly scoped materialized-view management in internal environment databases. It intentionally excludes general DDL/security privileges and does not revoke unrelated grants. The writer's LDAP password must be provisioned separately from the Spark Kerberos keytab, stored as a protected credential, and used only over TLS. A separate reviewed production migration is required after test acceptance.

## Historical Ranger test plan — superseded

The material below records the previous approved Ranger test direction and evidence. It must not be treated as current work to resume.

## Scope and authorization

The user requested Build and Test for the approved isolated Unit 5 stack. Build and run only the dedicated `ranger-test-*` Compose project/profile. Preserve the default Compose project and every existing service, named volume, credential, identity, policy, bucket, object, and table. Use only synthetic users, role groups, catalog namespaces, SQL rows, and object prefixes.

Do not connect to production FreeIPA, active MIT KDC, production RustFS, current Hive Metastore, JupyterHub, Airflow, or existing StarRocks FE/BE. Do not publish non-loopback ports.

## Preflight and build

- [ ] Verify the default project’s containers, networks, and volumes by metadata only; capture a baseline inventory.
- [ ] Verify the test project/service/network/secret/volume names do not collide and have no production attachments.
- [ ] Verify all test secrets exist, are protected, are not tracked, and are not printed; verify no default Ranger password will be accepted.
- [ ] Verify source signatures/checksums and image digests; record exact Ranger, UserSync, PostgreSQL, FreeIPA, StarRocks, HMS, RustFS, and test-KDC build versions.
- [ ] Build images and start only the explicit isolated test project. Prove each service’s network attachments and volume mounts from Docker metadata. Ranger Admin/DB are healthy, and Ranger UserSync/FreeIPA images build. FreeIPA runtime initialization exited 123 and remains stopped; no UserSync or downstream service was started.
- [ ] Confirm FreeIPA LDAP/TLS readiness, read-only UserSync bind, role-group synchronization, Ranger Admin health, isolated PostgreSQL health, and sanitized audit path.
- [ ] Confirm StarRocks FE/BE readiness and exact Ranger/Hive client libraries/configs. Stop if the FE lacks documented Hive Ranger integration or a required plugin is not compatible with 4.1.6.

## Authorization matrix

Create only synthetic test identities and data. Apply test policies equivalent to the approved role intent:

| Identity/group | Production synthetic namespace | UAT synthetic namespace | Development synthetic namespace | Writes |
|---|---|---|---|---|
| `analyst-user` / `lakehouse-analysts` | SELECT allowed | SELECT denied | SELECT denied | Denied everywhere |
| `developer-user` / `lakehouse-developers` | SELECT allowed | SELECT allowed | SELECT allowed | DML only in development |
| synthetic writer / `lakehouse-writers` | SELECT and approved DML | SELECT and approved DML | SELECT and approved DML | DDL denied |
| synthetic administrator | Approved administrative operations | Approved administrative operations | Approved administrative operations | As configured for test administration |
| unknown/unmapped user | Denied | Denied | Denied | Denied |

The synthetic test writer is not `write-service-account` and uses no production service credentials. Validate direct Hive catalog queries through StarRocks FE; do not treat direct Spark-to-RustFS as a Ranger test.

- [ ] Prove the actual external Hive catalog is configured for its Ranger Hive service and log the effective requester/resource/action.
- [ ] Test database/table/view SELECT and minimum approved DML actions; include negative policy boundaries and SQL DDL denial.
- [ ] Verify policy changes are not bypassed by native StarRocks grants, cached user/group state, or alternate service identities.
- [ ] Verify unknown user/group/resource/action and conflicting role membership fail closed.
- [ ] Confirm allow/deny audits have principal, service/policy, resource/action, timestamp, result, bounded reason and no credentials or sensitive row data.

## Failure, consistency, and recovery checks

- [ ] Test Ranger Admin unavailable before a new uncached decision and with a warmed cache; record actual FE behavior and do not infer fail-closed cache semantics.
- [ ] Test FreeIPA unavailable, bad CA/hostname, UserSync failure, and unknown identity; all new access must deny.
- [ ] Measure FreeIPA group removal through UserSync and policy refresh for fresh authentication, a new query in an existing session, cached resources, uncached resources, and after FE restart.
- [ ] Record observed revocation latency without asserting an SLA.
- [ ] Export Ranger service definitions/policies and back up the isolated policy DB, restore into a second isolated target, and compare policy/readback.
- [ ] Capture after-test default-project inventory and compare it to baseline; any unexpected change is a failure and cleanup stops.

## Cleanup and acceptance

- [ ] Remove only test-prefixed containers and synthetic records after recording evidence.
- [ ] Keep or remove named test volumes only through an explicit test-project cleanup command that revalidates the exact project and volume prefix.
- [ ] Verify no test container remains and existing default containers, networks, volumes, policies, buckets, and object inventories remain unchanged.
- [ ] Record exact results, observed compatibility limitations, source digests, and any verification waiver; no assumption of success from container health alone.

## Stop conditions

Stop without touching any live service or data if: an image/service has ambiguous identity; the project could attach to a protected network or volume; secret files are missing/unprotected; version compatibility is unsupported; StarRocks external Hive authorization cannot be established; an unknown decision is allowed; native grants bypass Ranger; test data cannot be proven synthetic; or cleanup inventory differs unexpectedly.

This plan is approved by the user's explicit request to continue through Build and Test on 2026-10-27. It authorizes isolated test operation only, not production policies, production FreeIPA, service identity rotation, user migration, or KDC transition.

## Unit 5 current status addendum — 2026-10-28

This addendum supersedes the earlier progress statements above where they say the isolated FreeIPA service is still stopped/unhealthy or UserSync has not started. Those statements describe earlier checkpoints.

**FreeIPA and identities**: The isolated FreeIPA test service is now healthy. Synthetic `developer-user`, `analyst-user`, `write-service-account`, the UserSync bind identity, and scoped groups were bootstrapped idempotently. A direct LDAP simple bind using the test identity succeeds with OpenLDAP. No production identity or FreeIPA service was touched.

**UserSync**: Ranger Admin and the UserSync JVM are running on the isolated test networks. The test health check confirms only that the JVM process exists; it is not evidence of successful synchronization. Ranger Admin authentication succeeded and returned the test directory inventory, but LDAP synchronization fails: Java/JNDI receives LDAP result code 49 for the bind and UserSync reports zero users and zero groups. The equivalent OpenLDAP bind succeeds, and a direct FreeIPA query using the configured group filter returns the three expected groups. The Java/JNDI authentication discrepancy remains unresolved; do not mark UserSync or Ranger identity synchronization as passed.

**Focused configuration check**: Sanitized inspection of generated UserSync XML confirms the expected test LDAP URL, bind DN, and search bases. The bind secret is kept in Ranger's JCEKS credential store; a separate in-memory comparison confirmed the stored test credential matches the mounted test secret, without displaying either value. A direct Java/JNDI simple-bind check still returns LDAP result 49. This narrows the issue to the Java/Ranger bind path; it does not establish whether the cause is JNDI behavior, Ranger credential resolution, or a Java-side directory compatibility issue.

**Passed checks**: Static Bash syntax and isolated Compose profile validation passed after the test-only UserSync entrypoint and health-check changes. Ranger Admin and its PostgreSQL remain healthy. No secret values were logged or added to this record.

**Still open**: Resolve Java/JNDI-to-FreeIPA bind behavior and prove UserSync readback before proceeding to synthetic Hive Metastore/RustFS/KDC, disposable StarRocks runtime, Ranger Hive service/policies, positive and negative authorization matrix, failure/cache/revocation/audit, backup/restore, and protected-resource inventory checks. The Unit 5 Build and Test stage remains incomplete. Production services, identities, policies, buckets, databases, and data remain unchanged.

## Build and Test progress — 2026-10-27

**Completed so far**: `bash -n` passed for the Ranger DB/Admin entrypoints and secret-preparation script; Python compilation passed for the isolated Python 3.14 compatibility patch; isolated Compose profile validation passed. Built both local Ranger 2.9.0 Admin and DB images from pinned official multi-architecture image digests. The Ranger test DB reports healthy, accepts local PostgreSQL connections, and has the 78 Ranger schema tables expected after initialization. Ranger Admin's local `/login.jsp` returned HTTP 200 and its health check is healthy.

**Isolation evidence**: Docker metadata shows the Admin container is attached only to `ranger-test-control-net` and `ranger-test-db-net`, and the DB only to `ranger-test-db-net`. Both have only their dedicated `ranger-test-*` data/log volumes and file-backed test secrets. Neither service publishes a host port. The default `docker-compose.yml` was not edited. Container/network/volume inventory snapshots are saved under `construction/unit-5/build-test/`; no previous container, network, or volume was removed. Beyond Docker resource metadata, production identity, storage-object, catalog, and policy inventories were not read or compared because no test connected to those services.

**Additional image and FreeIPA result**: The UserSync image built from the official Apache Ranger 2.9.0 artifact after checksum verification. The isolated FreeIPA image built. Its test-only container exited during first-time setup with status 123 and was stopped; the reason has not been diagnosed. A proposed diagnostic action to copy its full `/data` and `/var/log` trees was automatically rejected because those trees could contain credentials, keytabs, and directory state. No workaround was attempted. The test volume remains preserved for later in-container, narrowly scoped diagnosis. The pinned FreeIPA image declares `/run` and `/tmp` anonymous volumes; two launch attempts created four test-attempt volumes. Two are attached to the stopped test container and two are unreferenced. The current Compose definition explicitly names future `/run` and `/tmp` mounts with `ranger-test-*` names. No volume was removed.

**Not complete**: FreeIPA did not become healthy. No UserSync group sync, LDAP TLS failure case, Ranger policy service, StarRocks FE/BE, Hive catalog query, allow/deny role matrix, outage/cache/revocation, audit policy test, or backup/restore test has run. Ranger Admin/DB health and image builds do not establish StarRocks 4.1.6 authorization compatibility. Unit 5 Build and Test remains open; do not treat this progress record as acceptance or a waiver.

**2026-10-28 follow-up**: Stopped FreeIPA container metadata confirms exit code 123 and the prior `ranger-test-directory-net` attachment. The test Compose file now matches the architecture's `ranger-test-ipa-net`; Compose validation and shell syntax checks pass. No container recreation, restart, volume removal, or network removal occurred. The installer log has not been read pending approval for a narrowly scoped sanitized inspection. FreeIPA readiness remains the dependency gate for UserSync and authorization testing.

**Additional isolated build/diagnostic evidence**: Disposable StarRocks 4.1.6 FE/BE local images built successfully from the approved pinned base digests. A no-network read-only filename check found Ranger 2.9.0 API/audit/common/classloader artifacts in FE, but did not establish external Hive catalog authorization support; no test FE/BE services were started or given credentials/state. The original IPA failure was diagnosed with the user's approval as unsupported `--no-dns` in the test-generated options. That was removed. After choosing a non-overlapping 172.29.252.0/24 test subnet, retry still exits with code 123 during initialization. The isolated container was stopped; a new 132-byte installer log remains unread pending separate approval.

## Native StarRocks LDAP role test update — 2026-10-28

This section supersedes the preceding statements that say a disposable StarRocks FE/BE has not been started. Those statements record earlier Ranger-path checkpoints.

**Built and running**: Disposable StarRocks 4.1.6 FE and BE are healthy on the internal `ranger-test-ipa-net`. Neither publishes host ports. FE/BE state is held only in named `starrocks-ldap-test-*` volumes. The isolated FreeIPA test container is healthy and on that network. The old Ranger Admin, DB, and UserSync containers are not needed by this native-RBAC path and remain removed. The metadata-only before/after comparison shows only the two test FE/BE containers and their two named volumes added; no network changes. Live StarRocks, Hive Metastore, object-store, KDC, Airflow, and JupyterHub were not changed.

**Applied and read back**: TLS admin login to the disposable FE succeeded. The FreeIPA LDAP group provider is configured over LDAPS with CA validation; provider readback masks its bind password. The bootstrap applied the three native roles, environment-scoped table/view grants, materialized-view grants, and external-group grant statements with no SQL error. Root readback confirms: developers read all three source test databases, insert only into development, and read MVs in all three output DBs; analysts read only production source/MVs; writers read/insert in all three sources and manage MVs in all three output DBs. The three internal output databases are `default_lh`, `default_lhdev`, and `default_lhuat`. This is grant-definition evidence only, not proof an authenticated LDAP principal receives the intended role.

**Login blocker**: OpenLDAP simple bind with a synthetic developer credential succeeds. A StarRocks login attempt using the documented MySQL cleartext authentication plugin and CA-verifying TLS still fails with LDAP result code 49. Therefore no LDAP user has successfully logged in through StarRocks and external-group resolution, effective roles, positive/negative authorization, writer MV operations, unknown/no-group rejection, or cache/revocation behavior remain unverified. The documented StarRocks `SHOW GRANTS` syntax queries users and roles but does not provide a target for an external group; accepted group grant statements consequently have no separate runtime readback yet.

**Static checks passed**: Bash syntax passed for the test entrypoints and bootstrap launcher; Python compilation passed for the bootstrap and test admin initializer; isolated StarRocks test Compose config validation passed. The generated runtime credential directory is protected and values were not displayed or written into this plan.

**Still open**: Resolve Java/JNDI-to-FreeIPA authentication, then run the complete LDAP login and authorization matrix, including actual external group role application, materialized-view write operations, and cache/revocation. Do not apply this bootstrap to production. Unit 5 Build and Test remains incomplete; the test FE/BE and FreeIPA are intentionally left running for the next diagnosis.

## 2026-10-28 native LDAP test continuation

This update supersedes the preceding native-path login blocker. Earlier Ranger checkpoints remain historical and are not current work.

**Resolved test setup issues**:
- FreeIPA test account passwords had been set from newline-terminated secret files with `ldappasswd -T`; StarRocks configured and client passwords omitted the newline. The isolated FreeIPA bootstrap now strips CR/LF into private temporary files before setting those test account passwords.
- Native LDAP users did not resolve groups until StarRocks' cluster-wide `group_provider` config was set to `lakehouse_freeipa_groups`. The guarded bootstrap now sets this parameter after creating the provider.
- The production FE entrypoint now persists `group_provider = lakehouse_freeipa_groups` in `fe.conf`, and the disposable FE entrypoint mirrors this setting so a container restart does not clear the native group-provider selection.

**Passed runtime checks**:
- TLS admin login and all three synthetic LDAP logins succeeded with CA-verified LDAPS. Each login received the expected group-derived StarRocks role.
- Source-table authorization matrix passed against `default_catalog.test_prod`, `.test_dev`, and `.test_uat`: developer SELECT all / INSERT dev only; analyst SELECT prod only / writes denied; writer SELECT and INSERT all three.
- Materialized-view SELECT matrix passed: developer all three; analyst production only; writer all three. Writer create, alter, and drop passed in each of `default_lh`, `default_lhdev`, and `default_lhuat`. Developer and analyst refresh attempts were denied.
- Removing `write-service-account` from the isolated FreeIPA writer group and waiting for the configured 60-second provider cache led a fresh StarRocks session to `CURRENT_GROUP() = NONE`, `CURRENT_ROLE() = NONE`, and denied source reads. Re-adding the membership restored the expected writer role and read access after cache refresh.
- Container/network/volume metadata show only the isolated test FE/BE state added; live lakehouse services and data were not changed.

**Unresolved materialized-view refresh limitation**:
- A deferred MV refresh fails with `Current role(s): NONE` while the authenticated writer has the LDAP-derived `lakehouse_writer` role and can run SELECT directly. StarRocks' asynchronous refresh worker does not use the role-derived source SELECT grant.
- A temporary direct `GRANT lakehouse_writer TO USER 'write-service-account'@'%'` made deferred refresh succeed, but that direct role survived FreeIPA group removal and allowed source reads after cache expiry. The temporary grant was revoked, the test user's default role reset to NONE, and group-only access was restored. No direct role or user-level source grant was added to the bootstrap.
- `DEFAULT ROLE ALL` alone did not make a forced refresh work; a previously reported successful no-op refresh had skipped source reads. Do not treat it as a workaround.

**Remaining before acceptance**: Choose a revocation-safe design for writer-owned asynchronous MV refresh, test unknown/no-group registration and active-session revocation, verify negative DDL/security operations, and validate against the actual Hive external catalog. The bootstrap remains guarded to the disposable FE and must not be used in production until those gaps and the refresh limitation are resolved.

## 2026-10-28 approved writer service-account exception

This addendum supersedes the preceding statement that the writer-refresh design remains undecided. The user approved a direct StarRocks role exception for `write-service-account` after runtime testing showed asynchronous MV refresh does not inherit LDAP group-derived roles.

- The guarded bootstrap now grants `lakehouse_writer` directly to `write-service-account` and sets `DEFAULT ROLE ALL`. Its FreeIPA `lakehouse-writers` mapping remains in place. No direct role is granted to developer or analyst identities.
- This direct role survives FreeIPA group removal. Group removal is therefore not a valid revocation procedure for this service identity. Disable the FreeIPA account to block LDAP authentication; for permanent retirement, also revoke the direct StarRocks role and reset its default role.
- Re-applied the guarded bootstrap to the disposable FE. TLS login readback showed `CURRENT_GROUP() = lakehouse-writers` and `CURRENT_ROLE() = lakehouse_writer`; `SHOW GRANTS` confirmed the direct role.
- Created a synthetic deferred MV and ran `REFRESH MATERIALIZED VIEW ... FORCE WITH SYNC MODE` in `default_lh`, `default_lhdev`, and `default_lhuat`. All three completed, and each MV returned one materialized row. The three probe MVs were dropped afterward.
- Temporarily disabled the synthetic FreeIPA `write-service-account`; its StarRocks LDAP login failed. Re-enabling the account restored login and the writer group/role. The test was run with automatic re-enable on exit. This confirms FreeIPA account disable, rather than group removal, is the account-level authentication revocation control; it does not revoke the direct role while the account is enabled.
- An unregistered/unmapped username was denied. The writer was denied `CREATE TABLE` and `GRANT ... TO USER` operations. During a live SQL session, disabling the FreeIPA account blocked a new login but the existing session remained query-capable; after re-enable, new login worked. Disable therefore revokes future authentication, not already-open StarRocks sessions.
- A temporary LDAP user without any FreeIPA role-group membership authenticated as `CURRENT_GROUP() = NONE` and `CURRENT_ROLE() = NONE`; a source-table SELECT was denied. The temporary FreeIPA and StarRocks user records and protected client option file were removed after the check.
- The disposable FE currently lists only internal `default_catalog`; it has no Hive external catalog. Actual Hive external-catalog authorization remains unverified because the production HMS/RustFS were intentionally not connected.
- Python compilation, Bash syntax checks, isolated Compose config validation, and bootstrap dry-run validation passed. The production FE has not been changed.

**Remaining before Unit 5 acceptance**: No additional isolated authorization test is open. Direct Spark/RustFS behavior is evidenced by Unit 3's completed role matrix; it was not re-run here because the retained probe launcher targets the production network. Production deployment and rollout remain separate from this test stage. Developer/analyst group-removal cache behavior and negative DDL/security checks are covered in the 2026-10-28 follow-up addenda. The direct writer role is an approved exception with its lifecycle limitation documented.

## 2026-10-28 additional native-role verification

**Negative authorization checks**: Using the isolated TLS client as `write-service-account`, the disposable FE denied `CREATE EXTERNAL CATALOG` (missing SYSTEM `CREATE EXTERNAL CATALOG`), `ALTER DATABASE default_lh SET DATA QUOTA 1G` (missing database `ALTER`), `CREATE DATABASE`, `CREATE VIEW`, `CREATE ROLE`, `CREATE USER`, and `GRANT lakehouse_analyst TO USER ...`. Each returned StarRocks access denied (5203); the statements created no objects or changed no quotas. A subsequent admin readback confirmed only `default_catalog` was present and no `writer_deny_probe` object remained. The test FE, BE, and isolated FreeIPA service remain running; no production service was queried or changed.

**Remaining verification gaps at this checkpoint**: The test FE then had only its internal catalog; the external-catalog integration was completed in the later addendum below. Direct Spark-to-RustFS enforcement is covered by Unit 3's authorization tests and was not repeated on the production-attached probe launcher.

## 2026-10-28 isolated Hive external-catalog verification

**Test topology**: Started a dedicated PostgreSQL 16.14 Hive metastore schema, Hive Metastore 3.1.3, and RustFS service with separate named test volumes and generated test-only credentials. All services attached only to `ranger-test-ipa-net`; no ports were published. A one-shot local Spark 3.5.5 / Iceberg 1.8.1 process created `test_prod.auth_probe`, `test_dev.auth_probe`, and `test_uat.auth_probe` with synthetic rows in the isolated HMS and object store. No live lakehouse service, credential, catalog, bucket, or object was used.

**StarRocks external catalog**: Created a disposable `iceberg_test` Hive catalog on `starrocks-ldap-test-fe`. StarRocks discovered the three synthetic databases and queried and wrote Iceberg data through the test HMS/RustFS. Role grants were scoped to those three synthetic databases.

**Authorization results**: All 15 checks passed. `developer-user` read all three and inserted only into UAT-independent development (`test_dev`); production insert was denied. `analyst-user` read `test_prod`; reads from `test_dev` and `test_uat` and production insert were denied. `write-service-account` read and inserted into all three. The test catalog's role grants were removed with the catalog during cleanup.

**Cleanup**: Dropped `iceberg_test`, stopped and removed only `starrocks-hive-test-*` containers and their two dedicated named volumes, and deleted only `.runtime/starrocks-hive-test/` containing the generated config and test credentials. The disposable StarRocks FE/BE and test FreeIPA remain for the rest of the role-test session. This Hive integration used one test-only store credential and did not itself exercise per-user Spark policies; those are covered by the separate Unit 3 Spark/RustFS role matrix cited above.

## 2026-10-28 external Iceberg materialized-view refresh verification

**Result**: In a fresh isolated Hive/RustFS stack, Spark created and populated a synthetic Iceberg table `iceberg_test.test_prod.auth_probe`. On the disposable StarRocks FE, `write-service-account` created `default_lh.mv_external_probe` as an asynchronous manual-refresh MV over that external Iceberg table. A forced synchronous `REFRESH MATERIALIZED VIEW` succeeded, and querying the MV returned the synthetic source row. This verifies the approved direct-role exception against the real external catalog query path, not only an internal source table.

The first DDL attempt exposed two test-environment details: the installed version requires an async refresh strategy such as `REFRESH MANUAL`, and the one-BE disposable cluster requires `replication_num=1`. After using the documented async MV syntax and matching the test BE count, creation and refresh passed. The test MV and catalog were dropped; the isolated Hive/RustFS containers, two dedicated volumes, generated test credentials, and runtime config were removed. The StarRocks FE again lists only `default_catalog`. No production service or data was used.

**Remaining operational gate**: Before any production application, separately inspect and reconcile existing FE users/grants and review the direct writer-role lifecycle with operators. This guarded bootstrap is test-only and no production rollout was performed.

**Unit 5 Build and Test disposition**: Isolated verification is complete. The 15-case external Hive/Iceberg authorization matrix, internal materialized-view role matrix, external-source MV manual refresh, LDAP group/cache behavior, unknown/no-group denial, and negative DDL/security checks are recorded above. Per-user direct Spark/RustFS authorization remains evidenced by the Unit 3 matrix; it was not repeated here because its retained probe launcher attaches to the production network. The test-only Hive/RustFS stack and its two volumes were removed; the disposable StarRocks FE/BE and isolated FreeIPA remain. No production grants, identities, catalogs, policies, or data were changed. Production grant inventory/reconciliation, writer-session and direct-role offboarding procedure, rollout, and rollback are separate deployment work, not outstanding isolated tests.

## Isolated legacy writer DML verification — 2026-10-28

The user chose to preserve the production writer's existing `INSERT`, `UPDATE`, and `DELETE` table grants during role migration. To check what these permissions actually permit on the installed StarRocks 4.1.6 external Iceberg connector, a separate test-only Hive Metastore/PostgreSQL/RustFS stack was started on `ranger-test-ipa-net`, with generated test credentials, named volumes, no published ports, and a synthetic `lake-test` bucket. No production credentials, catalog, network, bucket, or object was used.

Spark/Iceberg created `iceberg_dml_test.test_dml_db.dml_probe` with three synthetic rows. A temporary Iceberg external catalog was added only to `starrocks-ldap-test-fe`, and DML grants were scoped to that test database for `lakehouse_writer`. The test writer authenticated over TLS and `CURRENT_ROLE()` returned `lakehouse_writer`.

| Operation | Result | Evidence |
|---|---|---|
| `INSERT` | Passed | Added synthetic id 4; readback returned it. |
| `DELETE` | Passed | Deleted synthetic id 2; readback omitted it while retaining ids 1 and 3. |
| `UPDATE` | Unsupported | StarRocks Iceberg connector rejected the statement as unsupported. |

The external catalog was dropped, then only the temporary test Hive/RustFS/PostgreSQL containers and named volumes were removed. The synthetic test configuration and credentials under `.runtime/starrocks-hive-test/` were deleted. The disposable StarRocks FE/BE and isolated FreeIPA services were left as they were before this check. No production data was queried or changed.

**Migration implication**: carry the user's approved `INSERT`/`UPDATE`/`DELETE` grant scope into the production role as exact grants on the eight inventoried tables in `databaseA` and `databaseB`, without expanding to other tables. Record clearly that UPDATE is not operational on Iceberg with StarRocks 4.1.6 despite the retained grant. Any migration that changes how workflows update data needs separate design and approval. Production migration/rollback is not authorized by this isolated test.
