# NFR Requirements — Unit 3 Platform Compose Integration

## Scope and Quality Profile

These requirements apply to the local Docker Compose integration of Airflow 3, its dedicated PostgreSQL service, Git DAG Bundle storage, and Jenkins. They supplement the approved Unit 3 Functional Design and must preserve the existing Hive/RustFS/Spark lakehouse state.

The integration targets a single-host PoC. It has no HA, uptime, host-loss recovery, backup/restore, throughput, latency, or capacity guarantee. The Unit 2 limit of at most two active DAG runs, five-minute driver/worker readiness, and 60-second paired cleanup remains authoritative for workload execution.

## Requirements

### U3-NFR-01 — Airflow control-plane startup

- After the dedicated Airflow PostgreSQL reports healthy and `airflow-init` exits successfully, the Airflow API service MUST become healthy within five minutes.
- If the deadline is missed, the Compose health surface MUST report the API service unhealthy and provide sanitized diagnostics for operator investigation. This requirement does not mandate automatic restart or claim recovery.
- Jenkins readiness is independent of Airflow readiness. Jenkins failure MUST NOT be represented as an Airflow startup failure, or vice versa.
- Airflow API health MUST NOT be represented as proof of Git remote access, Bundle resolution, Docker bind-path access, Kerberos readiness, Spark readiness, or workload readiness.

### U3-NFR-02 — Service health probes

- Airflow PostgreSQL, Airflow API, and Jenkins MUST be probed at 10-second intervals, using a five-second timeout, and MUST be marked unhealthy after three consecutive failed probes.
- The Airflow initializer MUST run after Airflow PostgreSQL health and MUST complete successfully before the Airflow application services are considered ready.
- The initializer's successful one-shot completion is a startup dependency, not a recurring health probe.
- Health checks MUST use local service checks and MUST NOT expose credentials in arguments or output.

### U3-NFR-03 — Persistent data behavior

- Airflow metadata MUST survive ordinary container recreation and Compose stop/start through the dedicated Airflow PostgreSQL named volume.
- Jenkins home state MUST survive ordinary container recreation and Compose stop/start through its dedicated named volume.
- This local PoC does not provide or claim backup/restore, host-loss recovery, an RPO, or an RTO.
- Airflow and Jenkins initialization, update, and teardown MUST NOT remove or reset existing lakehouse named volumes or mutate Hive/RustFS data.

### U3-NFR-04 — Bundle revision retention safety

- Bundle revisions referenced by active DAG runs MUST remain available for the full lifetime of those runs.
- Automatic local checkout cleanup MAY remove only inactive revisions older than 30 days.
- A cleanup failure MUST be reported with sanitized diagnostics and MUST NOT block active runs or delete their pinned revision.
- This retention rule applies to runtime checkout storage only; it MUST NOT mutate Git remote references or publish/update Bundles.

### U3-NFR-05 — Deployment secret-file protection

- Required Airflow bootstrap, API, and Fernet secret source files MUST be supplied at deployment time and MUST have host mode `0600` (owner-readable and writable only).
- When secret files are mounted into a container, they MUST be mounted read-only.
- Git credentials MUST be supplied through a protected deployment credential reference when the configured remote requires authentication; they MUST NOT be committed or printed in diagnostics.
- Airflow initialization MUST fail before Airflow services are considered ready if a required bootstrap/API/Fernet secret is missing or unreadable. A public Git remote does not require Git credentials.
- Secret values MUST NOT appear in source control, logs, task output, health-check output, or error messages.

### U3-NFR-06 — Local compute and capacity scope

- Unit 3 MUST preserve the host sizing approach and MUST NOT add fixed per-container CPU or memory limits for the new services.
- No CPU, memory, throughput, latency, or capacity guarantee is made.
- Resource exhaustion that prevents a service from becoming healthy MUST be surfaced through its health state and sanitized logs; it MUST NOT trigger automatic resource escalation.
- The existing Unit 2 maximum of two concurrent DAG runs remains the workload admission limit; Unit 3 does not increase it.

### U3-NFR-07 — Socket and network boundary preservation

- Only the Airflow scheduler among Airflow services and the separately approved Jenkins service MAY receive the Docker Engine socket.
- Airflow API server, DAG processor, triggerer, initializer, and PostgreSQL MUST NOT receive the Docker socket.
- Scheduler-created workload containers MUST use the existing `iceberg-poc-net` network. No new public port is introduced for internal service dependencies.
- The approved all-interface UI bindings remain `8085:8080` for Airflow and `8098:8080` for Jenkins; port `50000` remains unpublished. This local design does not provide TLS termination.

### U3-NFR-08 — Bundle and run isolation

- Every run MUST retain its pinned Bundle revision in read-only form; local cleanup MUST NOT remove or alter a revision used by an active run.
- A missing, unreadable, or mismatched host/container path mapping MUST fail before workload submission and MUST NOT use an inferred fallback path.
- Unit 2's per-run credential/cache isolation and cleanup bounds remain mandatory and MUST NOT be weakened by Compose service health or retention cleanup.

## Verification Targets for Later Build and Test

- Measure Airflow API readiness after PostgreSQL health and initializer completion; confirm the five-minute limit and unhealthy outcome on timeout.
- Confirm PostgreSQL/API/Jenkins probes use the specified interval, timeout, and consecutive-failure threshold.
- Recreate and stop/start Airflow and Jenkins containers and confirm their dedicated named-volume data persists; confirm no existing lakehouse volume is reset.
- Exercise Bundle cleanup with active and inactive revisions, including a revision older than 30 days; confirm active revisions remain and cleanup failures are surfaced safely.
- Confirm required deployment secret files reject missing/unreadable values, have mode `0600`, mount read-only, and never leak values to logs or health checks.
- Inspect service socket/network boundaries and published ports; validate host/container Bundle paths and Docker daemon bind resolution.
- Confirm no fixed CPU/memory limits or unapproved capacity claims are introduced.

## Applicability Notes

- **Availability/recovery**: A single-host local PoC with no HA, backup/restore, RTO, RPO, or host-loss recovery target.
- **Security**: Explicit secret and Docker socket constraints apply even though the Security Baseline extension is disabled.
- **Scalability/performance**: No quantitative performance or capacity claim; two concurrent runs remains the Unit 2 cap.
- **Property-based testing**: Apply only to eligible pure functions and serialization round-trips.
- **Testing stage**: These are future verification targets. No tests were run during NFR Requirements generation.
