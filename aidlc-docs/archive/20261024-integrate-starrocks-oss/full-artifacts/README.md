# Hive, RustFS, Kerberos, Spark, and JupyterHub PoC

This local Docker Compose project uses Hive Metastore 3.1.3 as the Iceberg catalog, PostgreSQL for metastore metadata, RustFS for S3-compatible table storage, and Spark for the TPCH sample workload and notebooks.

## Components

| Service | Purpose |
|---|---|
| `kdc` | MIT Kerberos realm and service/workload/user identities |
| `identity-provisioner` | One-shot Kerberos, RustFS IAM, and PostgreSQL role setup |
| `metastore-db` | PostgreSQL storage for Hive catalog metadata |
| `hive-schema-init` | Non-destructive Hive schema inspection/initialization |
| `hive-metastore` | Hive Thrift catalog on the internal Compose network |
| `object-store` | RustFS S3-compatible object storage |
| `create-bucket` | Ensure-only creation of the `lake` bucket |
| `spark` | Spark 3.5.5 and Iceberg 1.8.1 with Hive catalog configuration |
| `jupyterhub` | Local Hub that starts isolated Spark notebook containers |
| `tpch-generator` | Optional scale-factor-1 TPCH input generation |
| `tpch-loader` | Optional Spark ETL as `write-service-account` into Hive/RustFS |

TPCH generation and loading are available under the `workload` Compose profile and do not run during normal startup. Inputs, results, and local credentials are stored under ignored `.runtime/`; Iceberg objects remain in the RustFS volume.

## Prerequisites

- Docker Desktop or another Docker Engine with Docker Compose v2.
- Allocate enough Docker memory for Spark, RustFS, Hive, PostgreSQL, Kerberos, and JupyterHub.
- Hive 3.1.3 is an archived/EOL release and is intended for this local PoC only.

## Start and inspect

```bash
./scripts/start.sh
docker compose ps
docker compose logs -f hive-metastore
```

Bootstrap creates missing local credentials under `.runtime/credentials/`, preserves existing values, and does not print credential contents. The startup script builds and starts the retained services.

When migrating an existing local installation, run the one-time Dremio cleanup described below before starting or stopping the full stack. If the KDC container is stopped or absent, first run `docker compose up -d kdc`, which reuses the existing KDC volume.

Developer endpoints bind to loopback:

- RustFS console: <http://127.0.0.1:9001>
- Spark UI: <http://127.0.0.1:8082>
- JupyterHub: <http://127.0.0.1:8008>

Hive Thrift (`hive-metastore:9083`), PostgreSQL (`metastore-db:5432`), Kerberos, and kadmind are internal to the Compose network.

## Provision identities

After starting the stack, provision the Hive, workload, and StarRocks identities:

```bash
./scripts/provision-identities.sh
```

The local bootstrap creates `.runtime/credentials/rustfs-starrocks-secret-key` if it is absent, with mode `0600`; existing contents are preserved. The provisioner creates or verifies the Kerberos principal `starrocks@<realm>` and keytab `.runtime/credentials/keytabs/starrocks.keytab`, plus the existing Hive and workload identities. It provisions RustFS account `starrocks` with policy `lakehouse-starrocks`, scoped to `databaseA` and `databaseB` in the `lake` bucket. The StarRocks credential is distinct from the Spark writer and other platform identities.

Kerberos and RustFS provisioning are attempted independently once each. The command reports separate provider outcomes and returns failure if either provider fails. Successful provider resources remain in place; after correcting the reported cause, rerun `./scripts/provision-identities.sh` to reconcile idempotently. Existing credentials and principal keys are not implicitly rotated. Existing RustFS policy drift fails closed and requires manual reconciliation. On success, the existing Hive configuration render/restart step still runs.

The StarRocks RustFS secret is provided to the provisioner as a file-backed Compose secret. The keytab is written to the existing protected host keytabs directory. The future StarRocks runtime must consume these credential files read-only; its service and mount configuration are added in Unit 2.

