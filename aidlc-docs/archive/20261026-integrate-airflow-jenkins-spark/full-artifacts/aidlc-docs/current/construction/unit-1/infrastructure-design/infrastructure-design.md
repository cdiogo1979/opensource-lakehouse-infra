# Infrastructure Design — Unit 1 Spark Writer Runtime

## Purpose and Deployment Scope

Configure the existing local Docker Compose Spark service to maintain the shared writer Kerberos identity and RustFS writer credentials, and provide a worker-only mode for Airflow-created ephemeral worker containers. Keep the upstream `tabulario/spark-iceberg:3.5.5_1.8.1` base image pinned by digest, the existing long-lived master/worker/history service, notebook endpoint, `iceberg_net`, loopback-only host ports, and current long-lived service sizing. A local derived Spark image adds Debian `krb5-user`, because the pinned upstream image does not contain `kinit` or `klist`; no additional runtime package or long-lived Compose service is introduced. Per-run worker containers use this local image, their own private credential caches, and the same read-only writer credential files. They register with the shared master and are not guaranteed exclusive executor placement.

## Compose Service Mapping

| Concern | Infrastructure mapping |
|---|---|
| Compute | Existing `spark` Compose service; locally built from the pinned Spark 3.5.5 base digest with Debian `krb5-user` |
| Lifecycle control | Existing mounted Bash entrypoint, adapted to supervise the ticket lifecycle, Spark daemons, and notebook child process |
| Worker-only mode | Same derived image and writer lifecycle, invoked with a worker-only role to acquire a private TGT, start one worker, report readiness/registration, and stop cleanly when its run container is removed |
| Kerberos configuration | Existing read-only `/etc/krb5.conf` mount plus KDC healthy startup dependency |
| Writer principal | Existing `write-service-account@LAKEHOUSE.LOCAL` and host keytab file |
| Keytab | Read-only bind mount from `.runtime/credentials/keytabs/write-service-account.keytab` to `/run/credentials/write-service-account.keytab` |
| RustFS writer identity | Existing file-backed Compose secrets `rustfs-writer-access-key` and `rustfs-writer-secret-key`, mounted read-only at `/run/secrets/rustfs-writer-access-key` and `/run/secrets/rustfs-writer-secret-key` |
| TGT cache | Private `/run/krb5` tmpfs, 16 MiB, mode `0700`; cache file mode `0600`; no named volume or sharing with Jupyter/Airflow run caches |
| Catalog/object storage | Existing `hive-metastore` and `object-store` service DNS endpoints and network |
| Network | Existing `iceberg_net`; advertise Spark master as `spark` and use `spark://spark:7077` internally |
| Host access | Preserve `127.0.0.1` bindings for notebook UI (`8082`) and Spark master (`7077`) |
| Health | Docker health check validates lifecycle readiness, TGT validity, and Spark worker registration/readiness |
| Logs | Sanitized lifecycle events to container stdout/stderr; no external logging/monitoring service |

## Process and Startup Order

1. Docker Compose waits for the existing object-store health check, successful bucket initialization, healthy Hive Metastore, and healthy KDC.
2. The entrypoint creates the private cache directory, applies restrictive permissions, and configures the explicit service `KRB5CCNAME` and writer keytab path.
3. The lifecycle supervisor obtains and validates the writer TGT. Startup failures remain unhealthy and retry without starting ETL admission.
4. After valid TGT acquisition, the supervisor starts the Spark master advertising `spark`, starts the worker against `spark://spark:7077`, and starts the history server.
5. It waits for worker registration/readiness, then starts or marks the existing notebook process as managed. The service becomes healthy only when the TGT and worker are ready.
6. The supervisor remains the container's controlling process. It handles termination signals, child processes, credential renewal, and worker drain/restart transitions; the notebook remains available on the existing host port while the service is healthy.

The Spark master DNS name is the Compose service name. All in-network clients, including Airflow-created drivers and workers, use `spark://spark:7077`. No additional host interface is exposed. Unit 3 will wire Airflow's per-run driver/worker containers to the same network and endpoint.

## Credential and Cache Filesystem

