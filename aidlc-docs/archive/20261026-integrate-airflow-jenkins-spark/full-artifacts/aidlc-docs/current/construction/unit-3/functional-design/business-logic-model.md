# Business Logic Model — Unit 3 Platform Compose Integration

## Scope

This model defines how Airflow 3, its dedicated metadata database, Jenkins, Git DAG Bundles, and the existing lakehouse Compose platform fit together. It describes service behavior and configuration responsibilities; it does not claim that the topology has been implemented or verified.

## Participants and responsibilities

- **Operator** configures deployment-specific values, starts/stops the Compose project, and uses the Airflow and Jenkins web interfaces.
- **Airflow API server** provides the Airflow UI and API. It has no Docker socket and no writer credentials.
- **Airflow DAG processor** fetches and parses the configured Git Bundle at an immutable revision. It shares the Bundle checkout path with the scheduler but has no Docker socket or writer credentials.
- **Airflow scheduler** runs LocalExecutor tasks, enforces the approved run admission policy, and owns Docker lifecycle operations for run containers. It receives the Docker socket and host path references required to request bind mounts; it does not receive writer secret values.
- **Airflow triggerer** supports deferrable Airflow tasks. It has no Docker socket or writer credentials.
- **Airflow initializer** performs Airflow metadata database migrations and configured bootstrap after the dedicated Airflow PostgreSQL is healthy. It has no Docker socket or writer credentials.
- **Airflow PostgreSQL** stores only Airflow metadata in a dedicated database and named volume.
- **Jenkins** runs repository validation only. It has persistent home storage and the approved Docker socket mount, but no Bundle publication, reference-update, or deployment responsibility.
- **Docker Engine** runs the Compose services and scheduler-created run containers. It resolves host-side bind paths, so the configured Bundle and credential paths must be meaningful to the Docker daemon host.
- **Git Bundles** preserve the sibling configuration: `lakehouse-main` tracks `main` and `lakehouse-uat` tracks `uat`. Each resolves to a pinned revision; the bundles create production/UAT DAGs but do not enable their disabled workloads.
- **Existing lakehouse services** continue to provide Spark, Kerberos, Hive Metastore, RustFS, PostgreSQL for Hive, JupyterHub, and StarRocks without losing their current configuration or state.

## Integrated startup flow

1. Compose starts the dedicated `airflow-postgres` service and waits for its health check.
2. `airflow-init` applies Airflow migrations and configured bootstrap. A failed initializer prevents the Airflow application services from starting as ready services.
3. The API server, LocalExecutor scheduler, DAG processor, and triggerer start after successful initialization. The API server is published at host port `8085`; no other Airflow service port is published.
4. Jenkins starts independently with its persistent home and its UI published at host port `8098`. The Jenkins inbound-agent port `50000` remains unpublished.
5. Airflow service health indicates process/API and metadata database readiness only. It does not prove Git access, valid Bundle configuration, Docker bind-path access, Kerberos readiness, Spark worker registration, or lakehouse query/write readiness.
6. Airflow control-plane availability is independent of temporary lakehouse service availability. A workload must fail closed if a required Spark, Kerberos, metastore, or object-store dependency is unavailable.

Airflow PostgreSQL and its volume are separate from the Hive Metastore PostgreSQL and its volume. Airflow initialization and teardown must not initialize, migrate, clear, or remove lakehouse data.

## Bundle and host path flow

