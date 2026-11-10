# Unit 1 NFR Requirements Plan — Airflow Writer Identity and Broker

## Unit context and fixed decisions

Unit 1 provides a private Airflow writer-token broker, short-lived run authorization, token renewal, and Airflow DAG lifecycle integration. Functional Design is approved.

Fixed by approved requirements/design and not reopened in this plan:

- Writer client secret remains within the Airflow boundary; Spark gets only the initial access token and DAG-run capability.
- Broker endpoint uses private Docker networking and verified HTTPS.
- Broker state is in-memory and bounded by the DAG-run maximum. Losing broker state on restart prevents further renewal and fails the run closed; HA, durable recovery, and resilience testing are excluded.
- Writer JWT lifetime is one hour; human Jupyter lifetimes and Polaris grants remain unchanged.
- Main/production is the only runtime E2E target; UAT source/config verification only.

## Assessment plan

- [x] Read Unit 1 Functional Design, approved requirements, Application Design, and execution plan.
- [x] Record fixed availability/restart and test boundaries to avoid reopening approved scope.
- [x] Resolve the measurable performance, framework, TLS certificate, and observability questions below.
- [x] Assess all answers for ambiguity and conflict with approved security/functional requirements.
- [x] Create `nfr-requirements.md` and `tech-stack-decisions.md`.
- [x] Validate Unit 1 NFR traceability; artifacts are ready for approval before Unit 1 NFR Design.

## Clarification questions

Fill each `[Answer]:` tag. The recommended options fit the local single-node Compose platform and existing Python stack.

### Question 1 — Broker request performance

What response-time expectation should apply to run registration and token renewal?

A) Under normal local Compose conditions, target p95 ≤ 2 seconds and enforce a 5-second client timeout; a timeout fails closed (recommended).

B) Set a different target; specify the p95 target and timeout.

C) No response-time target; use a 10-second timeout.

X) Other; describe after the answer tag.

[Answer]: A

### Question 2 — Renewal volume and concurrency support

Concurrent-workload testing is out of scope. What service capacity should the broker be designed to support?

A) Support at least 10 simultaneously active DAG-run registrations and independently refresh them; no throughput SLA or concurrent-load certification is required in this intent (recommended for a small local platform).

B) Support one active DAG run only; reject other registrations while it is active.

C) Set a different expected number of active runs and renewal burst.

X) Other; describe after the answer tag.

[Answer]: A

### Question 3 — Broker implementation framework

Which implementation stack should the dedicated broker use?

A) Python 3 with a small FastAPI application and Uvicorn server, separate from Airflow scheduler/web processes (recommended; aligns with the existing Python platform and isolates token issuance).

B) Python Tornado service using the existing JupyterHub/Tornado ecosystem.

X) Other; describe after the answer tag.

[Answer]: A

### Question 4 — Internal TLS trust

How should Spark validate the broker's HTTPS certificate?

A) Use a dedicated internal CA for the Airflow broker, mount only its public CA certificate read-only into the Airflow Spark runtime, and keep the CA private key outside Spark (recommended; isolates trust from the JupyterHub broker).

B) Reuse the existing JupyterHub broker CA for Airflow Spark.

X) Other; describe after the answer tag.

[Answer]: A

### Question 5 — Health, metrics, and logs

What broker observability should be required without exposing identity or credentials?

A) Provide readiness/liveness checks and aggregate counters for registrations, successful/failed renewals, rejections by safe reason code, and latency. Logs/metrics must omit tokens, capabilities, client secrets, user identifiers, and sensitive response bodies (recommended).

B) Provide health checks and sanitized logs only; no metrics endpoint/counters.

X) Other; describe after the answer tag.

[Answer]: A

## Category applicability review

- Scalability: Q2 applies; production throughput certification is not required.
- Performance: Q1 applies to broker registration/renewal.
- Availability: fixed by the approved in-memory/fail-closed scope; no HA or recovery requirement is introduced.
- Security: Q4 applies; secret, token, and capability handling remains fixed by approved requirements.
- Technology: Q3 applies; deployment details are completed in Infrastructure Design.
- Reliability and maintainability: Q5 applies to health, diagnostics, and aggregate service behavior.
- Usability/frontend: not applicable because this unit exposes an internal service API and has no user-facing interface.
