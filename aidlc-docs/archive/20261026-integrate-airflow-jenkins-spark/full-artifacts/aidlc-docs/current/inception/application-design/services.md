# Service Design

## Compose Service Groups

### Airflow Services

- **`airflow-postgres`**: Dedicated metadata database and named volume, separate from Hive metastore PostgreSQL.
- **`airflow-init`**: Runs Airflow database migration and administrative bootstrap, then exits successfully.
- **`airflow-api-server`**: Serves the Airflow UI/API; no Docker socket mount.
- **`airflow-scheduler`**: Uses LocalExecutor to execute DAG tasks and is the only Airflow service with Docker socket access for creating/removing run drivers.
- **`airflow-dag-processor`**: Fetches/parses configured Git Bundles and writes its checkout to the host-visible bundle storage path.
- **`airflow-triggerer`**: Retains the sibling Airflow 3 service topology for deferrable tasks.

### Spark Services

- **`spark`**: Existing master, worker, and history server in one Compose service. The entrypoint initializes the writer TGT and starts a renewal helper in the same service, then starts Spark processes. The TGT cache resides in private temporary storage.
- **`spark-run`**: Not a long-lived Compose service. For each DAG run, Airflow creates one ephemeral driver and one worker-only Spark container through Docker. The driver receives the pinned bundle read-only; both containers receive read-only writer credential files and private ticket-cache storage. The worker registers with the shared Spark master and is removed with the driver after the run. Spark Standalone may schedule the application's executors on any registered worker, so this is a lifecycle boundary rather than an exclusive placement guarantee.

### Jenkins Service

- **`jenkins`**: Runs CI checks and persists its home directory. Preserve the selected Docker socket mount, although the inspected pipeline does not currently call Docker. The socket gives Jenkins broad Docker daemon control and should be treated as a documented risk.

### Retained Lakehouse Services

The current KDC, Hive Metastore, metastore PostgreSQL, RustFS, JupyterHub, and StarRocks services retain their existing ownership, ports, credentials, and named data volumes. Airflow gets a separate PostgreSQL service and volume.

## Service Interactions

1. The operator triggers a DAG through the Airflow API/UI.
2. The DAG processor has resolved the selected Git Bundle revision; the scheduler's DAG task receives the pinned checkout path and environment.
3. The scheduler calls the Docker daemon to create one per-run driver and one worker-only container on `iceberg-poc-net`; it mounts the pinned bundle read-only into the driver and credential/config source files read-only into both containers.
4. Driver and worker independently obtain writer TGTs in private caches. The worker starts in worker-only mode and registers with the Spark master-advertised endpoint. Infrastructure Design must verify this endpoint against the current worker startup URL (`spark://spark-iceberg:7077`) and target Compose DNS.
5. The driver `spark-submit`s in client deploy mode. Spark Standalone may schedule executors on any registered worker, including the long-lived worker and workers created for other runs. Workers use the writer identity contract to access Hive at `thrift://hive-metastore:9083` and RustFS at `http://object-store:9000`.
6. Airflow captures task outcome and removes both per-run containers. Jenkins independently validates repository code and does not publish or move bundle refs.

## Mount and Secret Ownership

- Bundle checkout storage is under ignored runtime state and is bind-mounted at an identical absolute path into the Airflow bundle processing/scheduler boundary and Docker-created drivers. This lets the Docker daemon resolve host bind sources.
- The Airflow scheduler receives the Docker socket and bundle host path; it does not receive writer secret values.
- Driver keytab and RustFS secret files are mounted read-only from host runtime credential paths; the driver cache is private and ephemeral.
- The existing Spark service mounts the writer keytab and RustFS writer secrets read-only and uses private temporary cache storage.
- Jenkins retains the Docker socket by explicit selection. Its current source validation does not require Docker API calls.
- The target Compose network name remains `iceberg-poc-net`; Spark, Hive, KDC, and RustFS are addressed through Compose network service names.

## Failure and Ownership Boundaries

- Bundle fetch/resolve errors fail before driver creation.
- Spark submit or workload errors fail the Airflow task; cleanup removes only the temporary driver, not lakehouse data volumes.
- A Spark service ticket bootstrap/renewal failure is reported through service logs and health status; exact retry and restart behavior is deferred to Functional/NFR Design.
- Jenkins validation failures affect CI results only; they do not change bundle refs or running services.
