# Build and Test Plan — StarRocks Integration

## Scope

Verify the approved Unit 1 identity provisioning, Unit 2 StarRocks FE/BE runtime, and Unit 3 Iceberg catalog and SQL access bootstrap against the retained local lakehouse. Preserve existing Hive metadata, RustFS data, KDC state, StarRocks volumes, credentials, and notebook workspaces. Do not modify the sibling Airflow/Jenkins project.

## Safety Gates

- Never print credential values or raw SQL/client/server output that might contain them.
- Run `scripts/verify-starrocks-sql-secret-safety.sh` with non-secret probe values before any real credential-bearing SQL. A failure or incomplete inspection blocks `scripts/bootstrap-starrocks-sql.sh`.
- Run bootstrap only after a passing marker matches the current FE image and logging configuration. Bootstrap is additive and may create SQL accounts/catalog/grants and protected local credential files; it does not create or modify Hive sample data.
- Do not delete volumes, clear logs/history, rotate credentials, overwrite sample tables, or clean up objects not uniquely created by a test.
- Any unverified item remains explicitly incomplete; do not infer success from generated code or configuration.

## Verification Checklist

### Local checks — completed 2026-10-24

- [x] Bash syntax check for canary/bootstrap scripts — passed.
- [x] Python source compilation of `infra/starrocks/sql-bootstrap/runner.py` — final compile passed 2026-10-24 without writing bytecode artifacts.
- [x] `docker compose --profile starrocks config --quiet` — final Compose validation passed 2026-10-24.
- [x] Installed the host MySQL-compatible CLI at `/opt/homebrew/opt/mysql-client/bin/mysql`.

### Runtime checks — results 2026-10-24

