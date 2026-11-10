# NFR Design Patterns — Unit 2 Airflow Bundle Runner

## Scope and Constraints

This design covers Airflow's run-pinned Git Bundle workflow and per-run Spark containers. Each admitted DAG run creates one driver and one worker-only container. The driver and worker use separate private Kerberos caches and the approved `write-service-account@LAKEHOUSE.LOCAL` keytab plus RustFS writer credentials. At most two DAG runs are active; additional runs queue. Each worker joins the shared Spark Standalone master, which may schedule any application's executors on any registered worker. The existing long-lived Spark service remains available to notebooks and other clients.

No throughput, latency, capacity, availability, HA, or recovery-time promise is introduced. The three-catalog and authorization model remains subject to integrated Build and Test verification.

## Admission and Run Isolation Pattern

1. Resolve and validate the exact Bundle revision, environment, workload graph, and service endpoints before creating either container. Unconfigured UAT/prod selection fails closed.
2. Admit at most two active DAG runs. Queue additional runs before container creation.
3. Derive stable run-specific container names and labels from the Airflow run ID. Create exactly one driver and one worker-only container for an admitted run.
4. Mount the Bundle revision read-only. Mount keytab and RustFS credential files read-only. Create independent owner-only Kerberos caches inside each run container; never share cache paths between driver, worker, runs, long-lived Spark, or notebooks.
5. Do not submit workload code until both containers satisfy readiness. Driver readiness requires a validated writer TGT and Spark master connectivity. Worker readiness requires its own valid TGT, a live worker process, and master registration.
6. Poll both readiness conditions at intervals no longer than five seconds. Fail the run and enter paired cleanup if both are not ready within five minutes of container creation.

## Paired Lifecycle Pattern

The Airflow run coordinator owns the pair's lifecycle and is the only component that creates or removes run containers. Its transitions are:

| State | Required behavior | Transition |
|---|---|---|
| `VALIDATING` | Check immutable bundle revision, environment, workload graph, concurrency slot, and required configuration before container creation | Valid input and slot → `STARTING`; invalid input → `FAILED` without containers; no slot → remain queued |
| `STARTING` | Create driver and worker-only containers with run-specific labels and separate private cache state | Both created → `WAITING_READY`; partial creation failure → `CLEANING` |
| `WAITING_READY` | Poll both TGT/process/master conditions every 5 seconds or sooner | Both ready within 5 minutes → `RUNNING`; failure/deadline → `CLEANING` |
| `RUNNING` | Submit only pinned Bundle workloads; keep pair ownership and run metadata associated with the Airflow run ID | Success, failure, cancellation, or timeout → `CLEANING` |
| `CLEANING` | In parallel, stop the driver and decommission the run worker. Drain foreign executors within the same 60-second paired-cleanup deadline, then stop/remove the worker at that deadline if necessary | Both absent → terminal outcome; removal failure → `CLEANUP_FAILED` |
| `CLEANUP_FAILED` | Report container IDs and sanitized failure categories without replacing the original workload result | Operator-visible failure state |

Container creation/removal operations are idempotent by run ID. Cleanup checks whether each container exists before acting and removes only containers carrying the current run's identity. It does not stop the shared Spark master or long-lived worker and does not delete catalogs, tables, object prefixes, named volumes, or Bundle revisions.

## Shared Worker Drain and Timeout Pattern

Because Spark Standalone may place another application's executors on the run worker, cleanup cannot assume that the worker is used only by its owning DAG.

1. On cleanup, immediately close this run's submission path and request Spark-native worker decommission so the master does not assign new executors to the worker. Confirm the worker is no longer schedulable before starting the drain timer. The exact command and executor behavior must be validated against the pinned Spark image during Build and Test.
2. Observe executor/application occupancy on that worker and wait for executors belonging to other active applications to leave within the same 60-second paired-cleanup deadline. Driver shutdown proceeds in parallel.
3. If the worker drains before the deadline, stop and remove it. If executors remain when the shared deadline expires, stop and remove the worker anyway to honor the paired-container cleanup bound. Emit `worker_drain_timeout` with run ID, worker ID, elapsed time, and affected application/run IDs where observable; do not emit credentials or ticket contents.
4. A timeout may interrupt another application's executors. Spark may retry tasks, and another Airflow run may retry or fail. Report this as a distinct cleanup diagnostic and preserve the original workload outcome.
5. If the worker cannot be confirmed unschedulable, still enforce the bounded cleanup deadline, report the decommission failure, and remove the run-scoped worker at timeout. Do not claim that other applications were protected.

The selected drain bound does not provide strict isolation or guarantee uninterrupted concurrent runs. It reduces avoidable executor loss while preserving a hard cleanup deadline.

## Credential and Diagnostic Pattern

- Each container creates its own owner-only Kerberos cache and uses an explicit `KRB5CCNAME`; the cache is ephemeral and never mounted into shared persistent data.
- Keytab and RustFS credential mounts are read-only. Secret values, ticket contents, and raw credential-bearing command output are never written to logs or task output.
- Diagnostics include run ID, Bundle revision, environment, lifecycle phase, container identity, sanitized failure category, and timing where available.
- Distinguish configuration validation, driver start, worker start/registration, TGT validation, Spark submission, workload execution, drain timeout, and container cleanup failures.
- A cleanup or drain diagnostic must not mask the original workload failure or success result.

## Resilience, Capacity, and Performance

Failures are bounded and fail closed: no workload submission before pair readiness, no fallback from UAT/prod to dev, and no resource escalation. Admission remains capped at two runs. Existing long-lived service sizing is unchanged. The readiness and cleanup limits are operational bounds only; no throughput, latency, or capacity claim is made.

## Verification Boundary

Infrastructure Design must specify the exact worker-only command, private cache mounts, readiness checks, safe container labels, and decommission mechanism. Build and Test must verify that decommission prevents new executor assignments, foreign executors drain when possible, timeout removal occurs within the approved bound, diagnostics are sanitized, and the original DAG outcome remains visible. Test both an idle run worker and a worker still hosting another application's executors. Multi-catalog discovery, storage mapping, and authorization require the separate integrated verification matrix in ABR-NFR-06/07.
