# Infrastructure Design — Unit 3 Platform Compose Integration

## Purpose and Scope

Integrate Airflow 3.3.2, its isolated PostgreSQL metadata service, Git DAG Bundles, and validation-only Jenkins into the target Docker Compose lakehouse. Preserve all existing lakehouse service definitions, host ports, credentials, networks, and persistent volumes. Unit 3 connects the approved Unit 1/2 Spark runtime contracts; it does not redefine run readiness or driver/worker cleanup.

This is an infrastructure design, not implementation evidence. No Compose service was changed or started and no tests were run.

## Existing Platform and Preservation Boundary

The existing Compose project defines the `iceberg_net` key with Docker network name `iceberg-poc-net`. It includes KDC, Hive schema initialization and metastore, metastore PostgreSQL, RustFS and bucket initialization, Spark, JupyterHub, TPCH tools, and optional StarRocks services. Existing host publications include loopback-only RustFS, Spark, JupyterHub, and StarRocks ports; these remain unchanged.

Existing named volumes and their ownership are preserved: `object-store-data`, `metastore-db-data`, `kerberos-kdc-data`, JupyterHub and user work volumes, and StarRocks FE/BE state volumes. Unit 3 adds separate Airflow PostgreSQL and Jenkins home volumes. No volume reset/removal is part of startup, update, stop, or teardown.

JupyterHub already mounts `/var/run/docker.sock` to launch notebook containers. This existing lakehouse boundary remains unchanged. Unit 3 adds socket mounts only to the Airflow scheduler and approved Jenkins service; no other Airflow component receives one. The sockets on JupyterHub and Jenkins provide broad Docker-host control and must not be described as least-privilege isolation.

## Service Topology

| Service | Image/configuration ownership | Dependencies and network | Host exposure / storage / socket |
|---|---|---|---|
| `airflow-postgres` | Dedicated PostgreSQL 16 service using the existing digest-pinned Postgres image version | `iceberg_net`; local health via `pg_isready` | No host port; `airflow-postgres-data`; no socket/secrets beyond its DB password |
| `airflow-init` | Same target-built Airflow image and provider constraints as the application components | Waits for `airflow-postgres` healthy; validates required secret files; performs migration and admin bootstrap; `iceberg_net` | One-shot; no socket, writer secrets, or published port |
| `airflow-api-server` | Same target-built Airflow 3.3.2 image | Waits for successful initializer; `iceberg_net` | `8085:8080` on all host interfaces; Airflow log volume if needed; no socket/writer secrets |
| `airflow-scheduler` | Same target-built Airflow image; LocalExecutor | Waits for successful initializer; `iceberg_net`; Docker Engine API for run-container creation/cleanup | Docker socket; shared Bundle path; path references required by Unit 2; no writer secret values; no published port |
| `airflow-dag-processor` | Same target-built Airflow image with Git Bundle provider | Waits for successful initializer; `iceberg_net`; configured Git remote egress | Shared read/write Bundle checkout; no socket/writer secrets; no published port |
| `airflow-triggerer` | Same target-built Airflow image | Waits for successful initializer; `iceberg_net` | No socket/writer secrets; no published port |
| `jenkins` | Jenkins LTS image pinned to an immutable digest at implementation; validation-only configuration | `iceberg_net`; Git egress as required | `8098:8080` on all host interfaces; persistent `jenkins-home`; approved Docker socket; no agent port 50000 and no writer secrets |

Airflow control components use a separate Airflow image based on the official Apache Airflow 3.3.2 Python 3.10 image family, with required Git, Docker, FAB, and PostgreSQL providers installed under the matching Airflow constraints. Pin the exact parent digest and provider resolution during Code Generation. Do not derive the Airflow control image from the Spark image: scheduler-launched Spark containers use the existing `local/spark-iceberg:3.5.5_1.8.1-krb5` image and the Airflow control plane does not need Spark binaries. Do not copy the sibling's `admin/admin`, blank Fernet key, AWS defaults, published SSH port, or Jenkins agent publication.

Use the existing Jenkins validation service scope; do not add a Jenkins agent listener, Bundle publishing, ref update, Compose deployment, or writer credentials. Any Jenkins package/plugin needed by the validation pipeline must be justified by that pipeline and pinned; the sibling Dockerfile's unpinned `apt-get install docker.io` is not copied by default because Docker socket access is already provided and validation-only does not establish a need for a second daemon/client installation.

## Startup, Health, and Failure Wiring

