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

After starting the stack, provision the Hive service and workload identities:

```bash
./scripts/provision-identities.sh
```

The provisioner creates or verifies the Kerberos principals `hive/hive-metastore`, `admin`, `write-service-account`, `user_a`, and `user_b` in the configured realm. It also provisions scoped RustFS identities and PostgreSQL roles. It does not rotate existing credentials unless the explicit RustFS writer rotation option is selected.

## Run the TPCH workload

After identity provisioning, run the optional ETL:

```bash
./scripts/run-tpch-workload.sh
```

The workload generates scale-factor-1 input files under `.runtime/workload/tpch-data` and runs Spark as `write-service-account`. It creates or validates the eight TPCH tables in `databaseA` and `databaseB`. Existing schema or row-count conflicts stop the affected run without replacing the table. A redacted run manifest is written to `.runtime/workload/results/`.

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
