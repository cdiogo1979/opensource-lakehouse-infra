# NFR Design Patterns — Unit 1 Spark Writer Runtime

## Scope and Constraints

This design applies to the existing local Spark standalone service based on the pinned `tabulario/spark-iceberg:3.5.5_1.8.1` image. It retains the shared `write-service-account@LAKEHOUSE.LOCAL` identity and separate RustFS writer credentials. Following the user's approval on 2026-10-26, a local image derived from the same upstream digest adds only Debian `krb5-user`, because the base image lacks `kinit` and `klist`. No sidecar, external monitor, additional package, new principal, or production capacity target is introduced.

The running pinned image was inspected read-only: it reports Spark 3.5.5 and contains `/opt/spark/sbin/decommission-worker.sh`. This confirms the candidate admission command exists. Its runtime scheduling/drain behavior still requires Build and Test verification before SWR-NFR-02 is reported as passing.

## Lifecycle Supervisor Pattern

Use one Bash lifecycle supervisor as the Spark service's coordinator for TGT acquisition, validity, renewal, admission state, health, and recovery. Keep the supervisor as the container's controlling process and retain the existing Spark master/history-server responsibilities. Avoid independent renewal and readiness loops that could race or overwrite each other's state.

The supervisor uses explicit states:

| State | Meaning | Worker admission |
|---|---|---|
| `STARTING` | Private cache is prepared; initial TGT acquisition and validation are in progress | Closed; worker is not started |
| `READY` | Valid writer TGT exists and worker registration/readiness checks pass | Open |
| `DRAINING` | Ticket recovery has not succeeded by the pre-expiry safety threshold; graceful decommission is being requested | Closing; decommission request must be confirmed |
| `UNAVAILABLE` | No new ETL work may be assigned; ticket acquisition continues | Closed; worker remains absent/decommissioned |
| `RECOVERING` | A fresh ticket is valid and the worker is restarting/re-registering | Closed until worker checks pass |
| `STOPPING` | Normal service shutdown | Closed |

Only `READY` is healthy. Transitions to healthy require both a valid TGT for the configured principal and a ready, registered Spark worker. Container process liveness alone does not qualify.

## Kerberos Renewal and Recovery Pattern

1. At startup, create the cache directory with mode `0700`, set `KRB5CCNAME` to a service-private `FILE:` cache, and set a restrictive umask. Do not start the worker until initial keytab acquisition and TGT validation succeed.
2. Use the existing keytab and Kerberos client tools. The supervisor examines the TGT end time in a stable locale and begins renewal at least 15 minutes before expiration.
3. Run a single serialized renewal/reacquisition attempt at a time. If renewal fails, acquire a fresh TGT from the same keytab. Bound each Kerberos command so one slow KDC call cannot prevent the next recovery decision; retry at intervals no longer than one minute.
4. Suppress raw Kerberos command output from container logs. Emit only sanitized events such as `ticket_acquired`, `ticket_renewal_failed`, or `ticket_validation_failed`, plus the principal and lifecycle state where useful.
5. If attempts have not restored a valid TGT by a two-minute pre-expiry safety threshold, transition to `DRAINING` and request graceful worker decommission while the existing TGT is still valid. The threshold gives the supervisor time to stop new task assignments before expiry; recovery attempts continue during draining.
6. Confirm the worker has stopped accepting assignments. Do not kill the worker or its executors to enforce the gate. Existing work may continue and may succeed or fail at Hive Metastore/RustFS according to endpoint authentication.
7. Once a fresh TGT validates, remain unavailable until the decommissioned worker exits; then start/register a worker with the refreshed cache. Transition to `READY` only after both ticket and worker readiness checks pass.
8. If startup acquisition fails, remain unhealthy and retry automatically at the approved cadence. Keep ETL admission closed; after acquisition succeeds, start/register the worker and then become healthy.

If decommission cannot be requested or confirmed, keep readiness unhealthy and surface a sanitized failure. Do not substitute a forced worker termination because that would violate the in-flight-work requirement. Treat an unconfirmed admission gate as a failed requirement during Build and Test.

## Readiness and Health Pattern

The Docker health check reads the lifecycle state and checks the current TGT plus Spark worker readiness/registration. It returns healthy only in `READY`; all other states are unhealthy. The health check is an operator signal. Spark worker decommission is the enforcement action that prevents new task assignments.

Health transitions are atomic from the supervisor's perspective: publish `DRAINING` before starting graceful decommission, publish `UNAVAILABLE` after the worker is no longer schedulable, and publish `RECOVERING` before restarting/re-registering it. The worker must not be marked ready during decommission or restart.

## Credential Protection Pattern

- Mount the writer keytab and RustFS writer credential files read-only.
- Keep the service ticket cache in private runtime storage, outside image layers, Git bundles, notebook caches, Airflow driver caches, and persistent lakehouse data volumes.
- Apply the approved target modes: secret files `0600`, cache directory `0700`, cache files `0600`.
- Use an explicit service-local `KRB5CCNAME`; do not inherit a notebook or per-run driver cache.
- Never print keytab contents, RustFS secrets, TGT contents, or raw credential-bearing command output.

## Resilience, Capacity, and Performance

Recovery is local and automatic: single serialized attempts, bounded command execution, one-minute-or-faster retries, and worker re-registration after a valid TGT returns. No external alerting, failover, DR, or uptime target is introduced. Preserve current Spark resource settings and single-service capacity; make no throughput or latency guarantee. Readiness checks must remain lightweight and must not issue catalog or object-store queries.

## Verification Boundary

Infrastructure Design must specify Compose cache/secret mounts, ownership, lifecycle signal handling, health-check wiring, and worker/master registration checks. Build and Test must exercise loss and recovery paths against the pinned image and show that decommission stops new assignments while existing tasks are not deliberately terminated. Merely finding the script in the image is insufficient evidence of runtime conformance.
