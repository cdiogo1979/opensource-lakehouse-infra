# Hive, Kerberos, Dremio and RustFS PoC

This local Docker Compose PoC replaces Nessie with a Hive 3.1.3 Metastore catalog backed by PostgreSQL. RustFS stores Iceberg data in the `lake` bucket. Spark writes the sample TPCH tables as `write-service-account`; Dremio JDBC Space/view creation is attempted as a separate post-ETL step.

## Components

| Service | Purpose |
|---|---|
| `kdc` | Disposable MIT Kerberos realm, Hive and Dremio service identities, and protected provisioning keytab |
| `identity-provisioner` | Explicit one-shot workload Kerberos, RustFS IAM, and PostgreSQL role setup |
| `metastore-db` | PostgreSQL database dedicated to Hive metadata |
| `hive-schema-init` | One-shot, non-destructive Hive schema inspection/initialization |
| `hive-metastore` | Hive Thrift catalog on the private Compose network |
| `object-store` | RustFS S3-compatible storage |
| `create-bucket` | Ensure-only creation of the `lake` bucket |
| `spark` | Spark 3.5.5 and Iceberg 1.8.1 with Hive catalog configuration |
| `dremio` | Dremio Community 26.0.5, Kerberos client for Hive 3.x, JDBC Spaces/views |
| `tpch-generator` | Optional, one-shot scale-factor-1 TPCH input generation |
| `tpch-loader` | Optional one-shot writer-authenticated Hive/RustFS ETL |
| `tpch-jdbc` | Optional one-shot Dremio Space/view setup using only the Dremio writer credential |

The generator and loader are available only under the optional `workload` Compose profile and do not run during normal startup. Generated inputs and non-secret manifests live under ignored `.runtime/workload/`; Iceberg objects remain in the existing RustFS volume. Dremio Space/view failure is reported separately and does not remove successful ETL data.

## Prerequisites

- Docker Desktop or another Docker Engine with Docker Compose v2.
- Hive 3.1.3 runs with the host-native Java 8 runtime; its pinned upstream Hive/Hadoop/Tez distributions are reused in the local image build, so arm64 hosts do not run the Metastore JVM under amd64 emulation.
- Allocate enough Docker memory for Spark, Dremio, RustFS, Hive, PostgreSQL and the KDC. Hive 3.1.3 is an archived/EOL release and is used for this local PoC only.

## Start and inspect

```bash
./scripts/start.sh
docker compose ps
docker compose logs -f hive-metastore
```

The bootstrap command creates disposable local credentials in the ignored `.runtime/credentials/` directory and renders the local Hive configuration. It preserves credentials on later starts and does not print their values. The PostgreSQL password is provided using a Compose file secret; Hive's generated configuration is local and mode-restricted.

Developer-facing ports bind to loopback only:

- Dremio: <http://127.0.0.1:9047>
- RustFS console: <http://127.0.0.1:9001>
- Spark UI: <http://127.0.0.1:8082>
- JupyterHub: <http://127.0.0.1:8008>

Hive Thrift (`hive-metastore:9083`), PostgreSQL (`metastore-db:5432`), KDC, and kadmind are internal to the Compose network.

## Stop and reset

Stop services and preserve all data:

```bash
./scripts/stop.sh
```

Reset all Compose volumes, including Hive metadata, the KDC database, RustFS objects and Dremio state:

```bash
./scripts/clean.sh
```

The reset script requires typing `RESET ALL VOLUMES`. It removes the generated Hive service keytab so it can be recreated with the empty KDC volume. Local passwords/access keys remain in `.runtime/credentials/`.

## Unit 2 identity provisioning

The local bootstrap creates missing credentials under `.runtime/credentials/` without replacing existing files. Before provisioning, complete Dremio first-run in the UI using the username `admin` and `.runtime/credentials/dremio-admin-password`. If Dremio was already initialized, preserve the existing password and securely update that local file to match it. Then create the local user `write-service-account` in Dremio's user-management UI using `.runtime/credentials/dremio-writer-password`; do not grant it the `ADMIN` role. The provisioner does not automate Dremio account creation.

After starting the core stack and completing those Dremio steps, run the host helper. It invokes the one-shot profile, renders Hive with its named RustFS service credential, and restarts Hive:

```bash
./scripts/provision-identities.sh
```