- Source the existing writer keytab from `.runtime/credentials/keytabs/write-service-account.keytab`; mount it read-only at `/run/credentials/write-service-account.keytab`.
- Use the existing Compose file-backed RustFS writer secrets. Do not copy secret values into `.env`, Spark configuration, image layers, or logs.
- Compose mounts those secrets at `/run/secrets/rustfs-writer-access-key` and `/run/secrets/rustfs-writer-secret-key`. Workload code reads the files and configures the Iceberg S3 client; secret values must be redacted from Spark configuration views/logs and must not be logged.
- Keep source keytab and RustFS credential files at owner-only host mode `0600`, consistent with the approved NFR. Provisioning/configuration must fail if the required mode is not met.
- Mount `/run/krb5` as an ephemeral 16 MiB tmpfs with mode `0700`. Set the cache file to `0600`; use `KRB5CCNAME=FILE:/run/krb5/ccache`.
- Do not add a named ticket-cache volume. Do not share this TGT cache with notebooks, Airflow-created drivers, or other services.
- Retain existing named volumes and do not run destructive volume initialization as part of this unit.

## Airflow Worker-Only Container Contract

- Unit 2 creates one worker-only container per active DAG run, with no more than two concurrent runs. The existing long-lived Spark worker remains for notebooks and other clients.
- Reuse the derived Spark image and worker credential lifecycle. Each ephemeral worker has a read-only keytab and RustFS credentials plus a private tmpfs TGT cache; never share caches between the driver, worker, or another run.
- Start the worker only after its own TGT validates; report readiness only after registration with `spark://spark:7077` is confirmed.
- The shared Spark Standalone master may assign executors across all registered workers. The worker container's lifetime is tied to one DAG run, but executor placement is not exclusive.
- Unit 3 supplies the ephemeral worker's Docker network, mounts, dependencies, and health/readiness wiring. Airflow removes it with its paired driver within the approved cleanup deadline.

## Worker Admission, Health, and Recovery

When the lifecycle enters its pre-expiry drain state, the supervisor invokes the Spark base image's `/opt/spark/sbin/decommission-worker.sh`, verifies that the worker process exits after decommission, and leaves existing work to drain. It does not use forced process termination to enforce credential readiness. After fresh TGT validation and worker exit, it restarts/registers the worker; the service remains unhealthy until readiness checks pass.

Configure a Compose health check with a 15-second interval, 5-second timeout, 3 retries, and 60-second start period. A healthy result requires the supervisor's `READY` state, a valid writer TGT, and a registered/ready worker. The health check is an operator signal; graceful Spark worker decommission enforces the admission gate. Build and Test must prove that the script stops new assignments, preserves in-flight work, and permits the worker to rejoin.

Keep diagnostics sanitized: report lifecycle state, principal, ticket validity status, and safe failure category only. Suppress raw Kerberos and credential command output. Do not include keytab contents, RustFS secret values, TGT material, or credential-bearing command output.

## Compose Dependency and Shared-Resource Policy

Spark startup dependencies are:

- `kdc: service_healthy`
- `object-store: service_healthy`
- `create-bucket: service_completed_successfully`
- `hive-metastore: service_healthy`

Compose dependencies gate initial startup only. The lifecycle supervisor handles later KDC outages and recovery. Preserve existing service instances, `iceberg_net`, Spark resource limits, and all persistent data volumes. Give Spark only the writer credentials needed by this service.

## Messaging and Monitoring Applicability

No message broker or queue is introduced. Spark standalone master/worker scheduling is the existing job execution mechanism. Docker health and sanitized container logs are the complete local operator visibility surface for this unit; external monitoring, alerting, and log aggregation are outside scope.

## Open Verification Items

- Confirm Compose applies the desired file-backed secret mount behavior on the target Docker Compose version and host platform.
- Verify the master advertises `spark` and that both worker and remote drivers resolve/connect to it on `iceberg_net`.
- Verify lifecycle signal handling leaves no orphaned Spark/notebook child processes.
- Verify readiness and worker registration checks accurately reflect `READY` versus draining/recovery.
- Exercise the decommission and recovery behavior in Build and Test; script presence alone is not a pass.
- Confirm the local image builds from the pinned upstream digest with `krb5-user` and provides working `kinit`/`klist` commands.