- [x] Started the existing lakehouse services. KDC, Hive Metastore, and RustFS were healthy. The startup wrapper returned a Compose project lookup error after dependencies started; StarRocks was started separately below.
- [x] Built StarRocks FE/BE images and started the services with existing named volumes. Both FE and BE reached healthy state; no volumes were deleted or reset.
- [x] Ran the secret-exposure canary against the current FE image and effective logging configuration before credential-bearing SQL. It passed. Re-ran after FE/config rebuild; it passed again.
- [x] Provisioned the StarRocks Kerberos service identity/keytab, RustFS identity, and PostgreSQL identity. Existing credential values were preserved.
- [x] Registered/reconciled the existing `iceberg` external catalog and provisioned `root`, `admin`, `user_a`, `user_b`, and `write_service_account`. Bootstrap completed with authentication checks and least-privilege grant checks.
- [x] Verified `iceberg` lists `databasea` and `databaseb`, and queried an existing sample table through the catalog using a read-only preflight.
- [x] Verified the SQL read matrix: `user_a` reads databaseA and is denied databaseB; `user_b` and `write_service_account` read both; `admin` reads both.
- [x] Verified `user_a` and `user_b` are denied a zero-row INSERT attempt. This was a privilege check with a false predicate and did not change sample rows.
- [x] Resolved and verified Hive catalog table creation/write path: FE logs showed the `UnsupportedFileSystemException` was returned by Hive Metastore as a `MetaException` during `create_table`. Added `fs.s3.impl=org.apache.hadoop.fs.s3a.S3AFileSystem` and `fs.AbstractFileSystem.s3.impl=org.apache.hadoop.fs.s3a.S3A` to the Hive Metastore `core-site.xml` template, rendered it, and restarted HMS. A disposable Iceberg table then created successfully, accepted one insert, returned the inserted value, and was dropped along with its temporary catalog. The exact probe spill object was removed and its unique RustFS prefix re-listed as empty. This verifies the SQL root path; writer-account DML remains a separate check.
- [x] FE/BE runtime Hadoop S3 configuration is generated in per-container `/run/krb5` tmpfs and symlinked into StarRocks' normal `conf` directory. The secret file mode is 0600 and the secret-safety canary passed after FE/BE recreation. An intermediate `HADOOP_CONF_DIR` pointing at an isolated directory caused Hive Kerberos negotiation failure; using StarRocks' existing `conf` directory restored Hive access. This FE/BE configuration did not resolve the HMS-side `s3` error by itself; the effective fix was the HMS core-site alias.
- [x] Recreated FE/BE through `scripts/start-starrocks.sh`; the paired-state preflight passed, the wrapper canary passed, and backend registration succeeded. After restart, catalog discovery and the `user_a` databaseA allow/databaseB deny behavior still passed.
- [x] Verified positive DML/readback as `write_service_account` on `iceberg.databaseA.nation`: inserted one uniquely keyed row, read it back as the writer, deleted only that row, and confirmed it was absent. No pre-existing sample rows were changed. The table has the expected Iceberg snapshot history from the reversible insert/delete; snapshots/files were not expired or manually removed.
- [x] Verified Spark-to-StarRocks interoperability: ran a disposable one-row Iceberg table write in Spark as `write-service-account@LAKEHOUSE.LOCAL`, read the row through StarRocks, dropped the unique table, deleted its four RustFS objects under its exact unique prefix, and confirmed the prefix empty.
- [x] Verified FE/BE restart persistence using the startup wrapper: FE/BE volumes were preserved and catalog/user policy state plus the `user_a` allow/deny behavior remained after recreation.
- [x] Confirm both persistent Jupyter workspace volumes still exist after verification; the Hub remained running, and no notebook service or workspace volume was restarted, mounted, or modified by these checks. Notebook file contents were not inspected.
- [x] Verify a constrained reference profile for the approved occasional-query workload: the read-only TPC-H Q1 query passed with temporary limits of 2 CPUs and 2 GiB memory on each of FE and BE. This is the lowest per-node resource profile tested, not a proven absolute minimum. Recommend at least these FE/BE limits for this query profile; the complete stack passed on a Docker allocation of 6 CPUs and 15.6 GiB memory.
- [ ] Establish a true minimum and verify Docker storage capacity/growth. Lower CPU/memory profiles were not tested; Docker Desktop's disk quota and growth under ETL/concurrency remain unknown. Current images, volume footprint, and host free-space measurements are documented below; they support a practical starting recommendation, not a measured storage minimum.
- [x] Record observed FE/BE startup duration under stated conditions. On 2026-10-24, with cached local images and recognized persistent state, FE reached healthy about 70 seconds after its container start; BE reached healthy about 56 seconds after its start. The BE health time was about 75 seconds after FE started. These are single-run observations from Docker container and health-check timestamps, not guarantees.
- [x] Record current StarRocks persistent-volume footprint: `starrocks-fe-meta` 12.24 MB and `starrocks-be-storage` 6.647 MB at the time of the 2026-10-24 Docker usage snapshot. This is current usage, not a capacity recommendation or growth estimate.
- [x] Run a read-only TPC-H Q1 aggregation on the existing scale-factor-1 Iceberg `lineitem` table through StarRocks as `user_b`; it completed with four result groups in 3.1 seconds. During the query, sampled FE/BE peaks were 855.1/485.9 MiB and 5.46%/96.83% CPU. Hive Metastore, RustFS, and PostgreSQL sampled peaks were 576.9, 338.2, and 80.0 MiB. Sampling used one-second polling; brief peaks can be missed.
- [x] Record host conditions: Docker exposed 6 CPUs and 16,746,106,880 bytes (15.6 GiB) of memory; FE and BE had no CPU/memory limits. The host filesystem had 217 GiB free at measurement time, but Docker Desktop's disk quota was not measured. Treat this passing host profile as the tested reference and do not infer a lower minimum from it.
- [x] Test FE/BE resource limits using a read-only query. With each node temporarily capped at 2 CPUs and 2 GiB, the TPC-H Q1 query still returned four groups. Docker's `update` command did not remove limits when passed zero values; the limits were restored by Compose recreation through `scripts/start-starrocks.sh`, and inspect confirmed both nodes healthy with their original unlimited settings. The paired-state preflight, canary, and BE registration passed after recreation; named volumes were preserved.
- [x] Exercise paired-state preflight with isolated temporary fixtures: both empty passed, a recognized FE/BE pair passed, one-sided FE state failed closed, and an unrecognized pair failed closed. No production StarRocks volume was mounted in these tests.
- [x] Exercise ticket refresh failure handling in an isolated no-network container with a temporary empty keytab. The helper returned nonzero and emitted only its safe degradation diagnostic. No running service ticket cache or KDC was touched.
- [ ] Validate ticket-refresh failure while a valid TGT remains usable and verify behavior after ticket expiry. The isolated helper test did not exercise live FE/BE continuity or expiry; no production KDC/ticket state was disrupted to simulate expiry.

### Runtime issue and fix

The first bootstrap stopped at a built-in `public` role grant check after creating some additive objects. Reconciliation was corrected to allow only StarRocks' default `information_schema` grant. Subsequent checks found and fixed several runtime integration defects: `SHOW CATALOGS` has multiple columns; StarRocks masks catalog credentials in DDL output; StarRocks FE/BE need minimal Hive SASL/Kerberos client configs; Java must initialize Hadoop UGI in Kerberos mode; the Hive service principal must match the KDC identity; and FE/BE startup must not depend on unauthenticated root SQL after bootstrap secures that account. The host startup flow now registers the BE through the protected credential helper.