1. Airflow PostgreSQL starts with a local `pg_isready` probe every 10 seconds, timeout five seconds, retry threshold three failures.
2. `airflow-init` starts after PostgreSQL is healthy. It validates required Airflow bootstrap/API/Fernet secret sources and process readability before database migration/bootstrap. Failure exits nonzero and blocks Airflow application services.
3. API server, scheduler, DAG processor, and triggerer start only after successful initialization.
4. Airflow API health uses Airflow 3.3.2's `/api/v2/version` endpoint for API-process readiness and a separate monitor-health JSON inspection where component status is needed. Configure a `240s` API `start_period` with the approved `10s` interval, `5s` timeout, and three-failure threshold; verify that the resulting unhealthy transition occurs within five minutes after the dependencies are satisfied. Do not infer overall component health from `/api/v2/monitor/health` HTTP status alone: the endpoint may return HTTP 200 while reporting an unhealthy component. Verify exact health fields against the pinned Airflow version during Build and Test.
5. Jenkins health is independent and uses a local HTTP readiness check supported by the pinned Jenkins image. Do not couple Jenkins health to Git remote, Airflow, or Docker workload availability.
6. API becomes healthy within five minutes after both PostgreSQL healthy and successful initialization. A deadline monitor records a sanitized unhealthy result; no automatic restart or resource escalation is added by this design.
7. PostgreSQL, API, and Jenkins probes use 10-second intervals, five-second timeout, and three consecutive failures. Health probes do not mount secrets or invoke external systems.

The Airflow official health documentation identifies `/api/v2/monitor/health` as a component health endpoint but warns that its HTTP response code only indicates the REST request succeeded; inspect its returned component statuses rather than treating HTTP 200 as full health. `/api/v2/version` is suitable for API process responsiveness. (References are listed below.)

## Git Bundle, Host Paths, and Revision Retention

- Preserve the maintained two-entry Git Bundle list: `lakehouse-main` tracks `main` and `lakehouse-uat` tracks `uat`, both use the sibling repository URL, `lakehouse_git`, 300-second refresh, and sparse dirs `dags`, `configs`, and `notebooks`. `lakehouse-main` creates production DAGs with the `main-` prefix; `lakehouse-uat` creates UAT DAGs with the `uat-` prefix. Their workload configurations remain disabled and fail closed.
- Configure one ignored runtime checkout root under the target project, e.g. `.runtime/airflow-dag-bundles`. This is generated Airflow runtime data, not source. Do not copy the sibling project's `.airflow-dag-bundles` cache.
- Set required absolute path inputs `LAKEHOUSE_PROJECT_ROOT`, `LAKEHOUSE_BUNDLE_HOST_ROOT`, and `LAKEHOUSE_BUNDLE_CONTAINER_ROOT`. Mount the Bundle storage into the DAG processor and scheduler at the same absolute container path. The Docker daemon must resolve the host path to the same checkout; the scheduler passes the host path for a pinned revision to the driver as a read-only bind mount.
- Validate paths before workload launch. A missing/non-absolute/mismatched mapping fails closed; do not fall back to a container-only path or a second checkout.
- Airflow Git Bundles track a run's bundle version and the Git provider maintains local bare/revision checkouts. This design does not add custom cleanup based only on directory age. Automatic pruning is disabled in the initial integration unless Code Generation can demonstrate an authoritative active-run reference source and a shared atomic coordination protocol across checkout publication, run pinning, and deletion. The 30-day rule defines eligibility only after safety is proven; otherwise retain revisions and report storage growth for operator review. Never mutate remote refs.

## Secret and Identity Wiring

- Add deployment-managed file references under ignored runtime credential state for the Airflow admin bootstrap password, API secret, and Fernet key. Do not create or commit secret values in this stage. Git credentials are optional when the deployment remote is public.
- Require host mode `0600` and read-only container mounts. Align file ownership/UID/GID with the Airflow process so it can read the files without relaxing permissions. Initialization fails when any required secret is missing or unreadable.
- Store the administrator account identifier separately from its password; do not reuse weak sibling defaults. The admin user is created idempotently by the one-shot initializer.
- PostgreSQL receives its own file-backed database password. Airflow connection/secret configuration must not reuse the Hive metastore database or its password.
- Writer keytab and RustFS writer secrets remain mounted only into the Unit 2 run driver/worker containers under the existing read-only paths. Airflow scheduler may receive mount path strings, not credential contents. API server, DAG processor, triggerer, initializer, Jenkins, and Airflow PostgreSQL receive no writer credential values.
- Never log secret contents, Kerberos tickets, or raw secret-bearing command output. Health-check output contains only service status.

