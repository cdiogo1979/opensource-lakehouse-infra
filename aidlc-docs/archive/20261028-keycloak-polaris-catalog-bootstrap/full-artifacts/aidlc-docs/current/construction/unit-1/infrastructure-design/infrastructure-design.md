# U1 Infrastructure Design — Runtime Composition and Legacy Removal

## Scope

This design defines the supported local runtime for the platform-admin bootstrap journey: Keycloak, its dedicated PostgreSQL database, Apache Polaris with its own PostgreSQL metadata database, and RustFS. The default Compose project is `lakehouse-local`. Bootstrap CLI and Spark are one-shot/on-demand clients owned by U4. Catalogs, users/groups, buckets, RustFS policies, and smoke tables are provisioned in later units, not by provider startup.

No migration is performed. New providers use new state. Normal start, stop, restart, bootstrap, and failure recovery preserve all volumes and RustFS objects.

## Provider and image compatibility set

Use these release tags as the design baseline; implementation must resolve and record immutable multi-architecture digests for the selected platform before acceptance. Digest locking is architecture-sensitive, so retain the registry manifest/index digest (or record per-architecture child digests) rather than copying the legacy RustFS digest.

| Component | Design image/version | Design notes |
|---|---|---|
| Keycloak | `quay.io/keycloak/keycloak:26.8.1` | Official current download; use PostgreSQL production database mode and enable health endpoints. Use HTTP only on the private local network and loopback-published host port. Do not use `start-dev` as the default service mode. |
| Polaris server | `apache/polaris:1.8.0` | Official Apache release image; supports both `linux/amd64` and `linux/arm64`. Configure the relational JDBC metastore against Polaris-owned PostgreSQL. |
| PostgreSQL | `postgres:17.11-alpine3.24` for both independent database services | Same pinned official image, separate containers, database users, secret files, named volumes, and databases. Confirm the selected tag is available for the target architecture when locking digests. |
| RustFS | `rustfs/rustfs:1.0.4` | Replace legacy 1.0.0 image pin after review; 1.0.4 is the current release and includes an upstream trust-store security patch. Official docs support file-based root credential injection. |

Versions establish a documented starting compatibility set, not a claim that the integrated bootstrap has already been tested. U1 Build and Test will validate clean startup and health; Spark/Iceberg/RustFS interoperability is verified in U4. Image digests and resulting manifest details belong in the checked-in compatibility record and Compose file during Code Generation.

