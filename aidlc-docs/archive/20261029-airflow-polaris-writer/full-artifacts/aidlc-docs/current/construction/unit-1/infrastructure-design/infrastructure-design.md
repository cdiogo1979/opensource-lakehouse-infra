# Infrastructure Design — Unit 1 Airflow Writer Identity and Broker

**Status:** Approved by the user on 2026-10-29. Infrastructure questions Q1–Q6 are recorded as A.

## 1. Compose lifecycle

- Keep Airflow services behind the Compose `airflow` profile so existing Jupyter/core startup behavior does not change.
- Add `scripts/lakehouse.sh start-airflow`, `airflow-status`, and `stop-airflow` lifecycle commands. `start-airflow` ensures core dependencies (Keycloak, Polaris, RustFS, and databases) are started and healthy, then runs Airflow profile initialization and starts the Airflow services. It does not require JupyterHub to start.
- Define the Airflow service set already inventoried as deferred: `airflow-postgres`, `airflow-init`, `airflow-api-server`, `airflow-scheduler`, `airflow-dag-processor`, and `airflow-triggerer`; add the new `airflow-token-broker` service to the profile.
- Use a local Airflow executor appropriate to the existing scheduler-driven Docker workload. The scheduler/task execution process is the only Airflow process that needs the Docker socket and broker control credential. Keep Docker socket access away from API server, DAG processor, and triggerer.
- Preserve persistent Airflow metadata storage in a named volume. Do not remove or reset existing provider volumes as part of deployment.
- `stop-airflow` stops the profile's services without deleting named volumes or Bundle checkouts.

## 2. Broker image and process

- Build a dedicated minimal Python 3 broker image, separate from the Airflow image, with FastAPI, Uvicorn, async Keycloak HTTP, Prometheus client, and cryptography dependencies only.
- Pin the base image by immutable digest and pin direct/transitive Python dependencies in the implementation. Reuse Python 3.10 compatibility to match the existing pinned Airflow Python base unless dependency compatibility review establishes a need to change it.
- Start exactly one Uvicorn worker. The API server, scheduler, and broker remain separate processes; the broker owns all in-memory run state and ephemeral replay-encryption key material.
- Use the broker's internal HTTPS listener (port 8443) and private `/health/live`, `/health/ready`, and `/metrics` paths. Do not publish the broker port to the host.
- Configure Compose health checks according to the approved independent liveness/readiness semantics. Health responses remain sanitized.

## 3. Identity and secret wiring

### Writer credential