No destructive reset, credential rotation, table replacement/drop of existing samples, or workspace cleanup was performed. The approved reversible writer check temporarily inserted and then deleted a uniquely keyed row in `databaseA.nation`; pre-existing row values are unchanged, and Iceberg snapshot history was retained. The TPC-H query was read-only. Both Jupyter workspace volumes remained present, and this verification did not inspect or alter their contents. Compose recreation restored the FE/BE resource settings after the constrained test and preserved their volumes. At the time this evidence was collected, lower resource minima, Docker storage quota/growth, and live ticket-refresh continuity through TGT expiry remained open; the later closure decision is recorded below.

## Closure Decision — 2026-10-25

The user approved closing Build and Test with limitations. This is a verification waiver for the outstanding checks below; it does not indicate those checks passed.

- Live FE/BE continuity during ticket-refresh failure while a valid TGT remains usable, and behavior after ticket expiry, remain unverified.
- Docker Desktop storage quota and growth under ETL/concurrency remain unverified.
- Resource profiles below 2 CPUs/2 GiB per FE/BE remain unverified; 2 CPUs/2 GiB is the lowest tested profile for the documented read-only query.

The verification evidence and practical reference profile below remain valid within their stated scope. The next AI-DLC stage is Deployment Handoff; no deployment was executed as part of closing this gate.

## Current Result

Local checks passed after the runtime fixes: Bash syntax, Python source compilation, and `docker compose config --quiet`. The MySQL CLI is installed at `/opt/homebrew/opt/mysql-client/bin/mysql`.

The existing platform services are running. StarRocks FE/BE and Hive Metastore are healthy, the current canary passed, catalog discovery and a read-only sample query passed, SQL users/grants were reconciled, and the read/deny matrix passed. Compose recreation preserved StarRocks catalog/user policy state; the post-restart `user_a` allow/deny check passed. A controlled root-authenticated disposable Iceberg table CREATE, INSERT, and SELECT passed after adding the `s3` filesystem aliases to Hive Metastore's Hadoop core-site. A reversible writer-account probe inserted and deleted one unique row in `databaseA.nation`; the test row is absent and no pre-existing sample row changed. A separate Spark write as the Kerberos writer principal was read successfully through StarRocks; the disposable table and its exact RustFS prefix were removed. The root cause was HMS-side filesystem registration, not missing StarRocks catalog S3 settings. Both Jupyter workspace volumes remained present and were not touched; file contents were not inspected. Credentials were not rotated and no volumes were reset.

An idle point-in-time Docker resource sample was collected on 2026-10-24. On 2026-10-25, a read-only TPC-H Q1 scan of the existing scale-factor-1 `databaseA.lineitem` table completed as `user_b` in 3.1 seconds and returned four groups. One-second sampling observed FE at 855.1 MiB/5.46% CPU, BE at 485.9 MiB/96.83% CPU, Hive Metastore at 576.9 MiB/1.50% CPU, RustFS at 338.2 MiB/0.02% CPU, and PostgreSQL at 80.0 MiB/0.00% CPU; brief peaks may have been missed. The same query passed with temporary 2 CPU/2 GiB limits on each StarRocks node. Docker exposed 6 CPUs and 15.6 GiB memory; host disk had 217 GiB free, but Docker's storage quota was not measured. FE/BE limits were restored to unlimited and both nodes returned healthy after Compose recreation. Current StarRocks images are 2.79 and 3.82 GB; current FE/BE volume footprints are 13.99 MB and 9.287 MB. A practical initial recommendation for this single-query PoC profile is 2 CPUs and 2 GiB per StarRocks node, and a Docker allocation matching or exceeding the tested 6 CPUs/15.6 GiB full-stack host. Reserve at least 10 GB incremental Docker storage for the two StarRocks images and node state, excluding shared platform images and future warehouse growth. This storage figure is a recommendation derived from measured image/state sizes, not a measured free-space threshold. Tests below these CPU/memory settings, Docker disk quota/growth, and ETL/concurrency are not covered.

Isolated safety checks passed for empty and recognized paired-state fixtures, and fail-closed behavior passed for one-sided and unrecognized fixtures. An isolated no-network invalid-keytab run confirmed the refresh helper's safe failure message. Live refresh failure while a TGT remains valid and behavior after expiry were not tested. The user approved closing Build and Test with limitations on 2026-10-25; these gaps remain explicitly unverified under that waiver.
