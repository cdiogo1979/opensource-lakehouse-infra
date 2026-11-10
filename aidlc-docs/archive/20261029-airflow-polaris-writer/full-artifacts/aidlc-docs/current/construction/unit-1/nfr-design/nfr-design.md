# NFR Design — Unit 1 Airflow Writer Identity and Broker

**Status:** Approved by user on 2026-10-29. Design choices Q1–Q5 are recorded as A.

## 1. Process model and bounded state

- Deploy one dedicated FastAPI/Uvicorn broker service, separate from Airflow scheduler and webserver processes.
- Run exactly one Uvicorn worker. The broker's active-run map, capability verifiers, and replay records are process-local; additional workers or replicas would not share registrations and could incorrectly reject valid renewals.
- Use the asynchronous event loop for Keycloak HTTP calls. Protect state transitions that create, replay, revoke, or expire a run registration with an async lock so duplicate registrations cannot race into multiple capabilities.
- Design for at least ten simultaneous active DAG-run registrations. This is a code/configuration capacity target only; the intent does not include concurrent-load certification or a throughput SLA.
- Keep state bounded by configured run expiry and the approved maximum DAG-run lifetime. Purge expired and revoked records. No state is written to disk or shared with Jupyter.
- On process restart, all state and the replay encryption key disappear. Existing JWTs may remain valid until their own expiry, but missing run state prevents renewal. No recovery or identity fallback is attempted.

## 2. Capability and replay-record protection

- Generate the run capability from a cryptographically secure random source with at least 256 bits of entropy. Store only a SHA-256 verifier for normal capability checks; never log or persist the raw value.
- For the short-lived lost-response replay path, encrypt the raw capability using authenticated encryption (AES-256-GCM) with a fresh 256-bit process-ephemeral key generated at startup.
- Keep the encryption key only in broker process memory. Do not load it from a file or environment variable. Delete each replay record on successful recovery followed by normal expiry/revocation cleanup, and discard all records and the key on process exit/restart.
- Keep replay records subject to a short configured TTL no longer than the active registration. Apply the stable `(dag_id, run_id)` idempotency key already specified in Functional Design; never derive metric labels or logs from it.
- If encryption/decryption or replay-state validation fails, reject the request with a sanitized error and fail closed.

## 3. Request timing and failure behavior

- Enforce the approved five-second Spark client timeout for each broker request. Renewal keeps at most three total requests with waits of one second and then two seconds, and does not start another attempt with 60 seconds or less remaining on the current JWT.
- Use asynchronous outbound HTTP to Keycloak so independent run requests do not block the event loop. Apply explicit connection and total upstream timeouts shorter than the caller's five-second timeout; return a sanitized transient failure before the caller times out when Keycloak is slow.
- A broker timeout or upstream failure never changes identity, extends capability expiry, or causes Spark to use a stale/expired token or long-lived secret. Registration retries after an uncertain response reuse the same idempotency key.
- Keep p95 ≤2 seconds as a normal local Compose operating target, not a guaranteed SLA. Report target evidence only from the permitted production workflow and direct request instrumentation; do not claim load certification.

## 4. TLS and trust distribution

- For local Compose, provision a dedicated internal CA and a broker server certificate through an explicit local bootstrap step. Store private material only under ignored `.runtime` paths with restrictive host permissions.
- After signing the broker certificate, keep the CA private key on the host and outside all containers. Mount the broker server certificate and private key read-only into the broker only. Mount the CA public certificate read-only into Spark.
- Include the broker's Docker service DNS name in the server certificate Subject Alternative Name. Spark uses that same service name and verifies both the certificate chain and hostname; do not disable verification.
- Keep certificate bootstrap idempotent and avoid printing private keys or credentials. Production deployment must replace local CA issuance with the organization's certificate-management process while retaining the same trust boundary.

## 5. Health and metrics

- Liveness returns healthy when the broker process and event loop are responsive. It does not depend on Keycloak or Polaris.
- Readiness verifies that local configuration is valid, required TLS material is loaded, and in-memory state has initialized. A temporary Keycloak or Polaris outage alone does not trigger a restart loop; affected token requests fail closed with sanitized responses.
- Expose Prometheus-compatible metrics only on the private broker Docker network. Use counters for registrations, renewal success/failure, and rejection outcomes, plus a request-latency histogram.
- Restrict labels to fixed operation, outcome, and bounded safe reason-code values. Never emit run IDs, user/client identifiers, access tokens, capabilities, client secrets, or response bodies as metric labels or values.
- Apply the same redaction to application logs and error responses. Do not log full inbound/outbound request bodies or authorization headers.

## 6. NFR traceability

| NFR | Design coverage |
|---|---|
| NFR-1 | Five-second client timeout; bounded renewal retries; p95 target and sanitized failure behavior (§3) |
| NFR-2 | One async worker and bounded state designed for ten active runs (§1) |
| NFR-3 | Dedicated Python FastAPI/Uvicorn service, isolated from Airflow processes (§1) |
| NFR-4 | Dedicated CA, broker-only server key, Spark-only public trust, verified DNS SAN (§4) |
| NFR-5 | Dependency-independent health semantics, private aggregate metrics, redaction (§5) |
| NFR-6 | Ephemeral state/key, fail-closed restart behavior, no recovery (§1–2) |
| NFR-7 | Renewal retries and remaining-token cutoff retained exactly (§3) |
| NFR-8 | No test expansion; main-only runtime E2E remains the verification boundary (§3 and §7) |

## 7. Verification boundary and deferred deployment details

This design does not add concurrent-load, resilience, or UAT runtime tests. Unit 1 Infrastructure Design must pin Python/FastAPI/Uvicorn and crypto/metrics dependencies, define container resource limits and Docker networks, specify certificate file paths/permissions, and wire health checks. Build and Test must verify the implemented behavior without claiming the excluded checks passed.