## Network and Host Exposure

- All integrated Compose services join `iceberg_net`; its Docker name remains `iceberg-poc-net`.
- Airflow scheduler-created run containers explicitly join `iceberg-poc-net` and use existing service DNS, including `spark:7077`, `hive-metastore:9083`, and `object-store:9000` as required by Unit 2.
- Airflow PostgreSQL remains internal and has no published port. No new host ports are added for Hive Metastore, Spark workers, Kerberos, or RustFS.
- Publish Airflow as `8085:8080` and Jenkins as `8098:8080` without a host IP, preserving the selected all-interface binding. Do not publish Jenkins agent port `50000`.
- The UI links use HTTP. Compose provides no TLS termination. Preserve application authentication and document the existing all-interface exposure.

## Persistence and Resource Impact

| State | Volume/path | Owner | Lifecycle |
|---|---|---|---|
| Airflow metadata | New `airflow-postgres-data` named volume | `airflow-postgres` | Survives ordinary container recreation and Compose stop/start; no backup/restore guarantee |
| Jenkins config/jobs | New `jenkins-home` named volume | `jenkins` | Survives ordinary container recreation and Compose stop/start; no backup/restore guarantee |
| Airflow task logs | Separate named volume if required by image/service topology | Airflow | No lakehouse data; retention can be operator-managed |
| Bundle revisions | Ignored `.runtime/airflow-dag-bundles` host path | DAG processor/scheduler | Re-fetchable runtime data; no unsafe automated pruning |
| Existing lakehouse data | Existing named volumes | Existing services | Unchanged; never reset by Unit 3 |

No fixed CPU/memory limits or performance/capacity guarantee is added. The Airflow metadata service is isolated from the metastore DB. No backup service, message broker, proxy, or monitoring stack is introduced.

## Docker Socket Boundaries

| Component | Socket | Reason / boundary |
|---|---|---|
| Airflow scheduler | Yes | Docker lifecycle for Unit 2 per-run driver/worker |
| Jenkins | Yes, approved | Retained CI configuration; broad host-control capability |
| JupyterHub | Existing mount retained | Existing notebook-container lifecycle; not introduced by this unit |
| Airflow API server, DAG processor, triggerer, initializer, PostgreSQL | No | No Docker operation required |
| Other existing lakehouse services | No change | Preserve current Compose configuration |

Do not describe a Docker socket mount as a security sandbox or least-privilege boundary. Verify mounts from rendered Compose configuration and container inspection at Build and Test.

## Build and Test Verification Items

- Render Compose and inspect service merge results without creating/removing volumes; prove all existing services, ports, networks, credentials, and named volume declarations remain present.
- Confirm only approved Airflow components get socket access, while the existing JupyterHub mount remains unchanged; verify Jenkins socket and no port 50000.
- Verify PostgreSQL/init dependency ordering, all health-check timings, API five-minute startup bound, and component-health parsing.
- Verify Airflow and Jenkins named-volume persistence through ordinary recreation, separate from metastore/object-store volume data.
- Verify secret file modes, UID/GID readability, read-only mounts, missing-secret fail-closed behavior, and sanitized diagnostics.
- Verify Git path identity from DAG processor, scheduler, and Docker daemon; verify read-only pinned Bundle mount.
- Run `scripts/verify-airflow-environment-dags.sh` and require `main-init_environment` from `lakehouse-main` and `uat-init_environment` from `lakehouse-uat`; registration is required while UAT/prod workload execution stays disabled.
- Confirm automated Bundle pruning remains disabled unless an implementation demonstrates race-safe active-reference coordination; test no active pinned revision is removed.
- Verify all integrated services and per-run containers resolve the existing service names over `iceberg-poc-net`.
- Re-run the Unit 2 workload readiness, credential isolation, and cleanup checks; Unit 3 health must not substitute for them.

## References

- [Airflow 3.3.2 health status documentation](https://airflow.apache.org/docs/apache-airflow/3.3.2/administration-and-deployment/logging-monitoring/check-health.html) — health endpoints and interpretation.
- [Airflow Git Bundle provider documentation](https://airflow.apache.org/docs/apache-airflow-providers-git/stable/bundles/index.html) — Git Bundle configuration and version behavior.
- [Airflow Git provider API reference](https://airflow.apache.org/docs/apache-airflow-providers-git/stable/_api/airflow/providers/git/bundles/git/index.html) — GitDagBundle tracking and local checkout model.
