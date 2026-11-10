# Business Rules — Unit 3 Platform Compose Integration

## Startup and ownership

**BR-3-01 — Dedicated Airflow metadata store.** Airflow uses its own PostgreSQL service and named data volume. It must not use or alter the Hive Metastore PostgreSQL database or volume.

**BR-3-02 — Initialization gates Airflow services.** Airflow migrations and bootstrap complete successfully after Airflow PostgreSQL is healthy and before API server, scheduler, DAG processor, and triggerer are treated as ready.

**BR-3-03 — Lakehouse availability is a run-time dependency.** Airflow control-plane services may be healthy while lakehouse services are unavailable. Each run must independently fail closed when a required service is unavailable.

**BR-3-04 — Health checks have limited meaning.** Service/process/API health does not establish Git, Bundle, Docker path, Kerberos, Spark, metastore, RustFS, or workload readiness.

## Bundle configuration and path safety

**BR-3-05 — Preserve the maintained Bundle channels.** Airflow configures exactly `lakehouse-main` tracking `main` and `lakehouse-uat` tracking `uat`, matching the existing sibling configuration. The main bundle creates production DAGs; UAT creates UAT DAGs. Their workload configs remain disabled until each environment has an approved endpoint and credential set.

**BR-3-06 — No environment fallback.** A missing or invalid requested environment fails closed. It must never silently route a UAT or production request to development.

**BR-3-07 — Deployment-owned remote.** The Git remote URL and credentials are deployment inputs because no target remote is configured in the project. They must not be invented or committed as operational secrets.

**BR-3-08 — Immutable run input.** A run uses the exact Bundle revision resolved by the DAG processor; the driver receives that pinned revision through a read-only mount. A moving branch checkout is not substituted during a run.

**BR-3-09 — Identical Bundle path view.** The DAG processor and scheduler mount the shared Bundle storage at the same container path. The scheduler's Docker bind source must be a host path that Docker Engine can resolve and must identify the same pinned files.

**BR-3-10 — Explicit path mapping.** `LAKEHOUSE_PROJECT_ROOT`, `LAKEHOUSE_BUNDLE_HOST_ROOT`, and `LAKEHOUSE_BUNDLE_CONTAINER_ROOT` define the host/container mapping. Missing, unreadable, or inconsistent paths fail before submission; no inferred alternate path is allowed.

**BR-3-11 — Runtime cache is not source.** Runtime `.airflow-dag-bundles` checkout/cache contents from the sibling project are not copied or treated as maintained project source.

## Credential boundaries

**BR-3-12 — No weak default administrator.** Airflow bootstrap must not reuse the sibling stack's `admin/admin` credentials. Bootstrap/API/Fernet secrets are supplied through a protected deployment mechanism and are not embedded as source-controlled secret values.

**BR-3-13 — Writer credentials are run-container inputs only.** Writer keytab and RustFS writer secret values are not mounted into Airflow API server, DAG processor, triggerer, initializer, Jenkins, or Airflow PostgreSQL.

**BR-3-14 — Scheduler receives paths, not writer values.** The scheduler may receive host file path references needed to create Docker bind mounts, but must not receive writer keytab or RustFS secret contents as ordinary environment variables or configuration values.

**BR-3-15 — Read-only host credential mounts.** Run containers receive only the approved host credential files as read-only mounts, retaining restrictive host file permissions and the Unit 2 private ticket-cache contract.

**BR-3-16 — Sanitized diagnostics.** Logs and errors must not expose credential values, keytab/ticket contents, or raw secret-bearing command output.

## Docker and network boundaries

**BR-3-17 — Airflow socket isolation.** Among Airflow services, only the scheduler receives Docker Engine socket access. API server, DAG processor, triggerer, initializer, and PostgreSQL do not.

**BR-3-18 — Approved Jenkins socket.** Jenkins retains its separately approved Docker socket mount. Its broad host-control implications must be documented in the later security/NFR and infrastructure materials.

**BR-3-19 — Shared network identity.** Compose uses network key `iceberg_net` and Docker network name `iceberg-poc-net`; scheduler-created run containers explicitly join the same Docker network.

**BR-3-20 — Preserve service discovery.** Existing lakehouse service names and internal endpoints remain the integration contract, including Spark master `spark:7077`. Any required endpoint failure is surfaced as a run failure rather than routed to a fallback service.

## Service scope and exposure

**BR-3-21 — Jenkins is validation-only.** Jenkins may run repository validation but does not deploy Compose, publish Bundles, mutate Bundle references, or enable UAT/production deployment.

**BR-3-22 — Airflow UI binding.** Publish the Airflow UI/API as `8085:8080` with no host IP, binding all host interfaces.

**BR-3-23 — Jenkins UI binding.** Publish Jenkins UI as `8098:8080` with no host IP, binding all host interfaces. Do not publish Jenkins inbound-agent port `50000`.

**BR-3-24 — No new service exposure.** Do not add host ports for Airflow PostgreSQL, Hive Metastore, Spark worker ports, Kerberos, or RustFS beyond the current Compose bindings.

**BR-3-25 — No TLS termination in Compose.** UI traffic remains HTTP at this layer. This design does not provide a TLS proxy or claim production-grade remote exposure.

## Persistence and preservation

**BR-3-26 — Dedicated persistent ownership.** Airflow PostgreSQL data and Jenkins home use separate named volumes. Airflow logs use a separate volume only if required by the selected topology.

**BR-3-27 — Preserve lakehouse state.** Existing lakehouse service configuration, published ports, credential sources, network membership, and named data volumes remain unchanged and retain their contents.

**BR-3-28 — No implicit volume reset.** Normal start, stop, and recreation do not remove named volumes or reset lakehouse state. Volume deletion/reset is outside this unit's behavior.

## Verification boundary

**BR-3-29 — Design claims require runtime evidence.** Compose health alone does not prove Bundle pinning, socket isolation, host bind-path resolution, credential isolation, DNS connectivity, or workload access. Those behaviors remain Build and Test acceptance items.

**BR-3-30 — No performance claim.** This unit introduces no throughput, latency, or capacity guarantee beyond previously approved run concurrency and readiness/cleanup requirements.