References: [Keycloak downloads](https://www.keycloak.org/downloads), [Keycloak containers](https://www.keycloak.org/server/containers), [Polaris 1.8.0 Docker image](https://hub.docker.com/r/apache/polaris/tags), [Polaris relational JDBC metastore](https://polaris.apache.org/releases/1.8.0/metastores/relational-jdbc/), [PostgreSQL official image tags](https://hub.docker.com/_/postgres/tags), [RustFS 1.0.4 release](https://github.com/rustfs/rustfs/releases), [RustFS credentials](https://docs.rustfs.com/en/operations/credentials).

## Compose service inventory

The primary `docker-compose.yml` contains only these long-running providers and prerequisites:

| Compose service | Image | State / dependency | Readiness |
|---|---|---|---|
| `keycloak-db` | PostgreSQL 17.11 | `keycloak-db-data`; `keycloak` database and dedicated user; root password from a protected file | `pg_isready` against its own database |
| `keycloak` | Keycloak 26.8.1 | Depends on healthy `keycloak-db`; no legacy identity state is mounted; Keycloak JDBC password from a protected, read-only config/secret source | Keycloak readiness endpoint on management port 9000, private to Compose |
| `polaris-db` | PostgreSQL 17.11 | `polaris-db-data`; `polaris` database and dedicated user; schema `polaris_schema`; separate protected credentials | `pg_isready` against its own database; schema initialization must complete before Polaris starts |
| `polaris` | Polaris 1.8.0 | Depends on healthy `polaris-db` and successful schema initialization; Polaris JDBC config/password is supplied via read-only file; no Hive state | Polaris management readiness endpoint on port 8182, private to Compose |
| `rustfs` | RustFS 1.0.4 | New `rustfs-data` named volume; root access/secret keys use `_FILE` path variables and read-only secret files | `GET /health/ready` on port 9000 |

The PostgreSQL schema initializer is a short-lived, non-default helper run before Polaris on the first clean setup. It creates only `polaris_schema` in the new Polaris database and must be safe to rerun. Polaris 1.8.0 requires that schema to exist before its admin-tool bootstrap; Polaris does not create it automatically. Keycloak’s database is initialized by its supported PostgreSQL configuration. No PostgreSQL host ports are published.

Polaris Admin Tool and all data-product bootstrap steps are explicit one-shot commands in later units. They are not attached to normal `docker compose up` and do not create catalog or object-store data implicitly.

## Network, host ports, and issuer boundary

- Create one private Compose network, `core`, with no externally attached network.
- Publish only these operator endpoints, all on `127.0.0.1` with configurable host ports:
  - Keycloak HTTP: host `${KEYCLOAK_HOST_PORT:-8080}` to container `8080`.
  - Polaris catalog/management API: host `${POLARIS_HOST_PORT:-8181}` to container `8181`.
  - RustFS S3 API: host `${RUSTFS_S3_HOST_PORT:-9000}` to container `9000`.
  - RustFS console: host `${RUSTFS_CONSOLE_HOST_PORT:-9001}` to container `9001`.
- Keep PostgreSQL ports and Polaris management port `8182` unpublished.
- Service-to-service connections use Compose DNS names on `core`; HTTP stays within loopback or this private local network.
- U2 must select one Keycloak issuer URL that is reachable and identical for the browser, Polaris, and host-side clients. The host-versus-container issuer resolution is an explicit integration contract, not inferred from the port mapping.

## Persistent state and secrets

Compose project name: `lakehouse-local`. Do not set `container_name`. Compose prefixes network and named-volume resources. New named volumes are `keycloak-db-data`, `polaris-db-data`, and `rustfs-data`; never bind these services to the old Hive, FreeIPA, KDC, or RustFS volumes.

The runtime keeps authoritative secret/config files under `.runtime/credentials/`, ignored by Git, with owner-only permissions. Because local Compose file secrets are bind mounts and preserve host ownership/mode, the non-root Keycloak, Polaris, and RustFS images cannot read a host-owned `0600` file. The operator therefore stages service-specific read-only copies under `.runtime/container-mounts/`; the host directory remains `0700`, and only the one service granted each file can read its `0644` mounted copy. Polaris `pgpass` remains mode `0600` for libpq. Secret values are not placed in Compose interpolation or logged. RustFS supports `RUSTFS_ACCESS_KEY_FILE` and `RUSTFS_SECRET_KEY_FILE`. PostgreSQL supports `POSTGRES_PASSWORD_FILE`. Keycloak and Polaris receive their database password through their protected read-only configuration file (`keycloak.conf` and Polaris `application.properties`) rather than a Compose environment value.

Per the resolved Question 10, remove all existing credential/secret files in this project copy’s `.runtime/credentials/` when implementing the new secret set, then generate only files required by the new runtime. Do not remove other `.runtime/` content, Docker volumes, or RustFS objects. Inspect filenames only and never print secret contents. No deletion occurs as part of this design artifact generation.

## Startup, readiness, recovery, and operator commands

Replace the keytab-dependent `scripts/start.sh` with `scripts/lakehouse.sh` subcommands `start`, `status`, and `stop`:

1. `start` validates Docker Compose V2, generates only missing protected secret files (never overwrites existing required secrets), then starts the five core services. It performs the Polaris schema initialization prerequisite once the DB is healthy, then waits for each provider independently.
2. Readiness is bounded by `STARTUP_TIMEOUT_SECONDS` (default 600). Report `starting`, `ready`, `unavailable`, or `stopped` per provider and identify dependencies still blocking use. A live but unhealthy service is marked unavailable and is not automatically restarted by a watchdog.
3. Configure Compose restart handling for process exits with at most three retries; restarting a failed provider must not restart healthy dependencies or erase state. Exhaustion or timeout returns nonzero with a redacted actionable report.
4. `status` reports Compose and provider readiness without printing secret values. `stop` stops the project and preserves all named volumes.
5. Document offline, service-stopped backup and restore for each DB volume and RustFS data. Do not add scheduled backup services.

Exact retry/backoff syntax and healthcheck commands must be verified against Docker Compose V2 at implementation time. Health checks observe service state only; they must not implement a separate restart watchdog.

## Default and deferred Compose boundaries

- Default project startup is only Keycloak, its PostgreSQL, Polaris, its PostgreSQL, and RustFS.
- A separate `docker-compose.deferred.yml` is opt-in only and is not included by the core operator script. It may describe Airflow, JupyterHub, Jenkins, and StarRocks only with an explicit unsupported-pending-migration label; it must not declare or depend on FreeIPA, Hive Metastore, Kerberos, or KDC. Do not claim those deferred services work until migrated and tested.
- Remove FreeIPA, Hive schema initialization/metastore, KDC, keytabs, and their active startup/configuration references from the supported Compose graph. Historical AI-DLC archive content is not runtime configuration.
- Legacy cleanup remains a separately invoked, exact-name guarded operation. It rejects RustFS and unrelated volumes. The normal `start`, `stop`, and bootstrap paths never call cleanup.

## Requirements trace

| Approved design / requirement | Infrastructure decision |
|---|---|
| Single-machine local Compose, one workload at a time | Project `lakehouse-local`; core providers only; CLI/Spark on demand |
| Bounded startup and per-provider status | `lakehouse.sh` and 600-second configurable coordinator |
| Bounded process-exit retries, no unhealthy watchdog | At most three retries; health checks only observe |
| Persistent, separately owned state | Independent Keycloak DB, Polaris DB, RustFS data volume |
| Loopback-only host surfaces | Four configurable loopback publications; no DB ports |
| Protected secrets and redacted diagnostics | `.runtime/credentials/`, owner-only, read-only mounts; no secret interpolation/logging |
| No legacy dependencies or implicit deletion | New volumes and explicit legacy cleanup only |
| Pinned compatible releases | Version baseline and immutable digest capture required before acceptance |

## Out of scope

This unit does not implement realm/client/groups, Polaris principals/roles/catalogs, buckets/policies, data-product bootstrap, Spark image/job, user access tests, external TLS, production multi-node deployment, or migration of Airflow/JupyterHub/Jenkins/StarRocks. These belong to later units or separate work.