1. Deployment configuration supplies the Git remote URL and credentials. The project has no configured target remote, so the design does not hard-code one.
2. The DAG processor resolves the configured `lakehouse-main` and `lakehouse-uat` Bundles to immutable revisions and parses both. `lakehouse-main` produces production DAG IDs with the `main-` prefix; `lakehouse-uat` produces UAT DAG IDs with the `uat-` prefix. Their workload configurations remain disabled until the respective endpoint and credentials are approved.
3. The DAG processor and scheduler share the same Bundle checkout directory at the same container path. The scheduler passes the host-visible path for the pinned revision to Docker Engine when creating a run driver.
4. The driver receives that exact revision through a read-only bind mount. The host path and container path are configured independently but must identify the same files from the DAG processor, scheduler, and Docker daemon perspectives.
5. `LAKEHOUSE_PROJECT_ROOT`, `LAKEHOUSE_BUNDLE_HOST_ROOT`, and `LAKEHOUSE_BUNDLE_CONTAINER_ROOT` make the relevant path boundaries explicit. Missing or inconsistent mappings stop the run before workload submission; there is no path fallback.
6. The ignored `.runtime/airflow-dag-bundles` directory is runtime checkout state, not maintained source. The sibling project's generated `.airflow-dag-bundles` cache is not copied into the target.

## Run integration boundary

Unit 2 defines run-scoped driver and worker lifecycle. Unit 3 supplies the Compose, network, path, and secret-reference wiring that allows that behavior to operate:

- Compose services use the existing network key `iceberg_net` with Docker network name `iceberg-poc-net`.
- Containers created by the scheduler join `iceberg-poc-net`; service DNS provides the existing Spark endpoint `spark:7077` and the configured lakehouse endpoints.
- Only the scheduler receives the Docker socket among Airflow services. Jenkins retains its separately approved socket mount. The API server, DAG processor, triggerer, initializer, and Airflow PostgreSQL receive no socket.
- Writer keytab and RustFS writer secrets remain host-owned files mounted read-only into run containers according to the Unit 2 contract. Airflow services and Jenkins do not receive writer secret values. The scheduler receives only the host file path information needed to request those bind mounts.
- Unit 2 owns run admission, readiness deadlines, worker decommission, and cleanup semantics; Compose service health is not a substitute for those checks.

## Jenkins validation flow

Jenkins validates repository changes against the configured project checks and stores its state in a dedicated persistent home volume. It does not deploy the Compose stack, publish a DAG Bundle, change Bundle references, or target UAT/production. Its Docker socket is retained by explicit design approval and therefore remains a host-control boundary for Infrastructure/NFR documentation.

## Persistence and lifecycle

- Airflow metadata persists only in the dedicated `airflow-postgres-data` volume.
- Jenkins configuration and job state persist only in `jenkins-home`.
- Airflow task logs use a separate persistent volume only if required by the selected Airflow service topology.
- Existing Hive, metastore database, KDC, RustFS, JupyterHub, Spark, and StarRocks named volumes remain owned by their current services and retain their contents.
- Normal Compose start/stop and service recreation do not remove named volumes. Destructive volume removal or reset is outside this integration's lifecycle.
- Bundle checkout data is ignored runtime state and can be recreated from the configured remote; it is not a lakehouse data volume.

## Network and exposure behavior

Airflow UI/API binds `8085:8080` and Jenkins UI binds `8098:8080` with no host IP, so both listen on all host interfaces. The Jenkins agent port is not published. No new host publication is added for Airflow PostgreSQL, Hive Metastore, Spark worker ports, Kerberos, or RustFS. The design does not add TLS termination; application authentication and host/network controls govern access.

## Failure behavior and observability

- Airflow metadata database or initialization failure blocks the Airflow service startup path and is reported through service health/logs.
- A missing Git remote/credential, disabled or unresolved Bundle, invalid path mapping, or Docker-inaccessible bind path fails before workload code is launched.
- Airflow or Jenkins process health does not imply workload readiness or a successful repository validation.
- Airflow logs may identify run ID, pinned Bundle revision, environment, lifecycle phase, and sanitized errors. They must not contain keytab contents, ticket contents, RustFS credentials, or secret-bearing command output.
- No message broker or external observability stack is introduced by this design.

## Decisions deferred to later stages

Image implementation details, deployment secret injection mechanism, health-check commands, and resource limits belong to NFR/Infrastructure Design and Code Generation. Integration tests must verify the host/container path mapping, Bundle pinning, network DNS, socket boundaries, persistence isolation, and failure behavior before the platform is considered accepted.
