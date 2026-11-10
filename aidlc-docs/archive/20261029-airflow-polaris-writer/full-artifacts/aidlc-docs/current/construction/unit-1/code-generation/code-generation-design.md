# Code Generation Design — Unit 1 Airflow Writer Identity and Broker

**Status:** Approved; code generation is implemented. Builds and runtime verification remain for the Build and Test stage.

## Contract-first implementation

The authoritative API schema is `infra/airflow-token-broker/openapi.yaml` (the AI-DLC review copy is `broker-api-contract.yaml`). It defines `/v1` routes, separate control and run-capability bearer credentials, stable Airflow run identity, opaque run handles, absolute UTC token expiry, and sanitized RFC 9457 errors. Unit 2 must pin and validate this contract before implementing its Spark adapter.

### API lifecycle

1. Airflow calls `POST /v1/runs` using the broker control credential with `dag_id` and `run_id`. The broker validates the values and derives stable identity from their canonical pair. An active duplicate returns the same opaque `run_handle` and renewal capability with a fresh initial Keycloak access token. The encrypted replay record is used only to recover a lost registration response.
2. Airflow injects the initial access token and renewal capability only into the matching ephemeral Spark container environment, alongside non-secret broker URL and CA configuration. The adapter variables are `LAKEHOUSE_TOKEN_PROVIDER=airflow`, `LAKEHOUSE_INITIAL_ACCESS_TOKEN`, `LAKEHOUSE_TOKEN_BROKER_URL`, `LAKEHOUSE_TOKEN_BROKER_CA`, `LAKEHOUSE_RUN_HANDLE`, and `LAKEHOUSE_RUN_CAPABILITY`.
3. Spark calls `POST /v1/runs/token` over verified HTTPS. It sends `run_handle` in JSON and the run capability only as the bearer authorization header. The broker returns a fresh writer access token and absolute expiry.
4. Airflow calls `DELETE /v1/runs/{run_handle}` with the separate control credential on terminal cleanup. Repeated revocation is idempotent. A revoked or expired registration cannot renew.

The API never exposes the writer client secret. A run capability is never placed in a URL, body, XCom, command argument, or persistent file. Broker, HTTP client, reverse-proxy, and task logging must redact authorization headers and token-bearing success responses.

## Implementation ownership and order

1. In `opensource-lakehouse-infra-v2`, implement the broker and contract validation from the schema, then the pinned broker image, read-only secrets, verified TLS, health/metrics, private Compose networks, and Airflow lifecycle commands.
2. Update Keycloak bootstrap idempotently for the one-hour access-token lifespan on `write-service-account` only. Confirm the actual setting representation against pinned Keycloak 26.8.1 before editing the realm contract.
3. In `opensource-lakehouse`, update only the DAG factory and required Spark launch configuration. Register before launch, retain run credentials across task retries, avoid secret-bearing XCom/log output, and remove the Spark container/revoke on all terminal outcomes.
4. Add focused unit, OpenAPI schema, Compose configuration, Bundle registration, and secret-boundary checks. Build images and verify service readiness without launching production workloads until Unit 2 and the shared provider are complete.
5. Commit and push the authorized workload-repository changes to `main`; only after Unit 2 integration run the approved `main-init_environment` E2E.

## Error and retry mapping

- `400`: invalid request shape or Airflow identifiers.
- `401`: missing/invalid control credential or capability.
- `404`: unknown run handle; response does not disclose whether it previously existed.
- `409`: terminal or expired run cannot be reactivated.
- `429`: bounded in-memory capacity is exhausted.
- `502`: invalid or unsuccessful Keycloak token response; discard upstream body.
- `503`: broker is not ready or a temporary dependency is unavailable.
- All errors use RFC 9457 fields plus a stable allow-listed `code`; no credentials, token claims, raw identifiers, or upstream response content appear in details or logs.

## Preconditions and known workspace dependency

- The `opensource-lakehouse` checkout is present at the workspace root and is the authorized DAG target. Confirm its repository/branch and current user changes immediately before editing; preserve uncommitted work.
- Current service availability and Docker permissions are not assumed by these design artifacts.
- No UAT DAG execution, concurrency/load certification, resilience testing, grant/policy changes, or provider-volume resets are in scope.

## Review checklist

- [x] Five clarification answers are A.
- [x] API uses OpenAPI 3.1, `/v1`, separate control/run bearer schemes, explicit `run_handle`, UTC absolute expiry, and sanitized problem responses.
- [x] API contract establishes the required Unit 1 to Unit 2 dependency.
- [x] Implementation order preserves repository and runtime boundaries.
- [x] Live verification remains restricted to the approved main production job after Unit 2.
- [x] User approved these artifacts before source changes began.
