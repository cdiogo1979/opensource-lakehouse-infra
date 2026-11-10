# Unit 1 NFR Requirements

## Scope and Operating Context

These requirements apply to the local Compose foundation: Hive Metastore, metastore PostgreSQL, Kerberos KDC, RustFS, bucket initialization, and lifecycle orchestration. This is an isolated development PoC for one operator, two query identities, and one writer. It is not a production service and has no external identity provider.

## Capacity and Scalability

- **U1-NFR-01**: Support one local Docker Compose host, two test query identities, one writer, and the existing small TPCH demonstration workload.
- **U1-NFR-02**: No horizontal scaling, multi-host deployment, or independent service scaling target is required.
- **U1-NFR-03**: Capacity limits beyond the demonstration workload are not an acceptance requirement; resource requirements should be documented for the selected images if they prevent a local start.

## Performance

- **U1-NFR-04**: Prioritize correct, repeatable initialization and query access over response-time optimization.
- **U1-NFR-05**: No startup-time, query-latency, throughput, or benchmark SLA is required for this PoC.

## Availability and Recovery

- **U1-NFR-06**: The environment is single-host best effort. No HA, service failover, uptime target, or disaster-recovery objective is required.
- **U1-NFR-07**: Named volumes preserve local catalog and object-store state across stop/start. Recovery is operator-managed and follows the Functional Design's safe-rerun rules.
- **U1-NFR-08**: A full reset is an explicit destructive operation; it is not an availability or recovery mechanism invoked automatically.

## Security and Exposure

- **U1-NFR-09**: Keep service interfaces local to the development host. Host-published ports should bind to loopback unless an explicitly reviewed requirement changes the boundary.
- **U1-NFR-10**: Generated keytabs, Kerberos passwords, RustFS credentials, and native service credentials remain in ignored local runtime storage with restricted host access; never commit or bake them into images.
- **U1-NFR-11**: Logs and status output may identify principal/account names and operation outcomes but must not disclose secret values or keytab contents.
- **U1-NFR-12**: Keep component credentials separate. Kerberos keytabs are not reused as RustFS S3 keys, PostgreSQL passwords, or Dremio web/JDBC passwords.
- **U1-NFR-13**: Do not claim production security. DummyAuthenticator and the disposable KDC are local development mechanisms.
- **U1-NFR-14**: The existing requirement that storage-based Metastore authorization preserve effective-user outcomes for both Dremio and Spark remains a feasibility gate; this NFR document does not certify it.

## Technology Compatibility

- **U1-NFR-15**: Preserve the existing pinned Spark and Dremio versions where compatible. Any necessary change to those baseline versions must be documented and reviewed before implementation.
- **U1-NFR-16**: Select a Hive 3.x release, PostgreSQL version, and compatible service images only after checking the exact Spark Hive Metastore client/JAR configuration, Hive schema, Dremio Hive 3.x support, and RustFS integration.
- **U1-NFR-17**: A technically convenient version combination is not acceptable if it loses the required Kerberos/effective-user or catalog behavior. Incompatibilities are reported with the smallest proposed adjustment for review.

## Reliability and Observability

- **U1-NFR-18**: Required dependencies expose readiness sufficient to prevent dependent Hive initialization, ETL, and authorization scenarios from running prematurely.
- **U1-NFR-19**: Fail dependent startup promptly when KDC, metastore schema, bucket, or required permission setup fails. Do not report the overall platform as ready while a required foundation step is failed.
- **U1-NFR-20**: Retry only operations designed to be safe and idempotent. Preserve persistent data and leave recovery to the operator after failure.
- **U1-NFR-21**: Initialization output reports the component/step and whether it was created, already present, ready, or failed, without secret values.
- **U1-NFR-22**: No monitoring stack or alerting service is required. Local container health and actionable logs/status are sufficient for the demonstration.

## Maintainability and Usability

- **U1-NFR-23**: Keep configuration grouped by component and use the existing Compose project organization.
- **U1-NFR-24**: Document prerequisites, startup, stop-only behavior, destructive full reset, persistent state, and recovery after a failed initialization.
- **U1-NFR-25**: Operators use shell lifecycle scripts and documented Compose commands. No custom administration UI is required.
- **U1-NFR-26**: Startup/status output includes local service URLs where useful and states which required services are not ready.

## Explicitly Excluded NFR Targets

- Production availability, disaster recovery, and multi-region behavior.
- Horizontal scaling and performance benchmarking.
- External or enterprise identity management.
- Monitoring/alerting infrastructure and a custom operator UI.
- Network access from a trusted LAN or other hosts.
