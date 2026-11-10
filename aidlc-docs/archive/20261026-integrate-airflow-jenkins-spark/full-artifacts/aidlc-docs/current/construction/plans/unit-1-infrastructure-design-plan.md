# Unit 1 Infrastructure Design Plan — Spark Writer Runtime

## Approved Baseline

Unit 1 configures the current Docker Compose Spark service using the pinned `tabulario/spark-iceberg:3.5.5_1.8.1` image. Preserve the local PoC, Spark master/worker/history server, notebook endpoint, current resource sizing, persistent data, existing network, and credential identities. Add the service-side writer keytab and RustFS writer credentials using protected read-only mounts and a private non-persistent TGT cache. The lifecycle supervisor controls worker readiness and graceful decommission; Docker health and sanitized logs report state. No new runtime package, sidecar, queue, production endpoint, or capacity target is in scope.

## Infrastructure Design Checklist

- [x] Map the approved lifecycle and logical components to the existing local Compose service boundary.
- [x] Define the entrypoint/process arrangement for Kerberos lifecycle, Spark daemons, and the existing notebook process.
- [x] Define credential file and private ticket-cache mounts, ownership/modes, persistence, and Compose secret handling.
- [x] Define Spark master advertised hostname, worker and driver connectivity, and host port exposure.
- [x] Define Docker health-check command, timing, startup dependencies, and sanitized logging.
- [x] Assess deployment, compute, storage, messaging, networking, monitoring, and shared-infrastructure categories; document non-applicable messaging services.
- [x] Generate `aidlc-docs/current/construction/unit-1/infrastructure-design/infrastructure-design.md` and `deployment-architecture.md`.
- [x] Present the infrastructure design for explicit approval before Unit 1 Code Generation.

## Infrastructure Design Questions

Please fill each `[Answer]:` tag. The default answers preserve the approved local Compose scope; choose X if a different deployment target or behavior is intended.

### Question 1 — Deployment environment

Which deployment environment should Unit 1 target?

A) Keep this as the existing local Docker Compose PoC. Do not add cloud/on-prem production infrastructure or deployment profiles in this unit.

B) Add a second named environment/profile (describe its target and differences after `[Answer]:`).

X) Other (describe the deployment target after `[Answer]:`).

[Answer]:A

### Question 2 — Compute and process topology

The existing `spark` service starts the master, worker, history server, and a notebook in one container. How should the supervisor integrate with this topology?

A) Keep the single existing Spark service and notebook endpoint. Adapt the entrypoint to supervise the lifecycle and run the notebook as a managed child process; preserve the current master, worker, history-server, and host-port roles.

B) Split the notebook into a separate Compose service while keeping the Spark master, worker, and history server together.

X) Other (describe the process layout after `[Answer]:`).

[Answer]:A

### Question 3 — Credential and cache storage

How should Compose provide the writer credentials and service TGT cache?

A) Bind-mount `.runtime/credentials/keytabs/write-service-account.keytab` read-only at `/run/credentials/write-service-account.keytab`; use the existing file-backed `rustfs-writer-access-key` and `rustfs-writer-secret-key` Compose secrets read-only; mount `/run/krb5` as a private 16 MiB tmpfs with mode `0700`. Do not persist or share the cache.

B) Store the TGT cache in a named volume so it survives container recreation.

X) Other (describe source paths, mount modes, cache location, and persistence after `[Answer]:`).

[Answer]:A

### Question 4 — Spark network identity and endpoint

What address should the master advertise to workers and remote Spark drivers on `iceberg_net`?

A) Use the Compose service DNS name `spark` consistently for the master, worker, and remote drivers (`spark://spark:7077`). Keep the current host publication bound to `127.0.0.1`; do not expose the master to other host interfaces.

B) Retain `spark-iceberg` as the advertised hostname and add an explicit network alias for it.

X) Other (describe the advertised endpoint and host exposure after `[Answer]:`).

[Answer]:A

### Question 5 — Monitoring and health-check infrastructure

How should Compose report startup, credential, worker, and recovery readiness?

A) Add a Docker health check that requires both valid lifecycle state/TGT and a ready registered worker. Use a 15-second interval, 5-second timeout, 3 retries, and 60-second start period; keep sanitized diagnostics on container stdout/stderr and add no external monitoring service.

B) Report process health only; leave credential and worker readiness to log review.

X) Other (describe health semantics, timing, and logging after `[Answer]:`).

[Answer]:A

### Question 6 — Service startup dependencies

Which Compose startup dependencies should gate Spark initialization?

A) Retain the existing healthy object-store, successful bucket-init, and healthy Hive Metastore dependencies; add the KDC healthy dependency. The supervisor handles KDC failure after startup through its retry/recovery lifecycle.

B) Keep the current dependency list and let the supervisor handle all startup ordering, including object-store, bucket, Hive, and KDC readiness.

X) Other (describe startup ordering and post-start failure handling after `[Answer]:`).

[Answer]:A

### Question 7 — Shared infrastructure and resource isolation

How should the Spark service use existing shared platform resources?

A) Retain `iceberg_net`, existing KDC/Hive Metastore/RustFS services and current Spark resource limits. Give the Spark service only its required writer credentials; keep its TGT cache private and ephemeral and do not alter or recreate existing named data volumes.

B) Put Spark on a separate network and introduce separately managed KDC/Hive/RustFS connectivity or service instances.

X) Other (describe resource sharing and isolation after `[Answer]:`).

[Answer]:A

## Category Assessment

- **Deployment environment**: Local Docker Compose is the approved target; no cloud/provider selection is applicable.
- **Compute**: Existing single Spark service and image are retained; the lifecycle supervisor manages Spark daemons and the notebook child.
- **Storage**: The TGT cache is runtime state and must not persist. Keytab and S3 writer credentials remain protected host-backed files mounted read-only.
- **Messaging**: Not applicable. Unit 1 adds no broker, queue, or asynchronous messaging service; Spark standalone master/worker scheduling is the existing execution mechanism.
- **Networking**: Existing `iceberg_net` is retained; `spark` is the advertised internal master hostname and host publication remains loopback-only.
- **Monitoring**: Docker health and sanitized logs are approved; check interval is 15 seconds, timeout 5 seconds, 3 retries, and start period 60 seconds.
- **Shared infrastructure**: Existing KDC, Hive Metastore, RustFS, network, and data volumes are retained; the service TGT cache remains private.

## Approval Gate

After answers are reviewed and ambiguities resolved, generate the Unit 1 infrastructure design artifacts and request explicit approval before Code Generation.

**Status**: Answers A/A/A/A/A/A/A are clear and consistent with the approved designs. Infrastructure design artifacts are generated and awaiting explicit approval.
