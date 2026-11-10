# Unit 1 Infrastructure Design

## Scope and Deployment Target

Deploy the catalog, metastore database, local Kerberos realm, RustFS object service, and bucket setup as one developer-host Docker Compose project. The current development host is arm64. Do not add a cloud/LAN target, message broker, monitoring stack, alerting service, shared infrastructure, service replicas, or administration UI.

The design maps the Unit 1 foundation only. Unit 2 owns cross-component principal and permission provisioning; Unit 3 owns sample ETL and Dremio Space/view creation. Those units consume the contracts below but are not provisioned by this unit's infrastructure artifacts.

## Service and Image Mapping

| Service | Infrastructure selection | Host architecture and status |
|---|---|---|
| Hive Metastore | Apache image `apache/hive:3.1.3`, running the standalone Metastore service with external PostgreSQL. Pin the resolved image digest in implementation. | Apache has declared Hive 3.x EOL; 3.1.3 is archived and receives no upstream releases. The published image currently has linux/amd64 only. On this arm64 host it requires Docker Desktop amd64 emulation. This limitation was explicitly accepted for the local PoC, and is not an acceptable production or security-supported deployment. |
| Metastore PostgreSQL | Official `postgres:16.14` candidate with a dedicated database/user and named metadata volume. | Official image supports arm64. Hive 3.1.3 schema/driver compatibility with this exact server version remains an integration gate; retain the Hive-provided PostgreSQL JDBC driver version compatible with the chosen Hive image or deliberately replace it only after compatibility review. |
| Kerberos KDC | Project-owned small image based on a pinned Debian Bookworm slim image, containing MIT Kerberos KDC/admin packages at pinned package versions. Run `krb5kdc` and `kadmind` for the disposable realm. | Build for linux/arm64 on the developer host. Pin base image digest and package versions in implementation. Keep KDC database and configuration in a named volume; generated principal/keytab artifacts belong in the ignored local runtime credential directory. |
| RustFS | Retain the existing `rustfs/rustfs:1.0.0` version where its registry tag and API behavior are verified. If the exact tag is unavailable, use the matching official `1.0.0-glibc` multi-architecture build only after confirming equivalence. | RustFS publishes 1.0.0 glibc variants for amd64 and arm64. Preserve the existing 1.0.0 baseline; do not silently upgrade. S3 API availability does not prove Hive filesystem authorization. |
| Bucket initializer | One-shot Python/Boto3 initializer on the Compose network, pinned to a Python base and Boto3 dependency. Prefer a small project-owned image or pre-pinned dependency over installing packages on every startup. | Runs ensure-only bucket creation against RustFS. It must not delete objects and should use a bucket-scoped setup credential where RustFS policy semantics permit. |

### Hive 3.1.3 Acceptance of Support and Architecture Limits

