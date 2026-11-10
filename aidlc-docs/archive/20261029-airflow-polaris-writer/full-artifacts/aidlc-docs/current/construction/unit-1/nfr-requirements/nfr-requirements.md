# NFR Requirements — Unit 1 Airflow Writer Identity and Broker

**Status:** Approved by user on 2026-10-29. These requirements refine the approved functional requirements and do not change their scope.

## Performance

### NFR-1 — Broker request latency

Under normal local Docker Compose conditions, run registration and token renewal requests shall target p95 response latency of no more than 2 seconds. The Spark-side client shall enforce a 5-second request timeout. A timeout shall fail closed and follow the approved bounded retry behavior; it shall not cause identity fallback or use of a long-lived credential.

The p95 target is a local operating target, not a production SLA or a claim of performance certification.

## Capacity and concurrency

### NFR-2 — Active run capacity

The broker shall support at least 10 simultaneously active DAG-run registrations and maintain independent renewal authorization for each run. State shall remain bounded by the configured maximum run duration and cleanup rules in the approved Functional Design.

This requirement defines a minimum design capacity only. Concurrent workload tests, throughput guarantees, and load certification are excluded from this intent.

## Technology

### NFR-3 — Broker implementation

Implement the dedicated broker as a Python 3 FastAPI application served by Uvicorn. Run it as a separate service from the Airflow scheduler and webserver processes so token issuance and renewal handling have an isolated process boundary.

Exact base image and dependency versions, deployment health-check wiring, and service topology are to be selected in Unit 1 Infrastructure Design; versions must be pinned for the delivered implementation.

## Transport security

### NFR-4 — Broker HTTPS trust

Spark-to-broker traffic shall use HTTPS with certificate verification enabled. Use a dedicated internal CA for the Airflow broker. Airflow Spark runtimes may receive only the public CA certificate, mounted read-only. The CA private key shall remain outside Spark containers and shall not be committed to source control or exposed through logs/configuration.

The exact certificate issuance, storage, and rotation mechanism is an Infrastructure Design decision. No insecure TLS verification bypass is allowed.

## Observability and diagnostics

### NFR-5 — Safe health and metrics

The broker shall expose readiness and liveness checks and aggregate counters for run registrations, successful and failed renewals, and rejections grouped by safe reason code. It shall expose aggregate request-latency measurements.

Health responses and metrics shall not include access tokens, renewal capabilities, client secrets, user identifiers, or sensitive response bodies. Logs and error responses shall apply the same exclusions and use sanitized diagnostic details. Metrics shall be aggregate and shall not use run IDs or user/client identifiers as labels.

## Availability and failure behavior

### NFR-6 — Fail-closed state loss

Broker authorization state is in-memory and scoped to the bounded lifetime of active DAG runs. If state is lost on restart, requests requiring missing state shall fail closed. Durable state recovery, high availability, and broker resilience testing are not required by this intent.

### NFR-7 — Bounded retry behavior

Token renewal timeouts and transient failures shall use only the retry behavior defined in the approved Functional Design: at most three total requests, with waits of one second and then two seconds. Do not begin another request when the current token has 60 seconds or less remaining. The overall request timeout remains 5 seconds per attempt. Retries shall not extend capability validity or change the authenticated identity. Registration retries, if needed after an uncertain response, must use the same approved idempotency key and must not create a second capability.

## Verification boundary

### NFR-8 — Verification scope

Runtime end-to-end verification remains limited to the existing production `main-init_environment` workflow and its configured sample-table overwrite. UAT behavior is verified from source/configuration only. Concurrent workload and resilience checks remain excluded and shall be reported as unverified rather than passed.

## Traceability

| NFR | Source / related requirement | Verification evidence planned |
|---|---|---|
| NFR-1 | FR-4, FR-5; Unit 1 performance choice | Broker/client request timing and timeout behavior in functional/integration checks; no load certification |
| NFR-2 | FR-4, FR-5; Unit 1 capacity choice | Capacity configuration/code review; concurrent-load execution excluded |
| NFR-3 | FR-1, FR-4 | Image/service configuration and implementation review |
| NFR-4 | NFR-1 security handling; approved private HTTPS design | TLS config and Spark trust mount review; production workflow evidence |
| NFR-5 | NFR-1; token/capability secrecy | Health/metrics behavior and sanitized logging review |
| NFR-6 | Approved Functional Design rules 11–14 | Failure-closed code/config review; resilience tests excluded |
| NFR-7 | Approved Functional Design rules 15–19 | Renewal-client behavior review and main workflow evidence |
| NFR-8 | FR-7, FR-8; approved test boundary | Main workflow result and UAT source/config review |
