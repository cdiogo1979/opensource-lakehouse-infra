# User Stories — Airflow, Jenkins, and Spark Integration

Stories are grouped by feature, as selected in the approved story plan. Each story has concise, independently checkable acceptance criteria and links to the approved requirements.

## Feature: Git Bundle Management

### US-01 — Run the intended bundle revision

**As an ETL workload author,** I want Airflow to use the configured project repository and pin each DAG run to its resolved bundle revision, **so that** the code executed by a run is reproducible and cannot be changed by the running container.

**Acceptance criteria**

- Airflow fetches the configured project Git repository using the configured bundle identities.
- A run mounts its resolved bundle revision read-only in the per-run Spark container.
- The `dev` bundle targets the local lakehouse.
- UAT and production remain explicit unconfigured placeholders and do not silently target the local lakehouse.
- The bundle Git remote is provided through deployment configuration, not embedded as an assumed repository URL.

**Persona**: ETL Workload Author; Platform Operator  
**Requirements**: FR-2, FR-7, NFR-2

### US-06 — Keep non-local environments unavailable until configured

**As a platform operator,** I want unconfigured UAT and production bundle targets to fail clearly or remain unavailable, **so that** a run cannot accidentally use the local development lakehouse as another environment.

**Acceptance criteria**

- A UAT or production selection without a configured endpoint cannot submit a job to the local lakehouse.
- The unavailable or invalid target is reported clearly to the operator.
- Configuring an endpoint does not happen implicitly as part of selecting the bundle identity.

**Persona**: Platform Operator  
**Requirements**: FR-7, Operational Scenario 5

## Feature: Spark Execution and Writer Credentials

### US-02 — Submit a pinned workload to the target Spark cluster

**As a platform operator,** I want Airflow to create a temporary Spark driver for each DAG run and submit it to the existing Spark master, **so that** workloads use the lakehouse Spark cluster and do not share a persistent Airflow job container.

**Acceptance criteria**

- Airflow and Jenkins are available from the target Compose project and connect to `iceberg-poc-net`.
- The integration retains the existing lakehouse services and named data volumes.
- Each DAG run creates its own Spark driver container and mounts the run-pinned bundle read-only.
- The driver submits the workload to the existing target Spark master and worker service.
- The per-run driver is removed after the run completes.
- The integration does not replace remote Spark submission with local-only `local[*]` execution.

**Persona**: Platform Operator  
**Requirements**: FR-3, NFR-2

### US-03 — Write lakehouse data as the configured writer

**As an ETL workload author,** I want the driver and Spark workers to use the existing Kerberos and RustFS writer identity, **so that** a workload can create and write Hive/Iceberg data without embedding credentials in its code or bundle.

**Acceptance criteria**

- The driver and existing worker service use `write-service-account@LAKEHOUSE.LOCAL` for Kerberos access and the matching RustFS writer credentials for S3 access.
- The keytab is mounted read-only, and each runtime uses a private Kerberos ticket cache.
- RustFS credentials are provided through file-backed secrets.
- A sample Spark workload can create and write a Hive/Iceberg table and its data files to RustFS using this runtime.
- Keytab or RustFS secret values do not appear in bundle content, source files, or ordinary task logs.
- The shared worker identity's scope is documented; users do not mistake it for per-author storage authorization.

**Persona**: ETL Workload Author  
**Requirements**: FR-4, FR-5, NFR-1, NFR-3

### US-04 — Understand and clean up a failed run

**As a platform operator,** I want a failed Spark submission or workload to be reported and its temporary driver removed, **so that** I can diagnose the run without leaving orphaned containers or modifying persistent lakehouse data during cleanup.

**Acceptance criteria**

- Airflow marks the run failed and exposes the failure through its run status and logs.
- The per-run Spark driver is removed after a failed submission or task.
- Cleanup does not remove or recreate the existing lakehouse named volumes.
- The bundle revision used for the failed run remains unchanged.

**Persona**: Platform Operator  
**Requirements**: FR-3, Operational Scenario 3, NFR-2

## Feature: Jenkins Validation

### US-05 — Validate workflow changes without publishing them

**As a workflow maintainer,** I want Jenkins to validate repository changes without publishing artifacts or changing Airflow bundle references, **so that** code validation remains separate from workflow deployment.

**Acceptance criteria**

- Jenkins runs the configured CI validation for repository changes.
- Jenkins does not publish workload artifacts or deploy lakehouse services.
- Jenkins does not update or move an Airflow Git Bundle reference.

**Persona**: ETL Workload Author  
**Requirements**: FR-6

## Story-to-Requirement Coverage

| Requirement | Covered by |
|---|---|
| FR-1 Compose integration | US-02, US-05 |
| FR-2 Workflow source and Git Bundles | US-01 |
| FR-3 Per-run driver and remote Spark execution | US-02, US-04 |
| FR-4 Writer identity on driver | US-03 |
| FR-5 Writer identity on workers | US-03 |
| FR-6 Jenkins scope | US-05 |
| FR-7 Bundle environments | US-01, US-06 |
| FR-8 Preserve existing platform and data | US-04 |
| NFR-1 Credential handling | US-03 |
| NFR-2 Bundle immutability and run isolation | US-01, US-02, US-04 |
| NFR-3 Local environment scope | US-03 |
| NFR-5 Docker control boundary | To be detailed in infrastructure design and verified against Compose mounts |

## INVEST Review

- Stories are divided by the selected feature groups and do not prescribe implementation tasks.
- Each story has an identified persona, a user-valued outcome, and checkable acceptance statements.
- US-03 and US-04 are linked to distinct requirements and outcomes; their acceptance criteria can be verified independently.
- NFR-4 is a testing constraint rather than a user outcome and will be captured in workflow planning and test design.