## Run the TPCH workload

After identity provisioning, run the optional ETL:

```bash
./scripts/run-tpch-workload.sh
```

The workload generates scale-factor-1 input files under `.runtime/workload/tpch-data` and runs Spark as `write-service-account`. It creates or validates the eight TPCH tables in `databaseA` and `databaseB`. Existing schema or row-count conflicts stop the affected run without replacing the table. A redacted run manifest is written to `.runtime/workload/results/`.

## Start StarRocks

StarRocks is opt-in and does not start with the default platform stack. Provision its keytab and RustFS identity first with `./scripts/provision-identities.sh`, then start the FE and BE:

```bash
./scripts/start-starrocks.sh
docker compose --profile starrocks ps
docker compose --profile starrocks logs -f starrocks-fe starrocks-be
```

The startup wrapper builds only the local StarRocks runtime images, requires the existing KDC container to be healthy, checks both StarRocks volumes read-only, then starts FE followed by BE. It runs a new paired-state preflight on each invocation. A failed preflight container is preserved for inspection; a successful previous preflight is removed before the next check. After FE/BE start, it runs the secret-exposure canary against the current FE image/configuration, then registers and verifies the BE through the host SQL client, using the protected root password file when bootstrap has already secured root. The wrapper does not start/stop shared platform services or remove volumes.

The FE UI is at <http://127.0.0.1:8030>; the SQL endpoint is `127.0.0.1:9030`. Only these FE ports are published, and both bind to loopback. BE and coordination ports remain internal to `iceberg_net`.

`docker compose --profile starrocks ps` should show both FE and BE healthy. FE health uses its HTTP health endpoint because the root SQL account is password-protected after bootstrap. The project mounts minimal credential-free Hadoop/Hive Kerberos settings to enable SASL with the existing Hive service principal; it does not mount the full Hive configuration. Health indicates process/service readiness; catalog discovery and data access still require the Unit 3 canary/bootstrap and query checks.

Each node obtains a Kerberos ticket before starting and refreshes it hourly. Ticket caches live in separate memory-backed filesystems. Refresh failures emit a redacted status while the current ticket remains valid. Logs are available through Compose. Stop StarRocks without removing its state with:

```bash
docker compose --profile starrocks stop starrocks-be starrocks-fe
```

To restart after a stop, run `./scripts/start-starrocks.sh` again. It repeats the paired-state check before starting FE and BE in order.

FE metadata and BE storage use separate named volumes and survive stops/restarts. The preflight permits both volumes empty or recognized paired FE/BE state; one-sided, unreadable, or unknown contents fail closed. Inspect preserved preflight logs with `docker logs iceberg-poc-starrocks-preflight` and resolve the state manually before retrying. Do not delete or reset either volume as a routine recovery step.

Local verification on 2026-10-24, with cached images and existing paired state, reached FE healthy about 70 seconds after its container start and BE healthy about 56 seconds after its start (about 75 seconds from FE start until BE health). On 2026-10-25, a read-only TPC-H Q1 query against scale-factor-1 `databaseA.lineitem` completed as `user_b` in 3.1 seconds. One-second resource sampling observed FE at 855 MiB and BE at 486 MiB, with BE briefly reaching about 97% CPU. The query also passed with temporary limits of 2 CPUs and 2 GiB memory on each StarRocks node; treat these as the lowest tested limits for this one-query profile, not absolute minimums. The full stack was running on a Docker allocation of 6 CPUs and 15.6 GiB. Current FE/BE images are 2.79/3.82 GB and their volumes use 13.99/9.287 MB. Reserve at least 10 GB incremental Docker storage for StarRocks images and node state, excluding shared platform images and future warehouse growth. Host disk showed 217 GiB free, while Docker's own disk quota was not measured. Measure storage growth and the intended ETL/concurrency before reducing resources; lower limits have not been validated.

