# Unit 5 NFR Design Questions

Please answer each question with a letter after `[Answer]:`.

## Question 1 — Resilience Patterns
How should a user session that fails to start or crashes be handled?

A) Fail only that session, preserve its per-user work volume, report the failure category, and let the operator diagnose and restart it manually. Do not automatically retry queries or substitute another identity.

B) Automatically restart the affected user container once, while preserving its work volume, then report failure if it does not recover.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 2 — Scalability and Admission
If the host cannot start all three requested sessions because local resources are constrained, what should the Hub do?

A) Attempt to start each requested isolated session; let a spawn/resource failure affect only that session and report it clearly. Do not queue or silently evict another user's session.

B) Admit sessions serially and queue additional users until an active session stops.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 3 — Performance Pattern
Which Spark resource/performance pattern should the design use, given that no numeric SLA is required?

A) Keep the existing Spark local-mode defaults and avoid extra caching, benchmarking, or tuning; report host resource exhaustion as an operational failure.

B) Define explicit CPU and memory limits/tuning for each user container and local Spark process, while retaining best-effort outcomes.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 4 — Security Pattern
Which single-user container boundary should the design require?

A) Run notebook containers as the existing non-root `jovyan` user with no privileged mode or Docker socket; only the Hub has Docker socket access, and each user container receives only its own read-only keytab and RustFS identity.

B) Run notebook containers with elevated privileges to simplify credential and Spark configuration, while keeping the Hub loopback-only.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 5 — Logical Components
Are the existing JupyterHub, DockerSpawner, per-user notebook containers, target platform services, and local evidence files sufficient?

A) Yes. Add no health/monitoring service, shared Spark cluster, cache, queue, or centralized audit component; use current logs and operator observations.

B) Add a lightweight health/metrics component for notebook and Spark session status.

X) Other (please describe after `[Answer]:` below)

[Answer]:A
