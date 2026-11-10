# Component Methods and Interface Contracts

These are logical high-level interfaces for the design. They do not prescribe programming language or detailed business rules; those belong in Functional Design.

## Git Bundle Store

### `resolve_bundle_revision(bundle_id, run_id) -> PinnedBundle`

- **Purpose**: Resolve the immutable checkout and environment settings associated with an Airflow run.
- **Inputs**: Bundle identity and Airflow run identity.
- **Output**: Pinned revision identifier, host-visible checkout path, and environment configuration.
- **Failure**: Unknown bundle, absent revision, invalid environment, or missing repository credentials is reported as a failed Airflow task.

## DAG Factory and Run Orchestrator

### `build_dag(declaration, bundle_context) -> AirflowDAG`

- **Purpose**: Convert a bundle workload declaration and environment into Airflow tasks.
- **Inputs**: Bundle declaration and resolved bundle context.
- **Output**: DAG with run creation, workload submission, outcome reporting, and cleanup tasks.

### `create_run_driver(run_context, spark_image, mount_contract) -> ContainerReference`

- **Purpose**: Create the isolated Spark client/driver for a specific run.
- **Inputs**: Run ID, pinned bundle path, environment, Spark image, network, config paths, and read-only credential host paths.
- **Output**: Docker container reference.
- **Failure**: Docker create/start errors fail the task and are surfaced to the operator.

### `submit_workload(container_reference, workload, spark_master, run_config) -> RunResult`

- **Purpose**: Submit workload code to the existing Spark master and return its completion status.
- **Inputs**: Driver reference, workload path within the pinned bundle, Spark master endpoint, and run configuration.
- **Output**: Exit status and redacted task result.

### `remove_run_driver(container_reference) -> CleanupResult`

- **Purpose**: Remove the temporary driver after success or failure.
- **Inputs**: Container reference.
- **Output**: Cleanup status; repeated cleanup of an already-removed container is treated as complete.

## Spark Writer Credential Lifecycle

### `initialize_writer_ticket(keytab_path, principal, cache_path) -> TicketStatus`

- **Purpose**: Obtain and verify a writer TGT in the private cache before Spark processes need catalog access.
- **Inputs**: Read-only keytab path, existing principal, and private cache path.
- **Output**: Verified principal and ticket expiry/renewal metadata without secret values.

### `renew_writer_ticket(cache_path, keytab_path, principal) -> TicketStatus`

- **Purpose**: Maintain a usable writer TGT for the long-running Spark service.
- **Inputs**: Existing private cache and keytab/principal fallback.
- **Output**: Updated ticket status or an actionable service failure.

## Jenkins Validation

### `validate_repository(revision) -> ValidationResult`

- **Purpose**: Run source compilation and automated tests for a repository revision.
- **Inputs**: Repository checkout/revision.
- **Output**: Pass/fail result and redacted test logs; no bundle ref or deployment side effects.

## Existing Service Interfaces

- **Spark to Hive Metastore**: Hive Thrift endpoint with SASL/Kerberos.
- **Spark and Hive to RustFS**: S3-compatible endpoint and file-backed credentials for the respective identity.
- **Airflow to PostgreSQL**: Dedicated Airflow metadata database service and credentials.
- **Airflow to Git**: Configured Git connection; repository URL is deployment configuration.
