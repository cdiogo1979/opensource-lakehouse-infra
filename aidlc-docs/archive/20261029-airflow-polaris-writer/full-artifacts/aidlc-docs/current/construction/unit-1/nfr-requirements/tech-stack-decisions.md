# Technology Decisions — Unit 1 Airflow Writer Identity and Broker

**Status:** Approved by user on 2026-10-29. Infrastructure-specific pins and topology remain for Unit 1 Infrastructure Design.

| Area | Decision | Rationale and constraints |
|---|---|---|
| Broker language | Python 3 | Consistent with the existing Airflow and Spark integration code. Pin the runtime version during Infrastructure Design. |
| Broker API | FastAPI | Provides a small typed internal HTTP API for registration, renewal, revocation, and health checks. It must validate request shape and fail closed. |
| ASGI server | Uvicorn | Runs the broker in a distinct service/process, separate from Airflow scheduler and webserver processes. Pin the dependency version during Infrastructure Design. |
| Broker state | Bounded in-memory state | Holds active DAG-run capability verification and the approved short-lived encrypted replay record. No durable store or restart recovery is introduced. |
| Spark transport | HTTPS with verified certificate | Use a dedicated internal Airflow broker CA. Mount only its public certificate read-only into Spark. The private CA key stays outside Spark. |
| Capacity target | At least 10 active DAG-run registrations | Design capacity only; no concurrent workload test, throughput SLA, or load certification in this intent. |
| Request target | p95 ≤ 2 seconds; 5-second client timeout | Applies under normal local Compose conditions. Timeout follows the approved bounded retry policy and fails closed. |
| Observability | Readiness/liveness plus aggregate metrics | Record registrations, renewal outcomes, safe rejection classes, and latency without token, capability, secret, user, or run identifiers. |

## Deferred to Infrastructure Design

- Pin Python base image, FastAPI, Uvicorn, and transitive dependencies.
- Select the broker certificate generation/storage mechanism and how its public CA certificate is distributed to Spark.
- Define service ports, Docker network attachment, resource bounds, and health-check commands.
- Confirm that all required config is injected without placing the writer secret in Spark, source control, or logs.
- Define the metrics exposition mechanism and scrape/collection path while keeping the API private.
