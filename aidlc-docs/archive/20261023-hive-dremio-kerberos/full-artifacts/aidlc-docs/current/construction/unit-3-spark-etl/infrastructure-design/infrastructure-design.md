# Unit 3 Spark Runtime and Sample ETL — Infrastructure Design

## Scope and Deployment Target

Unit 3 adds a profile-gated, operator-invoked workload sequence to the existing single-host Compose project. It reuses the existing TPCH generator and the pinned Spark Iceberg runtime. Generation, Hive/RustFS ETL, and Dremio JDBC exposure run sequentially as one-shot operations. Default Compose startup does not generate or load data.

The existing long-running `spark` service continues to provide its notebook/master runtime. It does not receive writer keytabs or writer RustFS credentials. The ETL loader is a separate one-shot container using the same pinned Spark image with an explicit task entrypoint so it does not start the notebook, master, worker, or history-server daemons.

## Logical-to-Concrete Mapping

| Logical responsibility | Infrastructure mapping |
|---|---|
| TPCH generation | Existing `tpch-generator` profile service, using the current dbgen image/build. Change its output bind mount to a runtime-only input path (for example `.runtime/workload/tpch-data`) so generation does not replace repository fixtures. Default scale factor remains 1. |
| Spark ETL and validation | New profiled `tpch-loader` one-shot service, reusing the exact pinned `tabulario/spark-iceberg:3.5.5_1.8.1` image. Mount `tpch/load_tpch.py` and supporting code read-only. Override the base service entrypoint so no long-running Spark daemons start. |
| Hive catalog | Loader connects to `hive-metastore:9083` using the existing Hive-backed Iceberg Spark catalog configuration and writer Kerberos identity. |
| Iceberg storage | Loader connects to `object-store:9000` using path-style S3A and the writer's RustFS identity; data remains in the existing `object-store-data` volume under `lake/warehouse/databaseA.db` and `databaseB.db`. |
| Dremio JDBC | A second profiled, one-shot `tpch-jdbc` service reads the ETL manifest and uses `dremio:31010` with the non-admin writer account. It receives only the Dremio password and result directory; no host port is used between Compose services. |
| Input data | Generated `.tbl` files live under ignored `.runtime/workload/tpch-data`; generator writes them and loader mounts them read-only. The current checked-in/workspace `tpch/data` files are not the generator's destructive output target. |
| Run manifest | Redacted JSON/text manifest is written under `.runtime/workload/results`, outside persistent catalog/object-store data and outside tracked source. |
| Ticket cache | A mode-restricted tmpfs mount such as `/run/krb5` inside the one-shot loader. It is not a Docker named volume or host bind mount. An exit/signal trap removes its cache files. |

## Image and JDBC Driver Decisions