## Configure StarRocks SQL access and the Iceberg catalog

Install a MySQL-protocol-compatible `mysql` CLI on the host and ensure it is available on `PATH`. The scripts do not add a client package or service to Compose. Start StarRocks and complete the separate non-secret diagnostics canary before applying any RustFS or SQL-account credentials:

```bash
./scripts/verify-starrocks-sql-secret-safety.sh
./scripts/bootstrap-starrocks-sql.sh
```

The canary creates uniquely named disposable StarRocks user/catalog objects with non-secret marker values, scans FE output, configured FE log directories and query profile history, and removes only its own successfully created objects. It writes a pass marker under ignored `.runtime/state/` only after all inspections and cleanup succeed. The marker is tied to the current FE image, `fe.conf`, and dynamic FE logging configuration. If it cannot inspect a required surface, finds marker exposure, or cleanup fails, it exits without a pass marker. Do not clear FE logs or delete unrelated objects to make it pass. Resolve the cause or revisit the approved secret-handling requirement/design before proceeding.

Bootstrap refuses to send real credential-bearing SQL unless that marker matches the current FE image and configuration. It reads the StarRocks RustFS secret from `.runtime/credentials/rustfs-starrocks-secret-key` and preserves that file. Missing SQL password files are generated only when absent under `.runtime/credentials/` with mode `0600`; directory mode is `0700`. New files are `starrocks-root-password`, `starrocks-admin-password`, `starrocks-user-a-password`, `starrocks-user-b-password`, and `starrocks-writer-password`. Existing file contents are never rotated or overwritten. The MySQL client receives SQL on stdin; its authentication option file is private and temporary, and client/server output is suppressed except for redacted status.

The workflow uses an owner-only lock at `.runtime/state/starrocks-sql.lock`. If a run is active, it exits without mutation. If the lock remains after an interrupted process, confirm no workflow is running, then remove that lock manually before retrying. The scripts may clean only their own private temporary client-input files after lock acquisition. They do not retry automatically or roll back completed additive changes.

The registered StarRocks catalog name is `iceberg`, backed by Hive Metastore `hive-metastore:9083` and RustFS `http://object-store:9000`. The SQL access matrix is:

| StarRocks SQL identity | `databaseA` | `databaseB` | Administration |
|---|---|---|---|
| `user_a` | Read | Denied | None |
| `user_b` | Read | Read | None |
| `write_service_account` | Read and DML on existing tables | Read and DML on existing tables | None |
| `admin` | Full access | Full access | Full StarRocks administration |

The bootstrap checks existing state before applying grants. Credential drift, unrecognized/broader privileges, or conflicting catalog state stops with a redacted error and preserves existing state. A bootstrap success is not a substitute for Build and Test: query/write compatibility, least-privilege allow/deny behavior, and actual log-history exposure still require integrated verification.

## JupyterHub

JupyterHub is available at <http://127.0.0.1:8008> and uses DummyAuthenticator for this development PoC. Usernames are labels, not verified human identities. Each user server runs in an isolated non-root container with its own persistent workspace and matching Kerberos/RustFS identity files. Keep the Hub bound to localhost.

Open the read-only example `/opt/jupyter-examples/spark-authz.py` from the notebook file browser to query the Hive catalog. The Hub and single-user images are built by `scripts/start.sh`.

## Stop and local state cleanup

Stop containers while preserving named volumes and local credentials:

```bash
./scripts/stop.sh
```

During migration from an existing installation, run `scripts/clean.sh` while the KDC is running, before `scripts/stop.sh`. It removes only leftover Dremio-specific local runtime state, requires typing `REMOVE DREMIO STATE`, and verifies the Compose project/container/volume before removal. It does not reset Hive metadata, the KDC database, RustFS objects, TPCH data/results, or notebook workspaces. It is not a general stack reset command.

## Scope

This repository is a local proof of concept, not a production authentication or deployment design. Airflow and Jenkins orchestration are not included.
