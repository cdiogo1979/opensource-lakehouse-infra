# Technology Stack Decisions — Unit 2 NFR Requirements

## Approved and retained stack

| Area | Decision | Reason / constraint |
|---|---|---|
| Orchestration | Existing Airflow 3 LocalExecutor and Git DAG Bundles | Retains the inspected workflow model and pinned Bundle behavior. |
| Container lifecycle | Airflow scheduler's existing Docker Engine access | Creates one ephemeral driver and one worker-only container per DAG run; no new long-lived orchestrator service. |
| Spark cluster | Existing Spark Standalone master and long-lived worker service | Per-run workers register with the shared master; applications may schedule across any registered worker. |
| Spark container image | Existing local derived Spark image based on the pinned Spark 3.5.5 image with approved `krb5-user` tooling | Reuses the same Spark runtime and Kerberos client support; no new package is approved by this unit. |
| Authentication | Existing `write-service-account@LAKEHOUSE.LOCAL` keytab | No new identity or credential rotation. Driver and worker each obtain their own private run-scoped TGT. |
| Object storage access | Existing file-backed RustFS writer credentials | Read-only file mounts; credentials do not enter bundle content, ordinary environment variables, or logs. |
| Run concurrency | Maximum two active DAG runs; queue additional runs | User-selected PoC limit. It does not imply a capacity guarantee. |
| Driver/worker readiness | Five-minute deadline; poll at least every five seconds | Both TGT/readiness states and worker registration must pass before submission. |
| Cleanup | Stop the driver and decommission the run worker immediately; drain within the shared 60-second paired-cleanup budget, then stop/remove at the deadline | A drain timeout is recorded separately; forced removal may interrupt another application's executors. |
| Catalog model | Three Hive catalogs and separate RustFS warehouse prefixes | User-selected functional target; support across Hive, Iceberg Spark, StarRocks, and RustFS must be verified. |
| Monitoring | Airflow run state and sanitized service/task logs | No external monitoring or alerting service is added. |

## Constraints and open implementation verification

- Reconcile the approved requirements/story/application design with the accepted three-catalog and per-run worker decisions before code generation.
- Verify that the derived Spark image supports both the existing master/worker/notebook command and a worker-only command without changing the pinned Spark version.
- Verify independent credential-cache creation for the driver and each worker, worker registration, readiness, and cleanup through the existing Docker boundary.
- Spark Standalone shared scheduling is intentional; this unit does not add strict per-run executor placement, separate masters, a queue service, or a new scheduler.
- At run cleanup, wait for executors of other applications to leave a decommissioned worker within the same 60-second paired-cleanup budget. On timeout, force stop/remove the run worker and emit a sanitized drain-timeout event; another run may be affected.
- Verify catalogs, permissions, and object-prefix isolation before claiming authorization support. Do not infer those capabilities from current single-catalog configuration.
- Keep the existing long-lived Spark service resources and all persistent lakehouse volumes unchanged. No throughput, latency, or capacity promise is made.

## Rejected for this unit

- A new orchestration service, container platform, Spark cluster manager, or identity provider.
- A per-run Spark master or strict driver-to-worker affinity mechanism.
- Local-only Spark fallback, Bundle mutability, credential values in source/environment, volume resets, or unapproved resource escalation.
