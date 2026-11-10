# NFR Requirements — Unit 2 Airflow Bundle Runner

## Scope and Quality Profile

These requirements apply to Airflow's Git Bundle run lifecycle and its Spark driver/worker containers in the local Docker Compose PoC. Each active DAG run owns one ephemeral driver and one worker-only container. The worker registers with the shared Spark Standalone master, while Spark may schedule executors across any registered worker. The existing long-lived Spark service remains available for notebooks and other clients.

The PoC admits at most two active DAG runs; additional runs wait in Airflow's queue. No production SLA, HA, throughput, latency, capacity, RTO/RPO, or disaster-recovery target is specified. Existing long-lived service resource settings remain unchanged. No capacity guarantee is made for the additional per-run containers.

The accepted data access model comprises Hive catalogs `lakehouse_dev`, `lakehouse_uat`, and `lakehouse_prod`; writer/admin access across their catalog and storage boundaries; and equivalent read-only access for `user_a` and `user_b`. UAT/prod Airflow execution remains unconfigured and must fail closed. Multi-catalog support and actual authorization enforcement remain unverified until the integrated Build and Test stage.

## Requirements

### ABR-NFR-01 — Bounded Run Concurrency

- Airflow MUST admit no more than two active DAG runs for this workflow at a time.
- Each admitted run MUST create exactly one ephemeral Spark driver and one worker-only Spark container.
- Additional runs MUST remain queued; they MUST NOT create containers until a concurrency slot is available.
- Each run's worker MUST be registered with the shared Spark Standalone master, but the design MUST NOT claim exclusive driver-to-worker or application-to-worker placement. Spark MAY schedule executors for a run on any registered worker.
- The long-lived Spark service MUST remain running for notebooks and other clients during run-container startup and cleanup.

### ABR-NFR-02 — Fail-Closed Configuration and Readiness

- Bundle identity, run-pinned revision, environment configuration, workload declarations, and dependency graph MUST be validated before either run container is created.
- Selecting unconfigured UAT or prod MUST fail clearly; it MUST NOT fall back to dev or create any driver/worker container.
- From the time container creation starts, Airflow MUST allow no more than five minutes for both the driver and worker to become ready, checking readiness at least every five seconds.
- Driver readiness MUST include a validated TGT for `write-service-account@LAKEHOUSE.LOCAL` and successful Spark master connectivity needed for submission.
- Worker readiness MUST include its own validated writer TGT, successful worker process startup, and registration with the Spark Standalone master.
- If either container is not ready by the deadline, the run MUST fail and enter paired cleanup. Airflow MUST NOT submit workload code before both readiness conditions pass.

### ABR-NFR-03 — Per-Run Isolation and Bundle Immutability

- Every run MUST use exactly the Git Bundle revision resolved for that run. The driver MUST mount this revision read-only.
- Each driver's and worker's Kerberos cache MUST be private to that container and run. Caches MUST NOT be shared across the pair, between concurrent runs, with the long-lived Spark service, or with notebook containers.
- Writer keytab and RustFS credential files MUST be mounted read-only into each container with restrictive file access. Bundle content and ordinary environment variables MUST NOT contain credential values.
- Run cleanup MUST NOT mutate the pinned Bundle revision, persistent Hive metadata, RustFS warehouse data, existing named volumes, or the long-lived Spark service.

### ABR-NFR-04 — Paired Container Cleanup

- On any terminal outcome, including success, workload failure, cancellation, readiness timeout, or partial container startup, Airflow MUST attempt to stop and remove every container created for that run.
- Airflow MUST attempt graceful shutdown immediately and MUST ensure both the run's driver and worker are removed within 60 seconds of the DAG run reaching a terminal state.
- At run completion, Airflow MUST begin driver shutdown and worker decommission immediately. It MUST wait for executors belonging to other active applications to leave within the same 60-second paired-cleanup deadline; draining MUST NOT extend that deadline.
- If other applications' executors remain at the shared cleanup deadline, Airflow MUST stop and remove the worker to preserve the paired-container cleanup bound. It MUST emit a sanitized `worker_drain_timeout` diagnostic; the remaining executors may be interrupted and another run may retry or fail.
- A drain timeout MUST be reported separately and MUST NOT hide the original workload result or prevent cleanup of the run's driver and worker.
- If a container is already absent, cleanup for that container MUST be treated as successful.
- If either container remains after the 60-second deadline, Airflow MUST report cleanup failure. A cleanup failure MUST NOT hide the original workload or readiness failure.
- Cleanup MUST remove only run-scoped containers and ephemeral credentials/cache state; it MUST NOT remove shared workers, catalogs, tables, object prefixes, or named volumes.

