# Application Design — Airflow, Jenkins, and Spark Integration

## Overview

The target remains a Compose lakehouse using Hive Metastore for Iceberg metadata, RustFS for data objects, and Spark for ETL. Airflow 3 and Jenkins are integrated into the target Compose project. Airflow consumes version-pinned Git Bundles and creates one temporary Spark client/driver per DAG run. The driver submits to the existing Spark master and worker. The driver and worker use the existing Kerberos and RustFS writer identity. Jenkins remains validation-only.

## Approved Design Decisions

- Keep Airflow's dedicated PostgreSQL service and named volume, separate from Hive metastore PostgreSQL.
- Keep writer TGT acquisition and renewal inside the existing Spark service boundary; use a private runtime ticket cache.
- Preserve Jenkins's Docker socket mount, matching the approved NFR and sibling Compose setup. The current Jenkins pipeline does not invoke Docker; this grants the service broad Docker daemon control beyond its current CI commands.
- Preserve the existing `iceberg-poc-net`, lakehouse services, identities, configurations, and persistent data.
- Keep `dev` pointed at the local lakehouse and UAT/production as unconfigured placeholders.
- Treat the project Git remote as deployment configuration.

## Component Boundaries

- **Airflow control plane**: API server, LocalExecutor scheduler, DAG processor, triggerer, initializer, and dedicated metadata PostgreSQL. Only the scheduler needs the Docker socket for run-container lifecycle.
- **Git Bundles and DAG factory**: Fetch and resolve a run-pinned project revision, create and monitor the temporary driver, and remove it after success or failure.
- **Per-run Spark driver**: Runs from the target-compatible Spark/Iceberg image, mounts bundle/config/keytab/secret files read-only, uses a private cache, and submits in client mode to the target master.
- **Existing Spark service**: Continues hosting master, worker, and history server; initializes and renews the writer TGT inside the service and exposes the existing remote execution endpoint.
- **Jenkins CI**: Validates project source and tests. It does not publish artifacts, deploy services, or update bundle refs.
- **Existing lakehouse services**: KDC, Hive Metastore, metastore PostgreSQL, RustFS, JupyterHub, and StarRocks retain current responsibilities and data.

## Service Contract Summary

- Airflow Git Connection: fetches the configured project repository; credentials remain in Airflow's connection/secret mechanism.
- Bundle contract: the resolved revision is mounted read-only for the run from a host-visible bundle checkout path.
- Spark contract: per-run client driver submits to the existing Spark master, with Hive catalog config and writer runtime files; executors access Hive and RustFS with the worker-side writer identity. Infrastructure Design must verify the master-advertised endpoint against the current worker startup URL (`spark://spark-iceberg:7077`) and target Compose DNS.
- Credential contract: read-only keytab and RustFS secret files; private runtime TGT caches; no secret values in source, bundle, or logs.
- Network contract: services and run containers join `iceberg-poc-net`; Docker bind sources use host-visible absolute paths.
- Jenkins contract: CI validation only, with the selected Docker socket mount retained and documented as a risk.

## Deferred Detail

Functional Design will define task behavior, precise cleanup semantics, ticket renewal edge cases, config validation, and failure state transitions. NFR Design will define cache permissions, renewal timing/expiry handling, secret mount modes, and Docker socket boundaries. Infrastructure Design will verify Compose service dependencies, host paths, Spark master advertisement, and networking. No implementation files are changed in this stage.

## Design Artifacts

- [Components](components.md)
- [Component method contracts](component-methods.md)
- [Services](services.md)
- [Component dependencies and data flow](component-dependency.md)
