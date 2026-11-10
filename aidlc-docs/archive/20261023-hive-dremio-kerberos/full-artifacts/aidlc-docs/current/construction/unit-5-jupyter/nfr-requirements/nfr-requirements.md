# Unit 5 NFR Requirements — JupyterHub and Per-User Spark

These requirements apply to the local JupyterHub and isolated notebook/Spark sessions in the existing single-host Docker Compose PoC. They do not establish production service objectives.

## Capacity and Performance

- **U5-NFR-01 — Concurrent sessions**: Support up to three simultaneously active, isolated sessions for `user_a`, `user_b`, and `admin` on the existing PoC host. Horizontal scaling and additional users are out of scope.
- **U5-NFR-02 — Best-effort performance**: No numeric session-startup, query-latency, throughput, or concurrency-performance SLA is required. The environment must allow an operator to execute the fixed access scenarios and record their outcomes.
- **U5-NFR-03 — Resource constraints**: The PoC may use host resources on a best-effort basis. Resource exhaustion must be reported as a session/Spark failure, not an authorization denial.

## Availability, Recovery, and Data Preservation

- **U5-NFR-04 — Local availability**: JupyterHub and notebook sessions are single-host, best-effort services. No HA, failover, uptime, disaster recovery, or automatic backup/restore objective is required.
- **U5-NFR-05 — Operator-led recovery**: After diagnosis, the operator may restart only the affected notebook session. Do not automatically retry authorization checks or use another user's/admin's session as a fallback.
- **U5-NFR-06 — Workspace persistence**: Preserve the affected user's separate work volume across session stop/recreation and ordinary service recovery. There is no automatic backup guarantee; an operator may explicitly back up data outside this workflow.
- **U5-NFR-07 — Platform state**: Session recovery must not reset platform volumes, remove catalog data, rerun ETL, or rotate/replace existing credentials. Ticket caches are session-scoped and destroyed when the session stops.

## Security and Evidence

- **U5-NFR-08 — Local-only access**: Bind the Hub to the local host only. DummyAuthenticator usernames are labels and do not verify user identity; the Hub must not be exposed as an authenticated or production service.
- **U5-NFR-09 — Session isolation**: Each active username has a distinct container, writable work volume, private Kerberos ticket cache, and matching credential mapping. No writable notebook workspace, keytab, or ticket cache is shared between users.
- **U5-NFR-10 — Credential handling**: Mount only the matching user's keytab read-only and provide only that user's RustFS credentials to the session. Never log, display, commit, or include in an image a password, S3 secret, keytab/ticket content, or complete credential environment.
- **U5-NFR-11 — Evidence minimization**: Keep evidence local and redacted. Record only username/principal, target database/table, expected and actual result, timestamp, and redacted failure category. No separate audit service or formal retention period is required.
- **U5-NFR-12 — Failure classification**: A denial counts only when the expected principal is established and an authorization decision is identifiable. Session startup, Kerberos, Hive connectivity, missing objects, resource exhaustion, and RustFS credential errors are separate outcomes.
- **U5-NFR-13 — Authorization feasibility**: If the selected Hive/RustFS path cannot enforce the approved Spark matrix, report a feasibility blocker with evidence. Do not weaken the matrix, broaden access, or elevate a user automatically.

## Compatibility and Maintainability

- **U5-NFR-14 — Baseline compatibility**: Preserve JupyterHub 5.3.0 and Spark 3.5.5/Iceberg 1.8.1 image baselines. Any required baseline change is a separately reviewed compatibility adjustment.
- **U5-NFR-15 — Dependency pinning**: Pin DockerSpawner and other JupyterHub Python dependencies to explicit versions compatible with the retained JupyterHub release before implementation; floating dependency versions are not acceptable for the repeatable PoC build.
- **U5-NFR-16 — Reproducibility**: Document the retained image/dependency versions and the local startup, per-user session, recovery, and redacted verification procedures. No Airflow/Jenkins integration or direct RustFS authorization acceptance test is introduced.

## Assessment Status

Answers validated as A/A/A/A: three concurrent isolated sessions; no numeric performance target; operator-led recovery with persistent per-user volumes and no required backup/restore; and retained image baselines with pinned compatible Python dependencies. These are requirements, not claims that runtime capacity, compatibility, or authorization has passed verification.
