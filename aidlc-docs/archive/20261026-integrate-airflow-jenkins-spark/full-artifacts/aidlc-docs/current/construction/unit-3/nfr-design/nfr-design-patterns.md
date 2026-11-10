# NFR Design Patterns — Unit 3 Platform Compose Integration

## Scope

This design translates U3-NFR-01 through U3-NFR-08 into service-level behavior for the local Compose platform. It does not configure or start services. Existing Unit 2 workload readiness, credential lifecycle, and paired cleanup remain authoritative.

## 1. Dependency-gated startup with bounded health

**Pattern**: Separate dependency readiness, one-shot initialization, and steady-state service health.

1. Airflow PostgreSQL health is checked locally at 10-second intervals with a five-second timeout and three consecutive failures.
2. Airflow initialization starts only after PostgreSQL is healthy. It validates required Airflow secret sources before migration/bootstrap and exits nonzero on missing/unreadable inputs or migration failure.
3. API server and other Airflow application services depend on successful initialization. The API server must become healthy within five minutes after both PostgreSQL health and initializer success.
4. Airflow API and Jenkins are independently checked every 10 seconds, with a five-second timeout and three-failure threshold. Their health outcomes remain independent.
5. A missed API startup deadline produces unhealthy service status and sanitized diagnostic logs. This design does not add automatic restart/recovery semantics.

Health probes test only the local service endpoint/process and must not query external Git, Docker, Kerberos, Spark, Hive, or RustFS dependencies. Those are run-level checks, not control-plane liveness.

## 2. Dedicated persistent-volume lifecycle

**Pattern**: Single-writer ownership and non-destructive service recreation.

- Airflow PostgreSQL owns only its dedicated `airflow-postgres-data` named volume. Jenkins owns only `jenkins-home`. Airflow logs may use their own volume if required by the selected service topology.
- Container recreation and ordinary Compose stop/start preserve these named volume contents. Service initialization must not run destructive database reset/volume cleanup commands.
- Existing lakehouse volumes remain owned by their current services. Unit 3 startup, update, and teardown do not remove or rewrite them.
- No automated backup, restore, host-loss recovery, RPO, or RTO behavior is introduced or claimed.

## 3. Race-safe Bundle revision retention

**Pattern**: Reference-aware mark/check/sweep with fail-safe no-op.

1. A run receives an immutable revision identifier and read-only mount. The revision is treated as active from before the run can launch its workload until its terminal cleanup finishes.
2. A retention candidate must be older than 30 days and inactive according to an authoritative reference source. Active-run references must include queued/starting/running/cleanup states as applicable, so cleanup cannot remove a revision before the Docker bind is established or before terminal cleanup ends.
3. Run creation, Bundle fetch/checkout publication, and retention deletion coordinate through a shared critical section or equivalent atomic protocol visible to every process that can modify checkout state. This prevents a check/delete race with new run pinning or fetch.
4. Cleanup rechecks eligibility under the coordination boundary immediately before deletion. It removes only local checkout revisions; it never updates a Git remote ref or deletes active revisions.
5. If the implementation cannot establish authoritative active references or acquire/hold the coordination boundary, it skips pruning and emits a sanitized cleanup diagnostic. Preserving active run inputs takes precedence over reclaiming disk.
6. Cleanup failures do not block a run or Bundle fetch. They remain observable for operator follow-up.

The concrete Airflow metadata query/API and cross-process coordination mechanism are implementation decisions for Infrastructure Design/Code Generation. Every relevant fetch/run/cleanup actor must honor the same protocol; uncoordinated age-based directory deletion is not acceptable.

## 4. Secret source and consumer identity

**Pattern**: Host-owned secret files with explicit identity mapping and fail-closed startup.

- Required Airflow bootstrap/API/Fernet secret source files are deployment inputs with host mode `0600`; mounts into containers are read-only.
- Git authentication material is required only for remotes that require authentication and is handled as a protected credential reference.
- Before initialization, a validator checks required files exist and are readable inputs. Errors identify missing input category/path without printing values.
- The container UID/GID must be deliberately mapped so the intended process can read its mounted file while host mode remains `0600`. Do not relax host permissions or copy values into image layers/environment to work around ownership mismatch.
- Secret values do not appear in health-check arguments/output, logs, task output, or exception text.
- Writer keytab and RustFS writer credentials stay within the Unit 2 run-container boundary; Unit 3 does not give their values to Airflow control-plane services or Jenkins.

## 5. Docker control and host-path boundary

**Pattern**: Explicit socket allowlist and validated host path mapping.

- Docker socket access is limited to the Airflow scheduler and separately approved Jenkins service. No other Airflow service receives it.
- The scheduler and Docker daemon use host-resolvable Bundle and credential source paths. The configured host/container mapping is validated before a run can mount a pinned revision or credential file.
- Run containers join `iceberg-poc-net`. No new externally published dependency port is added.
- Docker socket access is broad host control. This design records the boundary and does not claim the mount is least privilege or sandboxed.
- Jenkins remains validation-only; its approved socket does not imply permission to deploy, publish, or alter Bundle references.

## 6. Failure classification and operator visibility

**Pattern**: Fail initialization or report health state without hiding root cause or leaking values.

- PostgreSQL failure prevents Airflow initialization. Initializer failure blocks Airflow application readiness.
- API startup deadline breach and steady-state probe failures are surfaced through Compose health and sanitized logs.
- Jenkins health failure remains independent from Airflow health.
- Missing required secret, ownership/read failure, invalid Bundle path, or failed revision-retention safety check is reported by category and non-secret path/context. The system does not fall back to alternate credentials or paths.
- Revision cleanup safety uncertainty results in skipped cleanup, not deletion.
- No automatic restart policy, host recovery, HA, backup/restore, CPU/memory escalation, or capacity promise is introduced.

## 7. Host exposure and resource profile

- Airflow UI/API remains published on all host interfaces as `8085:8080`; Jenkins UI remains `8098:8080`; Jenkins agent port `50000` is not published.
- TLS termination is not provided by Compose. The approved local HTTP exposure is preserved.
- No fixed per-container CPU/memory limits or performance claims are added. Unit 2 continues to cap active workload runs at two.

## Verification obligations

Later Build and Test must verify dependency ordering and the five-minute API deadline, health probe cadence/threshold, volume survival, file permissions and consumer readability, secret-safe failures, socket/network/port boundaries, and Bundle pruning under concurrent fetch/run/cleanup. Failure to prove active revision safety means cleanup must remain disabled rather than risk deleting pinned workload input.
