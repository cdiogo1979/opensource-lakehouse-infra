# Domain Entities — Unit 3 Platform Compose Integration

## Airflow Platform Deployment

Represents the Compose-managed Airflow 3 control plane and its service relationships.

**Attributes**
- `api_server`: UI/API service, published on host port 8085.
- `scheduler`: LocalExecutor coordinator; owns Airflow Docker lifecycle operations.
- `dag_processor`: resolves and parses Git Bundle revisions.
- `triggerer`: supports deferrable tasks.
- `initializer`: performs migrations and configured bootstrap.
- `network_key`: `iceberg_net`.
- `docker_network`: `iceberg-poc-net`.

**Invariants**
- Airflow services depend on successful Airflow metadata database initialization.
- Only the scheduler receives the Docker socket among Airflow services.
- Airflow service health is distinct from workload readiness.

## Airflow Metadata Store

The PostgreSQL database and dedicated persistent storage used only for Airflow metadata.

**Attributes**
- `service_name`: `airflow-postgres`.
- `database_volume`: dedicated `airflow-postgres-data` named volume.
- `published_host_port`: none.

**Invariants**
- It is not shared with Hive Metastore PostgreSQL.
- Airflow initialization does not mutate lakehouse metadata or data.

## Bundle Deployment Configuration

Describes the deployment-specific Git Bundle source and environment selection.

**Attributes**
- `remote_url`: deployment-supplied Git URL.
- `git_credentials_reference`: deployment-supplied protected reference; no credential value is modeled here.
- `configured_bundles`: `lakehouse-main` (production DAGs) and `lakehouse-uat` (UAT DAGs), preserving the maintained sibling list.
- `tracking_reference`: configured deployment input resolved to a pinned revision for each run.
- `disabled_execution_environments`: UAT and production until explicitly configured; DAG registration does not enable workload execution.

**Invariants**
- A run executes the immutable revision resolved for that run.
- Missing source or environment configuration fails closed.
- No environment silently falls back to dev.

## Bundle Storage Mapping

Represents the relationship between host-visible checkout storage and container paths.

**Attributes**
- `project_root`: `LAKEHOUSE_PROJECT_ROOT`.
- `bundle_host_root`: `LAKEHOUSE_BUNDLE_HOST_ROOT`.
- `bundle_container_root`: `LAKEHOUSE_BUNDLE_CONTAINER_ROOT`.
- `runtime_location`: ignored project runtime state, such as `.runtime/airflow-dag-bundles`.
- `consumer_services`: DAG processor and scheduler.
- `docker_daemon_host_path`: source path supplied for driver bind mounts.

**Invariants**
- DAG processor and scheduler use the same absolute container path.
- The Docker daemon resolves the host bind source to the same pinned revision.
- The run driver receives the pinned Bundle read-only.
- Missing or mismatched mappings prevent submission.

## Docker Control Boundary

Records which components can create or control containers through the Docker Engine socket.

**Attributes**
- `airflow_scheduler`: approved socket consumer for run-container lifecycle.
- `jenkins`: separately approved socket consumer for validation workflows.
- `airflow_api_server`: no socket.
- `airflow_dag_processor`: no socket.
- `airflow_triggerer`: no socket.
- `airflow_initializer`: no socket.
- `airflow_postgres`: no socket.

**Invariants**
- Scheduler-created run containers join `iceberg-poc-net`.
- Socket access conveys broad Docker-host control and must not be inferred to be least privilege.

## Runtime Credential Reference

Represents host-owned file references used to create run-container mounts without carrying secret values in Airflow configuration.

**Attributes**
- `writer_keytab_host_path`: host path reference only.
- `rustfs_access_key_host_path`: host path reference only.
- `rustfs_secret_key_host_path`: host path reference only.
- `mount_mode`: read-only.
- `consuming_containers`: Unit 2 run driver and worker containers.
- `scheduler_visibility`: paths needed to request Docker binds; no writer secret contents.

**Invariants**
- Airflow API server, DAG processor, triggerer, initializer, Jenkins, and Airflow PostgreSQL do not receive writer credentials.
- Secret values are not stored in this entity or emitted in diagnostics.
- Each run container retains its Unit 2 private Kerberos ticket cache behavior.

## Jenkins Validation Service

Represents Jenkins as a repository validation service, separate from Airflow workload scheduling.

**Attributes**
- `ui_host_port`: 8098 on all host interfaces.
- `agent_host_port`: unpublished.
- `home_volume`: dedicated persistent `jenkins-home` named volume.
- `docker_socket`: present by explicit approval.
- `allowed_scope`: repository validation.

**Invariants**
- Jenkins does not deploy Compose, publish Bundles, mutate Bundle references, or enable UAT/production deployment.
- Docker socket exposure remains a broad host-control boundary.

## Persistent Volume Ownership

Maps persistent data to a single owning service boundary.

| Volume | Owner | May initialize/reset lakehouse data? |
|---|---|---|
| `airflow-postgres-data` | Airflow PostgreSQL | No |
| `jenkins-home` | Jenkins | No |
| Airflow logs volume, if required | Airflow logging topology | No |
| Existing Hive, metastore, KDC, RustFS, JupyterHub, Spark, StarRocks volumes | Existing lakehouse services | Preserve current ownership and contents |

Normal service lifecycle does not delete named volumes. Bundle checkout is recreatable ignored runtime state, not a persistent lakehouse data volume.

## Published Endpoint

Represents the host-visible web interfaces added by this integration.

| Service | Host binding | Container port | Host interface | TLS in this design |
|---|---:|---:|---|---|
| Airflow API/UI | 8085 | 8080 | All | No |
| Jenkins UI | 8098 | 8080 | All | No |
| Jenkins inbound agent | None | 50000 | Not published | N/A |

No new host publication is defined for Airflow PostgreSQL, Hive Metastore, Spark worker ports, Kerberos, or RustFS.
