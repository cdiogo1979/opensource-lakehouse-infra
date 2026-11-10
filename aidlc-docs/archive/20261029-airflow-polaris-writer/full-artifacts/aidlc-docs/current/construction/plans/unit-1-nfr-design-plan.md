# Unit 1 NFR Design Plan — Airflow Writer Identity and Broker

## Approved inputs and fixed boundaries

Unit 1 NFR Requirements are approved. This design step refines implementation mechanisms without changing approved behavior or scope:

- Python 3 FastAPI broker served by Uvicorn, separate from Airflow scheduler/webserver processes.
- At least 10 active DAG-run registrations as a design capacity; no concurrent-load certification.
- In-memory, bounded run state; loss on restart fails closed; no HA or durable recovery.
- p95 request target ≤2 seconds under normal local Compose conditions; five-second per-request client timeout.
- Dedicated internal Airflow broker CA; Spark receives only the public CA certificate read-only.
- Readiness/liveness and aggregate metrics with no token, capability, secret, run, or user identifiers.
- Renewal has at most three total attempts with waits of one and two seconds, and no retry with 60 seconds or less remaining on the current JWT.
- Main production workflow is the only runtime E2E target. UAT runtime, concurrent-load, and resilience checks remain excluded.

## Design assessment plan

- [x] Review approved NFR requirements, technology decisions, Functional Design, and explicit security constraints.
- [x] Identify implementation details that affect the NFRs but do not reopen approved functional scope.
- [x] Resolve the questions below and check answers for contradictions.
- [x] Prepare `nfr-design.md` and `nfr-architecture.md`.
- [x] Validate each design against NFR-1 through NFR-8; artifacts are ready for approval before Unit 1 Infrastructure Design.

## Clarification questions

Fill each `[Answer]:` tag. The recommendations preserve the approved bounded in-memory design and local Docker Compose target.

### Question 1 — Uvicorn process model for in-memory state

How should the broker process model support independent run state without introducing shared persistence?

A) Run one Uvicorn worker with an asynchronous event loop. Keep all run state in that process; do not horizontally scale this broker in this intent (recommended and consistent with the no-HA boundary).

B) Add a shared external state store so multiple broker workers/replicas can serve the same capabilities; this changes the approved no-durable-state boundary and would need scope approval.

X) Other; describe after the answer tag.

[Answer]:A

### Question 2 — Encryption key for lost-response replay records

The approved functional design allows a short-lived encrypted in-memory capability replay record. How should its encryption key be managed?

A) Generate a fresh cryptographically secure key in broker memory at startup, encrypt replay records with authenticated encryption, and discard the key and records on restart/expiry/revocation. Never persist the key or replay record (recommended; restart already invalidates renewal state).

B) Store a persistent encryption key in a host secret file so replay records can survive broker restarts; this conflicts with the in-memory-only state boundary.

X) Other; describe after the answer tag.

[Answer]:A

### Question 3 — Metrics endpoint

How should operators access the required aggregate metrics?

A) Expose a Prometheus-compatible `/metrics` endpoint on the broker's private Docker network only. Use bounded label values such as operation and safe rejection reason; never label metrics with run, user, token, capability, or client identifiers (recommended).

B) Expose metrics only through the general broker API route and use no dedicated scrape endpoint.

X) Other; describe after the answer tag.

[Answer]:A

### Question 4 — Liveness and readiness semantics

Which checks should determine broker health without turning a temporary identity-provider outage into a restart loop?

A) Liveness reports only that the process/event loop is responsive. Readiness checks local configuration, loaded TLS material, and initialized in-memory state; it does not fail solely because Keycloak or Polaris is temporarily unreachable (recommended; requests still fail closed when dependencies are unavailable).

B) Readiness actively requires successful Keycloak and Polaris probes; dependency outages remove the broker from service until probes recover.

X) Other; describe after the answer tag.

[Answer]:A

### Question 5 — Local TLS certificate bootstrap and DNS identity

How should the dedicated CA and broker certificate be provisioned for local Compose?

A) A local bootstrap creates CA/server material under ignored `.runtime` storage. Keep the CA private key outside containers after issuance; mount the server key/certificate read-only only into the broker and the CA public certificate read-only into Spark. Include the broker's Docker service DNS name in the certificate SAN and have Spark call that name (recommended; production CA issuance remains a deployment-specific replacement).

B) Generate a self-signed server certificate and disable certificate verification in Spark for local convenience.

X) Other; describe after the answer tag.

[Answer]:A

## Scope and applicability review

- NFR performance, bounded capacity, security, and diagnostics apply and are covered above.
- High availability, recovery, load certification, UAT execution, and resilience tests remain excluded by approval.
- No UI or user-facing observability surface is introduced.
