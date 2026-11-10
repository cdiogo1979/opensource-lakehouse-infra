# Requirements — Airflow, Jenkins, and Spark Integration

## Intent Analysis

- **User request**: Integrate the Jenkins, Airflow, and Spark workflow into the lakehouse project. Preserve Airflow Git DAG Bundles and the per-run Spark container model, and run Airflow workloads as the existing lakehouse writer service account.
- **Request type**: Integration and enhancement of an existing brownfield system.
- **Scope estimate**: Cross-system, spanning Docker Compose, Airflow, Jenkins, Git DAG Bundles, Spark, Kerberos, Hive Metastore, and RustFS.
- **Complexity estimate**: Complex. The integration crosses service ownership, remote Spark execution, and credentials used by both the per-run driver and the existing Spark worker service.
- **Requirements depth**: Comprehensive.

## Goals

Integrate the existing orchestration workflow with the target lakehouse Compose environment so a version-pinned Airflow bundle can launch an ephemeral Spark driver, submit to the target Spark cluster, and read or write Hive/Iceberg and RustFS data using the existing writer identity. Jenkins remains a code validation service.

## Functional Requirements

### FR-1 — Compose integration

Add or adapt Airflow and Jenkins services, images, configuration, and required mounts in the target Compose project. Connect them to the existing `iceberg-poc-net` network while preserving the lakehouse services and their named data volumes.

### FR-2 — Workflow source and Git Bundles

Maintain the required DAG factory, DAGs, environment configuration, and workload code in this project. Configure Airflow Git DAG Bundles to fetch this project's Git repository. Each DAG run must use its resolved, pinned bundle version mounted read-only in its Spark run container. The Git remote URL is a deployment input because the target folder does not currently provide a Git remote value.

### FR-3 — Per-run driver and remote Spark execution

Airflow must continue to create an ephemeral Spark container per DAG run, mount the selected bundle read-only, submit the workload to the existing target Spark master and worker service, and clean up the per-run container on success or failure. Do not replace this model with a shared Airflow Spark container or local-only `local[*]` execution.

### FR-4 — Writer identity on the per-run driver

The per-run driver must authenticate to Hive Metastore and RustFS using the existing Kerberos principal `write-service-account@LAKEHOUSE.LOCAL` and its matching RustFS writer credentials. Mount the keytab read-only, create and use a private ticket cache, acquire and verify a TGT before submission, and expose RustFS credentials through file-backed secrets. Do not put credential values in DAG bundles, source code, or ordinary environment variables.

### FR-5 — Writer identity on target Spark workers

The existing Spark worker service must also be configured with the writer identity so remote executors can access Hive Metastore and RustFS. Mount the writer keytab read-only, use a private renewable Kerberos ticket cache, and provide the matching RustFS credentials as file-backed secrets. The worker-side identity is shared by workloads on this local Spark service; authorization remains bounded by the writer identity's grants.

### FR-6 — Jenkins scope

Include Jenkins as a CI validation service. Jenkins validates repository changes only; it does not publish artifacts, deploy services, or change Airflow bundle references.

### FR-7 — Bundle environments

Keep `dev`, `uat`, and `prod` bundle identities/configurations. Point only `dev` to this local lakehouse. Leave UAT and production endpoints as explicit unconfigured placeholders until those environments are supplied; do not direct them at the local lakehouse.

### FR-8 — Preserve the existing platform

Retain the Hive Metastore, PostgreSQL metadata store, Kerberos KDC, RustFS, Spark, JupyterHub, TPCH tooling, and StarRocks services, configurations, and persistent data. Do not rotate existing credentials as part of this integration unless a later approved requirement explicitly calls for it.

## Non-Functional Requirements and Constraints

### NFR-1 — Credential handling

Protect the writer keytab and RustFS secrets with read-only mounts and restrictive file permissions. Keep ticket caches private and runtime-scoped. Do not commit secrets, print secret values in logs, or store credentials in Git bundle content. The Security Baseline extension is disabled by the user's selection; these explicit credential requirements remain in scope.