The user selected Hive 3.1.3 despite its archived/EOL status and amd64-only image, accepting emulation on this arm64 workstation for the local PoC. The image should be referenced by immutable digest after it is resolved. No claim of active upstream maintenance, native arm64 execution, or production readiness is made. The Apache image tag exists, but is not multi-architecture. Apache's current release information marks the 3.x line EOL, and Apache's metastore documentation identifies external RDBMS persistence and the standalone Metastore service model. [Apache Hive downloads](https://hive.apache.org/downloads.html), [Apache Hive image tags](https://hub.docker.com/r/apache/hive/tags), [Hive 3 Metastore administration](https://hive.apache.org/docs/latest/admin/adminmanual-metastore-3-0-administration/).

The Hive Metastore is persistent and externalized from Derby. Apache recommends explicit schema initialization and verification; do not enable implicit schema mutation to make startup appear successful. Use the pinned Hive image's matching `schematool` to inspect state, initialize only a new empty metadata database, and fail on an incompatible schema. Never automatically upgrade or drop an existing schema. [Hive 3 Metastore administration](https://hive.apache.org/docs/latest/admin/adminmanual-metastore-3-0-administration/).

## Persistence and Data Boundaries

- `metastore-db-data`: PostgreSQL metadata only. PostgreSQL credentials are dedicated to Hive Metastore and do not grant RustFS object access.
- `rustfs-data`: RustFS bucket/object data. Keep object data separate from Hive metadata.
- `kerberos-kdc-data`: KDC database and realm state. Preserve it across stop/start; reset only through the explicit destructive reset procedure.
- Existing Dremio data volume remains owned by the Dremio unit and is not migrated or deleted here.
- Bucket creation is ensure-only. Existing bucket objects and all named volumes survive normal stop/start and failed initialization.
- Full reset removes named volumes only through an explicit operator command, documented separately from stop-only behavior.

The official PostgreSQL image currently publishes pinned 16.x tags for amd64 and arm64. Version 16.14 is a conservative candidate rather than a proven Hive pairing; exact server/driver/schema compatibility is verified during implementation and manual acceptance. [Official PostgreSQL image and tags](https://hub.docker.com/_/postgres).

## Identity, Credentials, and Configuration Files

- Store generated passwords, RustFS access keys, Kerberos master/bootstrap secrets, keytabs, and service credential files under a local ignored directory such as `.runtime/credentials/`. Create it with restrictive host permissions (owner read/write only where the host supports POSIX modes).
- The explicit local bootstrap flow creates required credential files before Compose startup, checks that required files exist and have restrictive permissions, and emits no secret values. Initialization must fail closed when required files are missing.
- Mount only the exact files consumed by each service, read-only where supported. Keep RustFS S3 credentials, Kerberos principals/keytabs, PostgreSQL credentials, and Dremio credentials distinct.
- Do not put generated secrets in tracked `.env` files, image layers, source defaults, command-line output, or logs. The current workspace `.env` contains fixed S3 access values and no `.gitignore` was found at the project root; implementation must add ignore rules and replace those values with local runtime inputs before treating the configuration as complete.
- Runtime service configuration may use non-secret environment variables. Where a component only accepts a password-valued environment variable, supply it from a protected runtime file through a wrapper that does not echo the value, or document the component-specific limitation and ensure process/log output does not reveal it.
- The Kerberos KDC admin/bootstrap identity is distinct from the platform `admin` application principal provisioned in Unit 2. They are not one shared identity or password.

## Network and Host Exposure

- Use one private Compose bridge network with service DNS names for KDC, PostgreSQL, Hive Metastore, RustFS, Spark, Dremio, and initialization clients.
- Keep Hive Metastore Thrift (9083), PostgreSQL (5432), KDC (88 TCP/UDP), and kadmind (749 TCP) internal to the Compose network unless a documented host-side developer tool requires publication. No broad host binding is allowed.
- Existing developer-facing ports such as Dremio UI/JDBC/Flight, RustFS S3/console, and Spark UI may retain their configured host port numbers, but every host mapping must bind explicitly to `127.0.0.1`. Remove any host-published port that is not needed for an operator workflow.
- No gateway, reverse proxy, load balancer, LAN binding, or external network is introduced.

## Readiness and Initialization

Use Docker Compose healthchecks and dependency conditions for service ordering. Compose supports `service_healthy` and `service_completed_successfully`; a dependency's running state alone does not mean it is ready. [Docker Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/).

| Component/step | Readiness contract | Downstream gate |
|---|---|---|
| PostgreSQL | `pg_isready` succeeds for the dedicated metastore database/user. | Schema inspection/initialization may start. |
| KDC | KDC process is running and local/network Kerberos authentication check succeeds after realm bootstrap. | Principal/keytab bootstrap and Kerberos-enabled Hive configuration may proceed. |
| Hive schema initializer | Successful schema inspection; initialize only an empty database using the Hive 3.1.3 schema tool; report pre-existing compatible schema. | Hive Metastore may start only after successful completion. |
| RustFS | Native readiness endpoint succeeds. | Bucket ensure may run. |
| Bucket initializer | RustFS bucket is present or created; no destructive object operation. | Storage consumers may proceed. |
| Hive Metastore | Thrift endpoint responds to a catalog client probe after schema, KDC service identity and configuration are available. | Identity provisioning, ETL, and query services may proceed under their unit-specific gates. |

Use bounded retries only for dependency availability and idempotent ensure operations. Authentication, configuration, authorization, schema mismatch, and unsupported behavior fail promptly with an actionable redacted diagnostic. A failed one-shot initializer keeps overall readiness false. Compose healthchecks establish service availability only; they do not prove per-user authorization or effective identity propagation.

## Local Resource Assumptions

No performance SLA or fixed CPU/RAM cap is introduced. Document Docker Desktop allocation adequate for the existing Dremio, Spark, RustFS, Hive, PostgreSQL, and KDC services. Hive's amd64 emulation on arm64 and Dremio/Spark memory demands are expected to dominate the local resource footprint. Startup/query speed is best-effort; correctness and observable readiness are the acceptance priorities.

## Category Decisions

- **Messaging**: Not applicable; no event/message flow is in Unit 1. Compose dependencies coordinate startup only.
- **Monitoring**: No added stack, alerting, or metrics service. Use Compose health/status and actionable local logs.
- **Shared infrastructure**: Not applicable; no multiple projects, tenants, or environments share services or volumes.
- **Compute scaling**: One local instance per service; no replicas or load balancing.

## Open Compatibility and Security Gates

1. Apache Hive 3.1.3 EOL/amd64 emulation is accepted for this PoC, but the exact image startup interface, Java/Hadoop dependency set, Kerberos SASL configuration, and Hive schema behavior still require validation.
2. PostgreSQL 16.14, Hive 3.1.3's JDBC driver, Hive schema creation, and persistent-volume behavior must be validated together before implementation is treated as complete.
3. Spark 3.5.5 and Iceberg 1.8.1 Hive client compatibility must be checked against the selected Metastore client JAR and Kerberos properties.
4. Dremio 26.0.5 Hive plugin configuration and Kerberos effective-user propagation remain unverified.
5. Hive storage-based authorization over RustFS and effective-user outcomes for both Dremio and Spark remain explicit feasibility gates. No storage permission model is certified by this infrastructure mapping.
6. RustFS `1.0.0` versus `1.0.0-glibc` tag/digest availability and matching API behavior must be confirmed before changing the Compose pin.
7. Runtime credentials must be moved out of the current fixed `.env` values into ignored local runtime files before implementation completion.

If a gate requires changing the approved Hive major version, Spark/Dremio pin, authorization architecture, or user access criteria, stop and present the smallest proposed change for approval.

## Implementation and Verification Boundary

This is an infrastructure design artifact only. It does not modify Compose, build images, start containers, run tests, or claim successful integration. Code Generation must pin image digests and package versions, implement read-only credential mounts, and document manual verification. Build/acceptance execution remains governed by the later workflow gate.
