# Build and Test Summary — Unit 3 Spark ETL and Dremio JDBC

## Outcome

**Complete for the Unit 3 workload gates.** The generator and derived image built. Kerberos authentication as `write-service-account` and ETL into both Hive-backed Iceberg databases in RustFS passed. The user created the two Dremio Spaces manually. The Kerberized Hive source connects to the metastore and reads RustFS Iceberg metadata. The JDBC writer created all 16 views as `write-service-account`, and the user confirmed that querying the data from Dremio now works after enabling S3 compatibility mode and correcting the RustFS endpoint. Final manifest state is `etl=complete`, `jdbc=complete`, `overall=complete`. Per-user cross-engine allow/deny behavior remains to be validated separately.

## Preflight and build

- Existing Dremio, Hive, KDC, PostgreSQL, RustFS, and Spark services were running; Hive, KDC, PostgreSQL, and RustFS were healthy.
- Credential file presence/modes were inspected without printing values. The existing readiness marker is an empty file, so `scripts/run-tpch-workload.sh` was corrected to test marker existence instead of non-zero size.
- Compose rendering passed with `docker compose config --quiet`.
- Existing named mounts were inspected: PostgreSQL metastore, RustFS object store, Dremio data, and KDC state all remained attached to their existing volumes. No volume was reset or removed.
- The first workload image build hit stale Bullseye security package URLs (404). Inspection of the pinned Spark base showed its intended Debian snapshot timestamp; the derived image now uses the matching 2025-02-24 Bullseye snapshot. Generator and loader images then built successfully.
- Built image inspection confirmed Java 17.0.14, `/usr/bin/kinit`, `/usr/bin/kdestroy`, and the copied Dremio 26.0.5 legacy JDBC JAR.

## Generated inputs

Scale-factor-1 dbgen inputs were generated under ignored `.runtime/workload/tpch-data`. All eight required files were non-empty. Existing `tpch/data` fixtures were not targeted or changed.

## Kerberos, Hive, and RustFS

The first ETL attempt obtained a ticket but reported Hadoop UGI as `root` and stopped before catalog writes. The loader was corrected to set Hadoop UGI from Spark's Kerberos configuration and explicitly load the ticket cache. The verified effective identity became `write-service-account@LAKEHOUSE.LOCAL`.

Subsequent attempts exposed two source-format/schema issues before the final pass: TPC-H `.tbl` rows have a trailing field delimiter, and the `partsupp` schema had `availqty` and `supplycost` in the wrong order. Both were corrected. Spark CSV fields persist as nullable, so expected schemas now match the schemas that Spark/Iceberg actually writes.

Final ETL run: `38a7c016-88d7-4ec9-896c-350d5c3d49d2`.

| Hive database | Tables | State | Verified row counts |
|---|---:|---|---|
| `databaseA` | 8 | Complete | customer 150,000; lineitem 6,001,215; nation 25; orders 1,500,000; part 200,000; partsupp 800,000; region 5; supplier 10,000 |
| `databaseB` | 8 | Complete | customer 150,000; lineitem 6,001,215; nation 25; orders 1,500,000; part 200,000; partsupp 800,000; region 5; supplier 10,000 |

The final manifest records `etl=complete`, `jdbc=complete`, `overall=complete`, the verified writer identity, and per-object states. It is mode `0600` and contains no password, key, token, or ticket fields. The ticket cache lived in container tmpfs and was destroyed before the JDBC container started.

Idempotency rerun: `bf5bed18-0418-4108-af3d-07bc15d027eb`. All 16 tables reported `already_valid` with the same expected row counts. No table was appended, replaced, or rewritten. This ETL-only handoff manifest remains `jdbc=not_started`/`overall=running` because it was used specifically for the rerun check; the separate Dremio capability attempt and its final partial result are in the manifest above.

Earlier safe attempts created some expected tables before later validation/parsing failures. The successful run validated those existing tables by schema and row count, then created the remaining tables. No existing table was replaced or dropped. Persistent platform data and volumes were preserved.

## Dremio JDBC

The isolated `tpch-jdbc` container received only the Dremio writer password and results mount. It connected as `write-service-account`; the manifest reports `connection_state=connected`. The first attempt found the Spaces absent and confirmed that Dremio 26.0.5 rejects `CREATE SPACE` over this SQL path. After the user created `databaseA` and `databaseB`, the JDBC retry found both (`already_present`). The view lookup uses `INFORMATION_SCHEMA.VIEWS` because `SHOW VIEWS IN ...` is unsupported. Once the Hive source was available, the final retry created all 16 views (eight in each Space); every view state is `created`.

The user's first attempt to add the Hive source failed with `GSSException: Cannot locate default realm`; Dremio had no Kerberos configuration. A dedicated `dremio@LAKEHOUSE.LOCAL` service principal/keytab, `krb5.conf`, Dremio daemon Kerberos settings, and Hive 3 plugin configuration resolved that issue. After the user configured RustFS S3A credentials in the source, a JDBC retry showed that the Hive Metastore itself also needed `hadoop.proxyuser.dremio.hosts` and `.users` settings: it rejected impersonation of `write-service-account`. Added the same bounded Compose subnet and four-principal allowlist to `infra/hive/core-site.xml.in`, rendered the local config, validated it as XML, and restarted only `hive-metastore`. The next JDBC retry succeeded with all 16 views created. The successful run ID remains `38a7c016-88d7-4ec9-896c-350d5c3d49d2`; ETL was not rerun.

The workload did not use Dremio admin, create Spaces through a different API, or change the pinned server/driver. Dremio source access uses the configured RustFS writer S3A credentials. This validates the write-service-account flow, but the shared source storage credentials do not by themselves prove per-user RustFS authorization; validate `user_a`/`user_b` allow/deny outcomes separately before treating those boundaries as verified.

## Remaining work

- Validate per-user cross-engine allow/deny behavior for `user_a` and `user_b`; do not infer those outcomes from the writer's successful view creation.
- Dremio's STS credential check for S3-compatible stores was disabled with `dremio.s3.compat=true`; the user updated the source endpoint and secret and confirmed successful data queries. No ETL rerun was needed.
- Do not delete the successfully loaded tables or reset volumes for follow-up authorization checks.

## Approval and execution record

The user approved the Unit 3 Build and Test plan on 2026-10-23. Compose validation, image builds, SF1 generation, Kerberos ETL, Hive source integration, and JDBC view creation were executed. The user created both Dremio Spaces; the writer detected them. Final run `38a7c016-88d7-4ec9-896c-350d5c3d49d2` completed with all 16 views created. Plan gates passed; per-user access-denial scenarios remain separate follow-up work.
