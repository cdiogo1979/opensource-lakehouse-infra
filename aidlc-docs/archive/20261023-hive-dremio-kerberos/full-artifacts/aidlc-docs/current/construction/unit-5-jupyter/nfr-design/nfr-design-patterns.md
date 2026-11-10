# Unit 5 NFR Design Patterns — JupyterHub and Per-User Spark

This design applies the approved NFR requirements and answers A/A/A/A/A. It adds no runtime service or shared execution tier.

## Resilience and Recovery

- Treat each spawned user server as an independent failure boundary. A spawn, Kerberos, Spark, Hive, or RustFS failure for one username must not stop another user's session.
- Fail fast when the matching keytab, RustFS credential reference, Hive endpoint, or required startup step is unavailable. Do not fall back to `admin`, `write-service-account`, or another user's identity.
- Do not automatically restart crashed containers, retry authorization queries, or queue a failed session for later admission. Report the failure category and let the operator diagnose and restart only that session.
- On session stop, destroy its private Kerberos ticket cache and container while preserving its username-specific work volume. Do not reset platform volumes, rerun ETL, or change credentials during recovery.
- Classify session/spawn, Kerberos, Spark, Hive connectivity, Hive authorization, missing-object, resource-exhaustion, and RustFS credential failures separately. Only a demonstrated authorization decision can count as an expected deny.

## Capacity and Admission

- Keep a fixed ceiling of three known identities and up to three concurrently active containers on the existing single Docker host.
- Attempt requested user sessions independently. A local resource-limit or Docker-spawn failure affects that request only; do not queue users, preempt a running server, or silently evict another user.
- Do not introduce horizontal scaling, a shared Spark cluster, a scheduling queue, resource autoscaling, or user growth policy.
- Treat host resource exhaustion as an operational failure. It does not alter the expected access matrix and must not be recorded as authorization evidence.

## Performance

- Keep Spark local to each single-user container and retain the existing local-mode defaults. Avoid adding shared caches, connection pools, warm pools, benchmark jobs, or speculative tuning in the absence of a performance target.
- Use the existing small, deterministic Hive table queries to demonstrate access. The goal is correct identity and policy outcome, not throughput measurement.
- Three sessions may contend for local CPU, memory, and I/O. Record resource exhaustion as an operational constraint; no numeric performance commitment is implied.

## Security and Isolation

- Publish JupyterHub on loopback only and retain DummyAuthenticator only for the local PoC. Its usernames are unverified labels; remote access is outside the accepted trust boundary.
- Restrict admitted usernames to `user_a`, `user_b`, and `admin`, each mapping to its exact same-named Kerberos and RustFS identity.
- Mount the Docker socket only in the Hub container because DockerSpawner requires it. Never mount the socket into a notebook container.
- Run notebook containers as non-root `jovyan`; do not request privileged mode or elevated capabilities.
- Give each user container its own read-only keytab, private ticket cache, distinct RustFS credential, and writable work volume. No credential, cache, or writable workspace is shared across identities.
- Avoid logging environment dumps or credential-bearing startup commands. Evidence stays local and redacted; it includes only the approved scenario fields.
- Hub administrator status is separate from Spark data authorization. `admin` is not used to substitute for either test user's allow/deny scenario.

## Compatibility and Operation

- Retain JupyterHub 5.3.0 and Spark 3.5.5/Iceberg 1.8.1. Pin compatible DockerSpawner and Jupyter Python package versions before image generation.
- Use only the Hub, DockerSpawner, per-user containers, existing Hive/KDC/RustFS services, per-user work volumes, and local logs/evidence. Add no health/monitoring service, centralized audit service, cache, queue, or shared compute component.
- Preserve manual operator control for session restart and user-volume maintenance. No automatic backup/restore or formal evidence retention is required.

## Open Runtime Gates

- Verify the pinned Python dependencies are compatible with JupyterHub 5.3.0.
- Verify the Spark single-user image can use the Kerberos ticket cache and user-specific RustFS credentials while connecting to the existing Hive Metastore.
- Verify that the Hive/RustFS authorization path enforces the expected `user_a` and `user_b` access matrix. This design does not claim that enforcement has passed.
- Verify the host can run three concurrent sessions; no resource sizing or performance SLA is claimed.