To rotate the RustFS writer secret, replace `.runtime/credentials/rustfs-writer-secret-key` with a newly generated value, refresh the derived `rustfs-writer.env` by rerunning `scripts/bootstrap-local.sh`, then run `ROTATE_RUSTFS_WRITER_SECRET=true docker compose --profile identity-provisioning run --rm identity-provisioner`. The guarded provisioner updates the IAM identity, reattaches its scoped policy, and verifies S3 access. Update the `hive` source's `fs.s3a.secret.key` in Dremio's UI before querying data; the old key stops working immediately.

The KDC bootstrap creates the Hive and dedicated `dremio@LAKEHOUSE.LOCAL` service identities/keytabs before Dremio starts. The identity provisioner verifies Dremio's keytab and creates the workload principals, RustFS IAM identities/policies, and PostgreSQL admin/service-role split. Dremio's keytab is readable by its container user through the supplementary local group; the host runtime credential directories remain owner-only. Persistent volumes are preserved. A successful identity setup alone does not prove the later Dremio/Spark end-user authorization scenarios.

The operator must complete Dremio account setup manually before provisioning. Dremio's Kerberos service identity is separate from Hive's Metastore identity. Spark no longer receives the RustFS root environment file. After a successful profile run, the helper switches Hive to its named S3A service credentials.

After provisioning, Dremio starts with the realm config, its dedicated keytab, and the Hive 3 connector's Kerberos/proxy-user settings. In the Dremio UI, add a **Hive 3.x** source named `hive` with metastore host `hive-metastore`, port `9083`, SASL enabled, and Hive principal `hive/hive-metastore@LAKEHOUSE.LOCAL`. Select **Storage Based with User Impersonation**. The Dremio connector and Hive Metastore both restrict proxying to `admin`, `write-service-account`, `user_a`, and `user_b` from the local Compose subnet. For per-query-user authorization through views, disable **Allow VDS-based Access Delegation** so the view owner does not replace the querying identity. In **Advanced Options**, set the S3A endpoint to `object-store:9000` (without a scheme), path-style access to `true`, SSL to `false`, and the credentials provider to `org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider`. Add `fs.s3a.access.key` and `fs.s3a.secret.key` under **Credentials** using the local RustFS writer credential files; Dremio needs these to read Iceberg metadata and data from RustFS. Dremio's Hive plugin is configured with S3 compatibility mode because RustFS does not implement AWS STS `GetCallerIdentity`.

## Unit 4 Dremio query identities and authorization

The local bootstrap now creates `.runtime/credentials/dremio-user-a-password` and `dremio-user-b-password` only when absent, with mode `0600`. Existing files are preserved; the bootstrap does not create Dremio accounts or change any RustFS key. Create the Dremio local users `user_a` and `user_b` manually in the Dremio user-management UI and set each password from its corresponding local file. Do not grant either test user the `ADMIN` role. Grant only the Dremio source/query permissions needed to run the examples. The Hive username mapping is as-is: `user_a` to `user_a`, and `user_b` to `user_b`.

The Hive Metastore configuration template now enables its storage-based authorization pre-event listener/provider and read checks. To render this configuration on an existing local setup, run `./scripts/bootstrap-local.sh` (it preserves existing credential values), then restart only Hive Metastore with `docker compose restart hive-metastore`. Do not run a volume reset. This configuration does not establish that RustFS path authorization distinguishes users: Hive and Dremio still use their configured service/source credentials for S3 access. Treat the per-user matrix as unverified until all outcomes and effective Hive usernames are evidenced.

Log in to Dremio separately as each user and run the four statements in [`sql/dremio-authz-matrix.sql`](sql/dremio-authz-matrix.sql). `user_a` must be allowed on `databaseA` and denied on `databaseB`; `user_b` must be allowed on both. Record the effective Hive username, outcome, and denial component. A Dremio login/source/Space denial, missing table, or RustFS credential error is not a Hive authorization denial. Preserve all data and credentials if a scenario fails; do not retry as admin or rotate the RustFS writer key.

## Unit 3 sample workload

After identity provisioning has completed and Dremio's local `write-service-account` exists, run the opt-in workload:

```bash
./scripts/run-tpch-workload.sh
```

The script builds the generator/loader images, writes scale-factor-1 input files to `.runtime/workload/tpch-data`, and runs the ETL as `write-service-account`. It creates or validates all eight TPCH tables in both `databaseA` and `databaseB`; an existing schema or row-count mismatch stops the affected workload without replacing data. The Kerberos ticket cache is temporary container tmpfs and is destroyed before the JDBC container starts. The run manifest is written under `.runtime/workload/results/` without credentials.