- Reuse the pinned Spark 3.5.5/Iceberg 1.8.1 runtime. Runtime inspection confirmed Java 17 and that `kinit` is absent, so derive the one-shot image from the pinned Spark image and add the small Kerberos client package needed for keytab-to-cache acquisition. Add the Dremio JDBC client artifact and workload task files; do not bundle credentials.
- Use the Dremio legacy JDBC driver from the same pinned Dremio 26.0.5 image for direct coordinator JDBC on port 31010. Dremio's documentation says the legacy driver is bundled in Dremio installations and supports Java 11+ from driver 25.0, while the Arrow Flight SQL JDBC documentation lists Dremio 26.1+ as a prerequisite; this PoC pins 26.0.5. The legacy driver is no longer enhanced, so this choice is version compatibility, not a claim that it is the preferred future client. Confirm the JAR path and Java compatibility during Code Generation/Build and Test.
- Use JDBC SQL for `CREATE SPACE` and `CREATE VIEW` operations. Dremio's SQL reference documents both commands. The exact non-admin writer privilege behavior on pinned Community 26.0.5 remains a required runtime gate.
- References: [Dremio legacy JDBC driver](https://docs.dremio.com/current/client-applications/drivers/jdbc/), [Arrow Flight SQL JDBC prerequisites](https://docs.dremio.com/current/client-applications/drivers/arrow-flight-sql-jdbc-driver/), [CREATE SPACE](https://docs.dremio.com/current/reference/sql/commands/create-space/), [CREATE VIEW](https://docs.dremio.com/current/reference/sql/commands/create-view/).

## Compose Profile and Invocation Order

1. Operator confirms Unit 1/2 stack and required writer credential artifacts are ready.
2. An explicit `workload` profile invocation generates scale-factor-1 data with `tpch-generator` into `.runtime/workload/tpch-data`.
3. The orchestration helper verifies all eight expected files, starts `tpch-loader`, and waits for its exit status.
4. Loader obtains the writer ticket, validates prerequisites, and executes ETL: create missing `databaseA`/`databaseB`, create missing Iceberg tables, validate existing schema/counts, and record per-object results. It never replaces existing tables and destroys the ticket before exit.
5. If ETL validation passes, the helper starts independent `tpch-jdbc`. It attempts Space/view SQL as the Dremio writer. If Dremio is unavailable or denies an operation, data is preserved and the manifest records JDBC failure/overall partial status.
6. Helper returns success only when requested ETL and JDBC steps complete; partial/failed outcomes remain nonzero/actionable and are recorded in the manifest.

The Compose service must not have a hard `depends_on: dremio: service_healthy` that prevents successful ETL when Dremio is unavailable; Dremio is a later optional phase whose failure is reported as partial. The ETL step does require KDC, Hive, RustFS/bucket, and credential/input preflight. Use bounded readiness waits, not retries for authorization/conflict errors.

## Credential and Secret Boundaries

| Consumer | Allowed inputs | Explicitly excluded |
|---|---|---|
| Generator | Scale factor; generated input output mount | All platform credentials |
| Spark ETL | Writer keytab read-only; writer RustFS access/secret files read-only; Kerberos config; temporary cache tmpfs | RustFS root/admin, Dremio password, PostgreSQL credentials, other user/admin keytabs |
| JDBC step | Dremio `write-service-account` password file; JDBC client artifact; non-secret manifest | Dremio admin password, RustFS credentials, Kerberos keytab/cache |

Use Compose secrets for RustFS/Dremio credentials where file-backed secrets are already supported. Mount only the writer keytab file, not the entire keytabs directory. Keep JDBC URL free of password material; load it from a protected file. Do not include credential files in the image build context or manifest.

## Network and Ports

- Loader, generator, KDC, Hive, RustFS, Spark, and Dremio use the existing private `iceberg_net` Compose network.
- Dremio JDBC target is the internal service name and port `31010`. No additional host port is published.
- Existing host-published developer ports remain loopback-only. No new API, report, or workload port is introduced.

## Storage, Lifecycle, and Reruns

- `.runtime/workload/tpch-data` stores reproducible source files and can be regenerated; it is separate from RustFS's existing persistent object volume.
- `.runtime/workload/results` stores non-secret run manifests. Do not store keytabs, tickets, passwords, access keys, or secret-bearing URLs there.
- The Kerberos cache exists only in container tmpfs and is removed on normal exit, error, and signal.
- Existing Hive tables and Dremio views are inspected before creation. Matching schema/count/target means `already_valid`; mismatches mean `conflict`. Never use `createOrReplace`, drops, truncate, append, or automatic cleanup.
- No persistent volume is reset or recreated by the workload invocation.

## Feasibility Gates and Risks

1. Confirm the Spark image includes working `kinit`/Kerberos client libraries and accepts the ticket cache in the actual one-shot execution mode.
2. Confirm writer DDL and S3A permissions against Hive/RustFS. Unit 2's namespace smoke test does not prove table writes or effective identity enforcement.
3. Confirm the legacy JDBC JAR path in the pinned Dremio image, Java 11+ support in the Spark runtime, and connectivity to Dremio 26.0.5.
4. Verify `CREATE SPACE`, `CREATE VIEW`, and object inspection under the non-admin Dremio writer. If denied, preserve ETL output and return partial status; do not retry with admin.
5. Confirm that a `CREATE VIEW` operation does not replace an existing conflicting view; inspect before issuing SQL and omit `OR REPLACE`.

If a gate fails, preserve pinned versions/data/credential boundaries and record the smallest proposal for review. No Airflow/Jenkins, user authorization demo, or sample-reader grant is added in Unit 3 infrastructure.
