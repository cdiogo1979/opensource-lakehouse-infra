# Unit 1 Infrastructure Design Plan — Airflow Writer Identity and Broker

## Approved inputs and fixed contract

Unit 1 NFR Design is approved. The following are fixed and not reopened here:

- Airflow 3 uses the existing pinned image base and services already inventoried for deferred integration; Airflow must be operable from v2 Compose.
- Git Bundles remain exactly `lakehouse-main` → `main` and `lakehouse-uat` → `uat`; do not change names, refs, validation, or selection behavior.
- Keycloak `write-service-account` gets the one-hour writer-token override; Jupyter human token lifetimes and Polaris grants stay unchanged.
- The writer client secret is consumed only within the Airflow trust boundary. The scheduler/DAG implementation registers and revokes runs; Spark gets only its per-run authorization and initial token.
- Run the broker as one Uvicorn worker with in-memory state. Use dedicated verified HTTPS, a dedicated CA, private metrics, and the approved health semantics.
- Replace legacy Spark Kerberos/keytab and long-lived RustFS writer-key use for this workflow with Keycloak/Polaris authorization and Polaris-vended storage credentials.
- Runtime E2E remains `main-init_environment`; UAT runtime, concurrent workload, and resilience tests remain excluded.

## Assessment plan

- [x] Review approved application, functional, NFR, and NFR design artifacts.
- [x] Inspect current Compose lifecycle, Airflow image and secret provisioning, Keycloak writer-secret path, and production DAG runtime mounts.
- [x] Resolve the six infrastructure choices below; ensure answers preserve the Bundle contract and secret boundary.
- [x] Prepare `infrastructure-design.md` and `service-topology.md`.
- [x] Validate Compose/service/startup paths, trust boundaries, and NFR traceability; artifacts are ready for approval before Code Generation planning.

## Clarification questions

Fill each `[Answer]:` tag. Recommendations use existing v2 Compose conventions and preserve the current `scripts/lakehouse.sh start` behavior unless Airflow is explicitly requested.

### Question 1 — Airflow activation in the Compose lifecycle

How should operators start Airflow while keeping the existing core/Jupyter startup path predictable?

A) Add an `airflow` Compose profile and explicit `scripts/lakehouse.sh start-airflow`, `airflow-status`, and `stop-airflow` commands. Keep the existing `start` command's service set unchanged (recommended; avoids making every local Jupyter startup pay the Airflow/Postgres cost).

B) Start Airflow automatically from the existing `scripts/lakehouse.sh start` command.

X) Other; describe after the answer tag.

[Answer]:A

### Question 2 — Broker container image

How should the broker be packaged relative to Airflow?

A) Build a minimal, separately pinned Python broker image with only the FastAPI/Uvicorn, Keycloak HTTP, metrics, and cryptography dependencies it needs. Keep it a separate Compose service and one worker (recommended; isolates the secret-handling API from Airflow's broader runtime dependencies).

B) Reuse the custom Airflow image for the broker service with a different command.

X) Other; describe after the answer tag.

[Answer]:A

### Question 3 — Source and scope of the writer client secret

How should the broker receive the client secret already used by the Keycloak bootstrap?

A) Reuse `.runtime/credentials/keycloak-writer-client-secret` as the single local source of truth and expose it to the broker as a read-only Compose secret. Do not mount it into scheduler, DAG processor, API server, or Spark (recommended; avoids duplicate secret copies).

B) Create a second Airflow-specific copy of the writer client secret.

X) Other; describe after the answer tag.

[Answer]:A

### Question 4 — Airflow control-plane authentication to the broker

How should Airflow authenticate registration and revocation calls, separately from Spark's per-run capability?

A) Generate a separate high-entropy broker-control secret under ignored `.runtime` credentials and mount it read-only only into the Airflow task-execution process and broker. Use it for registration/revocation; never give it to Spark (recommended; keeps admin operations distinct from run-scoped renewals).

B) Reuse the Keycloak writer client secret as the broker API credential.

X) Other; describe after the answer tag.

[Answer]:A

### Question 5 — Per-run token handoff to Spark

How should Airflow pass the initial writer JWT and run capability to the ephemeral Spark container?

A) Inject them as dedicated environment variables when creating the per-run Spark container, never as command-line arguments or XCom values. Treat Docker daemon access as privileged; redact values from logs and error messages, and do not copy them to persistent files (recommended; matches the current Docker-based task launch and avoids host-side credential staging).

B) Write them to a short-lived host file and bind-mount the file read-only into Spark, deleting it after container startup.

X) Other; describe after the answer tag.

[Answer]:A

### Question 6 — Docker network topology for the broker and Spark

How should Spark reach both the broker and Polaris while Airflow controls the run?

A) Add a private `airflow-spark` network. Attach the broker to `core` (Keycloak and Airflow control traffic) and `airflow-spark`; attach only the Airflow scheduler/task executor to `core`; connect each Spark container to `airflow-spark` and the existing `data-access` network (Polaris/RustFS). Publish no broker host port (recommended; separates writer renewal from Jupyter's network).

B) Attach the broker and Spark to the existing shared `data-access` network only.

X) Other; describe after the answer tag.

[Answer]:A

## Applicability and boundaries

- Broker health checks, TLS mounts, secret source, one-worker setting, and startup order apply and are addressed here.
- The one-hour writer override is already approved; implementation details must be checked against the pinned Keycloak behavior during code/design work.
- Bundle content and refs are immutable in this intent. Airflow's local host bundle path and Docker socket access are retained only as required by the existing Compose/DAG execution model.
- No live services, credentials, certificates, bundles, or production data are changed during this planning step.
