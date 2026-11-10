# Unit 1 Code Generation Plan — Airflow Writer Identity and Broker

## Approved scope and invariants

- Implement Airflow writer identity, broker, and DAG orchestration across `opensource-lakehouse-infra-v2` and the authorized `opensource-lakehouse` workload repository.
- Keep Bundle definitions, names, refs, paths, validation, and selection behavior unchanged: `lakehouse-main` → `main`; `lakehouse-uat` → `uat`.
- Use the approved one-hour writer access-token lifetime override only for `write-service-account`; keep human token policies, Polaris grants, RustFS policies, and provider data unchanged.
- Keep the Keycloak writer secret broker-only. Keep the separate broker control credential in the broker and Airflow task-execution boundary. Give each ephemeral Spark process only its initial JWT, run capability, broker URL, and CA trust configuration.
- Use the approved Compose profile, private networks, verified internal HTTPS, dedicated one-worker broker image, in-memory run state, and Airflow start/status/stop lifecycle.
- Main/production `main-init_environment` is the only runtime E2E target after Unit 2 is complete. UAT runtime, concurrency, and resilience verification remain excluded.

## Repository ownership

### `opensource-lakehouse-infra-v2`

- Add the broker source, versioned API contract, pinned minimal image/dependencies, TLS and health configuration, Compose profile/network/secrets, provisioning, and `lakehouse.sh` lifecycle commands.
- Add or update Keycloak bootstrap so the writer client alone receives the approved one-hour lifespan.
- Preserve existing provider volumes, Jupyter startup behavior, Polaris/RustFS grants, and other identities.

### `opensource-lakehouse`

- Modify only the DAG factory and the smallest necessary Spark startup/configuration needed for broker registration, initial token/capability injection, renewal configuration, and cleanup on all terminal outcomes.
- Remove legacy Kerberos/keytab and long-lived RustFS writer-key mounts from this writer workflow; preserve unrelated workflows and Bundle setup.
- Commit and push the authorized source changes to `main` for Airflow Bundle visibility; test the main production job only.

## Code generation sequence

1. Resolve the API questions below and publish the API schema plus examples as the Unit 1/Unit 2 integration contract before implementing its Spark consumer.
2. Verify the actual workspace checkouts and current pinned provider versions. The `opensource-lakehouse` directory must be available before its DAG edit; do not silently substitute a second copy or modify another repository.
3. Implement broker configuration, Keycloak client-credentials handling, idempotent registration/replay, capability verification, bounded run expiry, renewal, revocation, safe errors, health, and aggregate metrics.
4. Add repeatable secret/TLS provisioning, Compose profile wiring, readiness dependencies, and explicit Airflow lifecycle commands. Keep secret values out of output and make provisioners refuse unsafe replacement of existing files.
5. Implement DAG integration: register before Spark launch; pass only approved per-run values; preserve the main/uat Bundle selection; clean the container and revoke in success, failure, cancellation, and timeout paths.
6. Add focused broker/API/config checks and a contract check suitable for Unit 2's client. These checks do not expand the approved live-runtime verification boundary.
7. Build the pinned Airflow and broker images; verify profile startup, both Bundle registrations, and health without triggering a DAG. After Unit 2, execute the approved main `main-init_environment` E2E and record the UAT/concurrency/resilience exclusions.

## Acceptance checklist

- [x] Versioned broker API schema, examples, and compatibility contract are documented for Unit 2 consumption.
- [x] Registration is idempotent per stable Airflow DAG run; retry does not create or rotate an active capability; replay state is encrypted and bounded.
- [x] Renewal accepts only the matching active capability and fails closed after expiry, revocation, invalid token response, or broker state loss.
- [x] Broker obtains tokens only as `write-service-account`; writer secret is confined to broker-side secret mounts and does not appear in Spark environment, mounts, logs, image, API response, or XCom.
- [x] Control-plane registration/revocation is distinct from Spark renewal and requires the separate control credential over verified HTTPS.
- [x] Compose Airflow lifecycle is opt-in; broker has one worker, no host-published port, health endpoints, private metrics, and approved network memberships.
- [x] DAG cleanup removes the attempt's Spark container and revokes run authorization on terminal outcomes; cleanup failure remains bounded by run expiry.
- [x] Both existing Bundle registrations and refs remain intact; production E2E target remains `main-init_environment`.
- [x] Keycloak lifespan change is scoped to the writer client; issued-token expiry is validated at runtime by the broker.
- [x] No Polaris grants, RustFS policies, Jupyter identity behavior, persistent provider volumes, or unrelated workflows are changed.
- [x] Build/config/contract checks pass; live test results and explicitly deferred checks are recorded accurately (Build and Test stage).

## Clarification questions

Fill each `[Answer]:` tag. Recommendations establish a small, versioned, machine-checkable contract that Unit 2 can consume without depending on private implementation details.

### Question 1 — API contract artifact

Which format should be the authoritative broker contract for Unit 2 and the broker implementation?

A) OpenAPI 3.1 YAML checked into `infra/airflow-token-broker/openapi.yaml`, with request/response examples and a contract validation check (recommended; consumable by both Python projects and reviewable independently).

B) Markdown-only API documentation, with hand-maintained client/server agreement.

X) Other; describe after the answer tag.

[Answer]:A

### Question 2 — DAG-run identity and idempotency input

How should Airflow identify a registration without exposing credentials or making the client depend on broker memory internals?

A) Send `dag_id` and `run_id` as JSON fields to a control-authenticated registration endpoint. The broker validates lengths/character sets and derives its own stable idempotency key from the canonical pair; it returns an opaque random `run_handle` used by later calls (recommended; avoids unsafe IDs in URL paths and keeps the contract explicit).

B) Airflow generates and sends an opaque idempotency key, while the broker treats it as the sole run identity.

X) Other; describe after the answer tag.

[Answer]:A

### Question 3 — Renewal and revocation credential placement

Where should the run capability be sent, and how should control-plane revocation identify the run?

A) Send the capability only in the HTTPS `Authorization: Bearer` header to a renewal endpoint whose JSON body contains the opaque `run_handle`. Use the separate control credential for registration and revocation, with revocation also addressing `run_handle` (recommended; keeps run identity distinct from the secret capability and never places credentials in URLs or bodies).

B) Put the capability in the JSON body for renewal and use `dag_id`/`run_id` in the revocation path.

X) Other; describe after the answer tag.

[Answer]:A

### Question 4 — Response and error format

How should the contract represent token expiry and safe failures?

A) Return the access token and absolute UTC `expires_at` timestamp in a success response, and use RFC 9457 problem details with a small allow-listed error code set; never include upstream response bodies or secrets (recommended; clients can validate expiry consistently and errors stay machine-readable/sanitized).

B) Return token lifetime as integer seconds and use endpoint-specific ad hoc error JSON.

X) Other; describe after the answer tag.

[Answer]:A

### Question 5 — Broker API version compatibility

How should version changes be handled after Unit 2 starts consuming the contract?

A) Prefix routes with `/v1`; make incompatible changes require a new major route and keep the Unit 1 API contract pinned by the Spark runtime build (recommended; prevents silent drift across repositories).

B) Use unversioned routes and keep both clients upgraded in lockstep without an explicit compatibility marker.

X) Other; describe after the answer tag.

[Answer]:A