- Keep `.runtime/credentials/keycloak-writer-client-secret` as the one local source of truth. Configure it as a file-backed Compose secret mounted read-only only into `airflow-token-broker`.
- Broker configuration fixes the Keycloak realm and client ID (`lakehouse` and `write-service-account`); neither should be supplied by Spark.
- Update the Keycloak realm contract/bootstrap to set the one-hour access-token lifespan override on `write-service-account` only. Do not alter the realm-wide token lifetime or Jupyter client policy. Keycloak documents per-client Access Token Lifespan overrides in client Advanced Settings ([Keycloak Server Administration Guide](https://www.keycloak.org/docs/26.5.7/server_admin/)). Verify the issued JWT `exp` during the permitted functional checks.

### Airflow broker control credential

- Generate a separate high-entropy control secret at `.runtime/credentials/airflow-broker-control-token` with restrictive permissions and no stdout value.
- Mount that control secret read-only into the broker and only the Airflow scheduler/task-execution service that calls registration/revocation. Do not mount the writer client secret into Airflow scheduler services; do not mount either control secret into Spark.
- Airflow registration and revocation calls use the control credential over verified HTTPS. Broker endpoints reject unauthenticated control requests and redact authorization headers.

### Per-run Spark handoff

- Airflow obtains the initial writer JWT and opaque run capability from the broker, then supplies them as dedicated environment variables only when creating that run's ephemeral Spark container. The task returns only the Spark container name; never place token/capability values in XCom, command arguments, task logs, rendered templates, or persistent files.
- Spark receives the broker URL and CA certificate path as non-secret configuration. The client verifies TLS and presents the run capability only to the matching renewal endpoint.
- Docker daemon administrators can inspect configured container environment values. Treat access to the Docker daemon as privileged platform-administrator access; restrict it to the Airflow scheduler and trusted host administrators. The short-lived token remains subject to the approved one-hour expiry; capability revocation prevents later renewal but does not revoke an already-issued JWT.
- Spark does not receive the Keycloak writer client secret, broker control secret, Kerberos keytab, or long-lived RustFS root/writer keys for this workflow.

## 4. Docker network topology

- Add a private Compose `airflow-spark` bridge network with no host port publication.
- Add a private `airflow-internal` network for Airflow services and its metadata database. Attach the scheduler/task executor to both `airflow-internal` and `core`; keep the API server, DAG processor, triggerer, and metadata database on `airflow-internal` only.
- Attach the broker to `core` (Keycloak) and `airflow-spark` (Spark renewal). The Airflow scheduler reaches the broker over `core` for registration/revocation.
- Attach each Docker-launched Spark container to both `airflow-spark` (broker) and existing `data-access` (Polaris/RustFS). Do not rely on the default bridge or host-published broker port.
- Preserve existing provider memberships. Polaris and RustFS remain on `data-access`; no provider permissions or catalog/storage grants change.
- Airflow scheduler continues to use the host Docker socket and existing Bundle host/container path mapping to launch the ephemeral Spark container. The Spark container receives no host project credential mounts from the legacy Kerberos/RustFS writer-key set.

## 5. Git Bundle and DAG contract

- Keep the current Bundle validator and exact definitions unchanged: `lakehouse-main` tracks `main`, and `lakehouse-uat` tracks `uat`.
- Keep `main-init_environment` as the only runtime E2E target. UAT bundle parsing/configuration can be checked without executing UAT.
- Adapt the DAG factory in the sibling `opensource-lakehouse` repository to register the run before Spark startup, pass only per-run credentials to the container, and revoke the run and remove the container for success, failure, cancellation, and timeout.
- Preserve the configured sample-table overwrite behavior. Source changes must be committed and pushed to `main` for Bundle visibility; no other branch is a test target.

## 6. Startup and secret preparation order

`start-airflow` shall perform these local steps in order:

1. Run the existing runtime preparation and Keycloak bootstrap without displaying secret contents.
2. Run existing Airflow secret provisioning and create/check broker control and TLS material under ignored `.runtime` paths. Provisioning is idempotent and fails if an existing protected file is unsafe or malformed; it does not silently replace secrets.
3. Validate the exact Bundle configuration and required source checkout paths.
4. Build the Airflow image and the separate broker image.
5. Start and health-check metadata Postgres and platform dependencies.
6. Initialize Airflow metadata once, then start API server, scheduler, DAG processor, triggerer, and broker.
7. Verify both expected Bundle DAG registrations and report the production and UAT DAG IDs without running either DAG.

The implementation must not print credential values, access tokens, capabilities, private keys, or full sensitive API bodies.

## 7. NFR and scope traceability

| Approved item | Infrastructure coverage |
|---|---|
| NFR-1 / NFR-7 | Broker/client settings remain 5-second timeout, p95 target, bounded renewal; implementation verifies without load certification. |
| NFR-2 | One-worker broker image with capacity target of ten registrations; no concurrent-load test. |
| NFR-3 | Minimal separate broker image and Compose service. |
| NFR-4 | Read-only file-backed CA/server cert mounts; no host-published broker listener; Spark uses verified service DNS. |
| NFR-5 | Health endpoints and private aggregate `/metrics`; no sensitive labels or logs. |
| NFR-6 | In-memory state only; Compose restart cannot restore capabilities; fail closed. |
| NFR-8 | Main workflow runtime E2E only; UAT config/source check only. |
| FR-2 | Bundle names, refs, validator, and selection behavior unchanged. |
| FR-3–FR-6 | Writer-only Keycloak client, broker secret custody, per-run handoff, Polaris bearer identity, and vended RustFS credentials. |

## Deferred to Code Generation

- Resolve exact broker image digest and package versions against the local platform's supported architecture.
- Confirm the exact Keycloak Admin API representation for the client-specific token lifespan using the pinned Keycloak release, then enforce it idempotently without touching human-client policy.
- Define exact secret file modes/ownership, HTTPS request schemas, environment variable names, Spark container network connect/disconnect sequence, Compose service health check commands, and startup script behavior.
- Add focused unit/configuration checks. Runtime verification remains within the previously approved scope.
