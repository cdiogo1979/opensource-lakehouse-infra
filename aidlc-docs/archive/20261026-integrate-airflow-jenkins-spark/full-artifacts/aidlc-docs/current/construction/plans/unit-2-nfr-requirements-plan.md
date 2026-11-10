# Unit 2 NFR Requirements Plan — Airflow Bundle Runner

## Unit and Functional Baseline

This stage defines measurable quality requirements for Airflow's run-pinned Git Bundle workflow and per-run Spark driver/worker pair. One immutable bundle revision supplies the workflow and configuration; each DAG run creates one ephemeral driver and one worker-only Spark container using the existing `write-service-account` Kerberos and RustFS identity; and both containers are removed after success or failure.

The accepted functional design also calls for Hive catalogs `lakehouse_dev`, `lakehouse_uat`, and `lakehouse_prod`, each with `databaseA` and `databaseB`; writer/admin access across all three catalogs and their isolated RustFS storage; and equivalent read-only access for `user_a` and `user_b`. The dev sample target is `lakehouse_dev.test_database.test_airflow_generated_table`. UAT and prod Airflow endpoints remain unconfigured and must fail closed.

At most two DAG runs may be active; further runs wait in the Airflow queue. Each run worker registers with the shared Spark Standalone master, but executor placement may span all registered workers. Multi-catalog support through Hive 3, Iceberg Spark, StarRocks, and RustFS is not yet verified. These are explicit Build and Test acceptance gates, not presumed properties of the current single-catalog stack. Before implementation, reconcile the functional design delta in requirements, story acceptance criteria, and application/service design.

## NFR Assessment Checklist

- [x] Read Unit 2 Functional Design, approved requirements, stories, and Unit of Work boundaries.
- [x] Assess scalability/performance and availability against the local Compose PoC scope; no SLA or capacity target is approved.
- [x] Define credential isolation, bundle immutability, paired-container cleanup safety, and sanitized observability constraints from the approved baseline.
- [x] Identify measurable runtime questions for concurrency, startup/readiness, cleanup, catalog authorization verification, and performance scope.
- [x] Resolve all questions below; follow up on ambiguity or conflict before generating requirements.
- [x] Create `aidlc-docs/current/construction/unit-2/nfr-requirements/nfr-requirements.md`.
- [x] Create `aidlc-docs/current/construction/unit-2/nfr-requirements/tech-stack-decisions.md`.
- [x] Validate against Unit 2 Functional Design, requirements/story changes, US-01/02/03/04/06, and FR-2/3/4/7 and NFR-1/2/3/4.
- [x] Present NFR Requirements for explicit review and approval before Unit 2 NFR Design.

## Assessment Boundaries

- **Scalability/performance**: Local Docker Compose PoC. Do not make throughput, latency, or concurrent-run claims without a selected target. Keep existing Spark resource settings unless later approved.
- **Availability/recovery**: No HA, production uptime, RTO/RPO, or DR objective. Fail closed for unavailable environments and runtime prerequisites. Driver cleanup and visible run outcomes are in scope.
- **Security**: Keep keytab and RustFS secret mounts read-only, caches private per run, and credentials/ticket material out of logs, bundle content, and task output. The Security Baseline extension is disabled; explicit credential requirements remain mandatory.
- **Isolation**: A run is pinned to one Bundle revision and its environment config. One run's driver, TGT cache, and execution state must not be shared with another run.
- **Authorization**: Later integrated verification must cover all three catalog names, the two normal readers, the writer identity, and each storage prefix. This validates the approved functional policy; it does not assume existing engine enforcement.
- **Maintainability**: Prefer the approved Airflow, Docker, Spark, Kerberos, Hive, and RustFS stack. Do not add a helper service, identity, or runtime package without an approved design change.
- **Property-based testing**: Apply only to new pure functions or serialization round-trips; do not force it onto Airflow orchestration or Docker lifecycle behavior.

## NFR Questions

Please fill each `[Answer]:` tag. If no option fits, select X and describe the target.

### Question 1 — Concurrent DAG run limit

What maximum number of active DAG runs should this local PoC admit at once? Each run gets its own driver and worker containers and separate credential caches, while Spark Standalone may schedule executors across the shared cluster.

A) One active run at a time (recommended for the current local PoC; predictable shared-resource load).
B) Two active runs at a time; queue additional runs.
X) Other (provide the maximum and queue/reject behavior after `[Answer]:`).

**[Answer]:** X , each dag run should create 1 driver and 1 worker . For the poc consider two concurrent dag runs. Clarified: one ephemeral worker container per run; executor placement may use any registered worker.

### Question 2 — Driver readiness deadline

How long may Airflow wait for a driver to start, acquire/validate the writer TGT, and become ready to submit before failing the run?

A) Five minutes from container start, checking readiness at least every 5 seconds; then fail and clean up the driver.
B) Ten minutes from container start, checking readiness at least every 10 seconds; then fail and clean up the driver.
X) Other (provide a deadline and polling interval after `[Answer]:`).

**[Answer]:**A — five minutes from container start, with readiness checks at least every five seconds. Both the driver and worker must be ready; the worker must have a valid TGT and be registered with the Spark master before submission.

### Question 3 — Driver cleanup deadline

How quickly must the per-run driver be absent after a DAG run reaches a terminal state?

A) Attempt graceful stop immediately and ensure container removal within 60 seconds; report a cleanup failure if it cannot be removed within the limit.
B) Allow up to five minutes for graceful termination before reporting cleanup failure.
X) Other (provide the deadline and graceful-stop behavior after `[Answer]:`).

**[Answer]:**A — remove both per-run containers within 60 seconds of terminal run state.

### Question 4 — Authorization verification evidence

What evidence is required before the three-catalog access model can be considered verified?

A) In final integrated Build and Test, verify in every catalog that the writer can create/write a disposable table and object data; each reader can read a designated table; reader writes fail; and reader access is limited to the intended catalog warehouse prefixes. Verify StarRocks query-only behavior separately. Use disposable data and remove only the test objects afterward. (Recommended.)
B) Verify one catalog end-to-end, and document the other two catalogs as unverified until a later environment is available.
X) Other (specify the catalog/identity/component matrix and expected positive/negative outcomes after `[Answer]:`).

**[Answer]:**A

### Question 5 — Performance and capacity scope

What performance claim should this local integration make?

A) No numeric throughput/latency/capacity claim. Preserve existing service resources; use only the approved concurrency and readiness/cleanup limits as operational bounds. (Recommended.)
B) Set a measurable workload target (provide workload size, concurrency, and timing after `[Answer]:`).
X) Other (describe the scope after `[Answer]:`).

**[Answer]:**A

## Approval Gate

After answers are reviewed and ambiguity is resolved, generate the NFR Requirements and technology decision artifacts. Request explicit approval before proceeding to Unit 2 NFR Design.

**Status**: Approved by the user on 2026-10-26. Proceeding to Unit 2 NFR Design. The Functional Design and application/service boundaries were updated to include one ephemeral worker per run with shared Spark Standalone scheduling.