After ETL validation, a separate `tpch-jdbc` container creates or validates matching Dremio Spaces and views over JDBC using the non-admin writer. It receives no Kerberos keytab/cache or RustFS credentials. The Dremio Hive source name defaults to `hive` and can be set with `DREMIO_HIVE_SOURCE`. Create that source manually in the Dremio UI after identity provisioning; its Kerberized endpoint, impersonation, and RustFS S3A settings are documented above. The client never retries as admin. A nonzero exit with `overall=partial` means ETL data was retained and JDBC work needs follow-up. Review the manifest for per-object status; do not use `scripts/clean.sh` to retry.

## Current implementation boundaries and open gates

- Unit 2 Kerberos, RustFS IAM, PostgreSQL provisioning, named Hive S3 credentials, and Spark namespace access passed the recorded Build and Test gates. Dremio local accounts are created manually as documented above.
- Unit 3 Build and Test confirmed the ETL and all 16 Hive/RustFS tables, connected the Kerberized Hive source to RustFS, and created all 16 Dremio views as `write-service-account`. See `aidlc-docs/current/construction/build-and-test/unit-3-build-and-test-summary.md`.
- Kerberos SASL and Hive's effective-user setting are configured as integration candidates. They do not prove that Spark or Dremio preserves the intended effective user.
- Per-user cross-engine allow/deny behavior still needs separate validation. The Hive source, Kerberos impersonation for `write-service-account`, and Dremio Space/view setup passed. Spark 3.5.5/Iceberg 1.8.1 loaded and validated the sample data through Hive 3.1.3/PostgreSQL 16.14 and RustFS in Unit 3 Build and Test.
- RustFS bootstrap credentials are used only by RustFS, bucket setup, and the one-shot IAM provisioner. They are not the future `write-service-account` credentials.
- Dremio Community JDBC permissions and Hive-source integration passed for the writer; the writer is never elevated to admin.

Successful container readiness means only that the configured processes and foundation initialization are available; it does not imply authorization or impersonation has passed.

## Unit 5 JupyterHub and per-user Spark

`./scripts/start.sh` also builds the JupyterHub and single-user Spark images and starts the Hub as part of the default Compose stack. It binds to <http://127.0.0.1:8008>. The Hub uses DummyAuthenticator: `user_a`, `user_b`, and `admin` are development labels, not verified human identities. Keep the Hub local to this host; this is not a production login service.

Before starting user servers, the matching Kerberos principals/keytabs and RustFS identities must already exist. Use the existing explicit identity provisioning procedure; Hub startup does not provision or rotate identities. The only admitted labels are `user_a`, `user_b`, and `admin`. Each maps to its matching same-named Kerberos and RustFS identity. The `admin` label grants JupyterHub administrator rights, but its Spark session uses only the `admin` data identity and is not a substitute for the `user_a` or `user_b` authorization checks.

DockerSpawner creates an isolated non-root `jovyan` container on `iceberg-poc-net` for each active user. The Hub alone mounts the Docker socket. A user container gets one persistent named work volume, its own keytab and RustFS access/secret files mounted read-only, and a private ephemeral Kerberos ticket cache. The Hub receives credential path references but no credential values or credential file mounts. `.runtime/` and `.runtime/credentials/` remain mode `0700`; only the six admin/user RustFS files and three matching keytabs are made group-readable (`0640`) for the matching container's supplementary host GID. The writer and root credentials are unchanged. Build and Test must confirm non-root file readability and verify that other identities are not exposed.

Open the read-only example at `/opt/jupyter-examples/spark-authz.py` from a user's Jupyter file browser. Run the direct Spark queries as `user_a` and `user_b` separately. Expected results are: `user_a` can query `databaseA` and is denied on `databaseB`; `user_b` can query both. A Kerberos, Hive connectivity, missing-object, resource, or RustFS credential failure is not an authorization denial. The notebook reports only the username, principal, database, expected/actual result, and a redacted failure category.

The single-user image retains Spark 3.5.5/Iceberg 1.8.1 and JupyterHub 5.3.0; the Hub pins DockerSpawner 14.0.0 and its direct Python dependencies. Up to three sessions are supported on a best-effort basis without queuing or resource tuning. Stop or recreate only the affected server from the Hub UI after diagnosis; its work volume persists. Use `docker compose logs jupyterhub` and the spawned server's Docker logs for local troubleshooting. No session recovery step resets Hive, RustFS, Dremio, catalog, or user workspace volumes.
