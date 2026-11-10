# Application Components

## Airflow Platform

### Airflow Control Plane

- **Purpose**: Expose Airflow operations and schedule/execute DAG tasks.
- **Responsibilities**: Run the API server, scheduler, DAG processor, triggerer, and initialization/migration service using the sibling stack's Airflow 3.3.2 and LocalExecutor topology.
- **Interfaces**: Airflow UI/API; DAG processor reads Git Bundle configuration; scheduler calls the Docker Engine API for each run's driver and worker.
- **Boundary**: Airflow metadata is stored in a dedicated Airflow PostgreSQL service and named volume, separate from Hive metastore PostgreSQL.

### Git Bundle Store and Environment Configuration

- **Purpose**: Provide immutable DAG, configuration, helper, and workload code for each run.
- **Responsibilities**: Fetch configured project Git refs through an Airflow Git connection, resolve versioned bundle checkouts, and represent `dev`, `uat`, and `prod` identities.
- **Interfaces**: Git remote URL and Airflow connection; a host-visible bundle storage directory mounted at the same absolute path into the Airflow components and Docker-created driver container.
- **Boundary**: The repository URL is a deployment input. `dev` targets the local lakehouse; UAT and production remain explicit unconfigured placeholders.

### DAG Factory and Run Orchestrator

- **Purpose**: Turn bundle declarations into Airflow DAGs and coordinate a Spark run.
- **Responsibilities**: Resolve the run-pinned bundle path and environment, create one driver and one worker-only container per run with minimum required mounts, await TGT/readiness/worker registration, submit workloads to the Spark master, report status, and clean up both containers.
- **Interfaces**: Airflow DAG/task interface; Docker Engine API; Spark submit and worker-registration contracts; bundle directory; runtime config and credential host paths.
- **Boundary**: Bundle content is mounted read-only. The scheduler passes host file paths to the Docker daemon; it does not need to load the writer keytab or secret contents into its own environment.

## Spark Workload Runtime

### Per-Run Spark Driver

- **Purpose**: Keep the Spark driver process and run-scoped state isolated for one DAG run.
- **Responsibilities**: Read the pinned bundle, acquire a writer TGT in a private cache, load the Hive-backed Iceberg Spark configuration, and submit in client deploy mode to the target Spark master.
- **Interfaces**: Spark standalone master endpoint to be verified from the target master advertisement during Infrastructure Design (the current worker startup uses `spark://spark-iceberg:7077`); Hive Metastore `thrift://hive-metastore:9083`; RustFS `http://object-store:9000`; KDC; read-only bundle, keytab, Spark configuration, and file-backed RustFS credentials.
- **Boundary**: The per-run container is removed on completion or failure. No credentials are stored in the bundle or driver image.

### Per-Run Spark Worker

- **Purpose**: Add one temporary Spark worker container to the shared Spark Standalone cluster for each DAG run.
- **Responsibilities**: Start in worker-only mode using the writer credential lifecycle; register with the shared master; expose readiness; terminate when Airflow cleans up the run.
- **Interfaces**: Spark master endpoint; KDC; Hive Metastore; RustFS; read-only writer keytab and file-backed RustFS credentials.
- **Boundary**: Worker container lifecycle is dedicated per run, but Spark may schedule executors for any application on any registered worker. It does not guarantee driver-to-worker placement or isolation.

### Existing Spark Service and Worker Credential Lifecycle

- **Purpose**: Provide the existing Spark master, worker, and history server and remote executor runtime.
- **Responsibilities**: Run Spark processes using the Hive/Iceberg catalog config; acquire and renew the writer TGT within this service boundary; provide executors access to RustFS with the existing writer credentials.
- **Interfaces**: Existing Spark standalone master/worker endpoint, to be verified from the target master advertisement during Infrastructure Design; KDC; Hive Metastore; RustFS; read-only writer keytab and file-backed RustFS credentials.
- **Boundary**: A private runtime cache is held in service-local temporary storage. The writer identity is shared by all jobs on these workers and does not represent per-author access control.

## Jenkins CI

### Jenkins Validation Service

- **Purpose**: Validate code and configuration changes in the integrated repository.
- **Responsibilities**: Run the existing Python compilation and test validation. Do not deploy services, publish workload artifacts, or move Airflow bundle refs.
- **Interfaces**: Repository checkout and CI pipeline configuration; persistent Jenkins home volume.
- **Boundary**: Preserve the selected sibling setup's Docker socket mount to satisfy the approved NFR. The current pipeline does not invoke Docker, so the socket currently provides more privilege than its CI commands need; this is a documented host-control risk.

## Existing Lakehouse Services (Retained)

- **Kerberos KDC**: Issues service and writer tickets; existing principal and keytab remain unchanged.
- **Hive Metastore and metadata PostgreSQL**: Continue serving the Hive-backed Iceberg catalog.
- **RustFS**: Continues storing Iceberg objects in the existing bucket and data volumes.
- **StarRocks and JupyterHub**: Continue using their existing identities and configurations; no behavior changes are introduced by this design.