### ABR-NFR-05 — Credential-Safe Observability

- Airflow and container diagnostics MUST identify run ID, bundle revision, environment, phase, and sanitized failure category where available.
- Logs and task outputs MUST NOT include keytab contents, RustFS secret values, Kerberos ticket contents, or credential-bearing command output.
- The run result MUST distinguish configuration validation, driver startup, worker startup/registration, TGT acquisition, Spark submission, workload execution, and cleanup failures without leaking secrets.

### ABR-NFR-06 — Catalog Authorization Verification

- Final integrated Build and Test MUST verify the requested authorization policy for all three catalogs and their object-store prefixes; verifying only one catalog is insufficient.
- For `write-service-account`, verification MUST show successful creation/write of disposable tables and data objects in each catalog and its associated prefix.
- For both `user_a` and `user_b`, verification MUST show successful read of the designated test data in each catalog, failed write attempts, and no access outside the intended read-only catalog/prefix scope.
- StarRocks verification MUST demonstrate query/read use only for normal reader accounts and no reader write path.
- Tests MUST use disposable objects and remove only those test objects. Verification MUST NOT reset volumes or delete pre-existing user data.
- If Hive, Iceberg Spark, StarRocks, or RustFS cannot enforce or expose enough evidence to verify the policy, record the gap and do not mark this NFR as passing.

### ABR-NFR-07 — Multi-Catalog Compatibility Gate

- Before runtime integration is accepted, Build and Test MUST verify Hive 3 initialization and discovery of all three catalogs, Spark Iceberg catalog addressing for each, StarRocks external catalog/query behavior for each, and storage-prefix mapping/authorization.
- The existing single-catalog configuration MUST NOT be treated as evidence that all three catalogs work.
- UAT/prod catalog metadata may exist in the local metastore, but this MUST NOT make their Airflow endpoints runnable or permit fallback to the local dev execution target.
- Any unsupported multi-catalog behavior MUST be returned as a concrete design gap before deployment; the implementation MUST NOT silently map multiple catalog names to one data location.

### ABR-NFR-08 — Performance and Resource Scope

- The integration MUST make no numeric throughput, task-latency, or capacity claim.
- The concurrency cap of two active DAG runs and the five-minute readiness/60-second cleanup bounds are operational limits, not performance guarantees.
- Keep existing long-lived Spark service resource settings. The additional per-run containers MUST use the approved pinned/local Spark image and MUST NOT silently modify the long-lived service sizing.
- Resource exhaustion that prevents readiness or workload execution MUST be reported as a run failure; no automatic resource escalation is in scope.

## Verification Targets for Later Build and Test

- Trigger three DAG runs and verify no more than two run container pairs exist concurrently; the third remains queued until a slot opens.
- Verify each run starts one driver and one worker-only container, each obtains a private valid TGT, and each worker registers with the shared master.
- Verify a run may execute using any registered worker and does not rely on exclusive placement to its per-run worker.
- Verify readiness polls occur at least every five seconds and a missing driver/worker readiness condition fails within five minutes without submission.
- Verify both run containers are removed within 60 seconds after success, workload failure, cancellation, readiness failure, and partial startup.
- Verify a completed run's worker stops receiving new executors, drains executors for other active applications for up to 60 seconds, and is removed on timeout with a sanitized `worker_drain_timeout` diagnostic; verify the original DAG result is preserved.
- Verify Bundle mounts are read-only; keytab/S3 secret mounts are read-only; caches are private; and logs/results contain no credential or ticket material.
- Execute the complete authorization and catalog compatibility matrix required by ABR-NFR-06 and ABR-NFR-07.

## Applicability Notes

- **Scalability/performance**: No SLA or throughput target; only two concurrent DAG runs are admitted.
- **Availability/recovery**: No HA or DR target. Unconfigured environments and unavailable run prerequisites fail closed.
- **Security**: Explicit credential protections apply even though the Security Baseline extension is disabled.
- **Property-based testing**: Apply only to applicable pure functions and serialization round-trips; orchestration/container behavior requires focused integration verification.
- **Testing stage**: The requirements define future verification targets. No tests are run during NFR Requirements planning.