### NFR-2 — Bundle immutability and run isolation

Mount the exact bundle revision resolved for the DAG run read-only. The ephemeral Spark driver must be cleaned up after the run. Credentials and ticket caches must not be written into the bundle checkout or persist in the driver's container after cleanup.

### NFR-3 — Scope and environment

This is a local Docker Compose integration. No production availability, throughput, or resource-sizing target was specified. Continue using existing Spark master/worker resources unless later design work identifies a required change. UAT and production remain placeholders.

### NFR-4 — Property-based testing

Apply the selected partial Property-Based Testing extension only to applicable pure functions and serialization round-trips. The Resiliency Baseline extension is disabled.

### NFR-5 — Docker control boundary

Airflow and Jenkins require the Docker control access used by the current orchestration workflow. Document and constrain the required socket mounts and host paths during design; do not grant broader host access than the workflow needs.

## Operational Scenarios

1. An operator triggers a DAG from an allowed bundle environment. Airflow resolves the run's pinned bundle revision, creates the per-run Spark driver with a read-only bundle mount and writer credentials, submits to the target Spark master, and removes the driver when the run ends.
2. A remote Spark executor accesses Hive Metastore or RustFS as the writer identity using the existing worker service's private Kerberos ticket cache and file-backed RustFS credentials.
3. A task fails during submission or execution. Airflow reports the failure, removes the per-run container, and does not alter the pinned bundle or persistent lakehouse data as part of cleanup.
4. Jenkins validates a repository change without publishing it or moving an Airflow bundle reference.
5. A UAT or production bundle is selected before its endpoint is configured. The configuration must fail clearly or remain unavailable; it must not silently target local development.

## Acceptance Criteria

- Airflow and Jenkins start from the target Compose project and join `iceberg-poc-net`.
- Airflow fetches the configured project repository as Git DAG Bundles, and a run uses the bundle revision resolved for that run through a read-only mount.
- A DAG run creates an ephemeral driver and submits successfully to the existing target Spark master/worker service.
- The driver and worker can obtain/use the `write-service-account@LAKEHOUSE.LOCAL` Kerberos identity and the RustFS writer identity without storing credentials in bundle content, source, or logs.
- A Spark workload can create and write a sample Hive/Iceberg table and its data files in RustFS under the writer identity.
- Airflow removes the per-run driver after both successful and failed runs.
- Jenkins validation does not publish artifacts or change a bundle reference.
- `dev` targets the local lakehouse; UAT and production remain explicit placeholders.
- Existing lakehouse named volumes and data are retained.

## Decisions and Open Inputs

- The user selected remote Spark execution through the existing target Spark master and workers.
- The user selected configuring the existing worker service with a read-only writer keytab, private renewable ticket cache, and RustFS writer credentials, in addition to credentials in the per-run driver.
- The Git remote URL for the target repository must be provided through deployment configuration when available.
- UAT and production lakehouse endpoints are intentionally unspecified.
- Spark Kerberos ticket renewal and credential propagation behavior between driver and executors must be verified in design and build/test. The worker-side writer principal is the explicitly selected access path for executors.
- Airflow's Git provider credentials and other service secrets must use the existing secret/connection mechanism, not repository files; exact configuration will be decided during design.

## Extension Configuration

| Extension | Selection | Requirements effect |
|---|---|---|
| Security Baseline | Disabled | Its extension rules are not blocking; FR-4, FR-5, and NFR-1 still require the credential protections stated above. |
| Property-Based Testing | Partial | Apply only to applicable pure functions and serialization round-trips. |
| Resiliency Baseline | Disabled | No resiliency-baseline requirements are imposed. |

## Key Requirements Summary

Integrate Airflow and Jenkins into the lakehouse Compose network, keep versioned read-only Git Bundles and ephemeral per-run Spark drivers, and submit those drivers to the existing remote Spark cluster. Both drivers and workers use the existing Kerberos and RustFS writer identity through protected runtime credentials. Jenkins remains CI-only, and only the dev bundle points to this local environment.
