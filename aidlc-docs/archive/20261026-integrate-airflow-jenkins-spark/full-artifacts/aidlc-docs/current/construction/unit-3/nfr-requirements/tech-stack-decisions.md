# Technology Stack Decisions — Unit 3 NFR Requirements

## Decision Summary

| Area | Decision | Rationale / constraint |
|---|---|---|
| Airflow | Retain the approved Airflow 3.3.2 service topology and LocalExecutor | Matches the inspected and approved Unit 3 Functional Design; no engine change is needed for NFR targets. |
| Airflow metadata | Dedicated PostgreSQL service and named volume | Isolates Airflow metadata from Hive Metastore PostgreSQL and preserves state across ordinary container lifecycle. |
| Health | Compose service health checks with 10-second interval, 5-second timeout, and three-failure threshold | Provides a bounded local health signal while keeping workload readiness checks separate. |
| Git DAG Bundles | Existing Airflow Git Bundle support and host-visible checkout directory | Preserves pinned revisions and Docker daemon host-path requirements; inactive local revisions older than 30 days are eligible for cleanup. |
| Runtime secrets | Deployment-supplied file references, host mode `0600`, read-only container mounts | Keeps secret values outside source control and Airflow/Jenkins ordinary environment configuration. |
| Jenkins | Existing validation-only Jenkins service and persistent home volume | No publishing, deployment, or Bundle reference mutation is introduced. |
| Docker control | Docker socket remains limited to Airflow scheduler and approved Jenkins service | Preserves approved design; socket access remains broad host control and is not claimed to be least privilege. |
| Resource policy | Preserve host sizing; no fixed per-service CPU/memory limits or capacity claim | Matches local PoC scope and avoids inventing a target absent user requirements. |
| Test scope | Compose/runtime integration verification in the later Build and Test stage | NFR requirements define observable conditions; they do not claim implementation or runtime evidence. |

## Dependency and Change Policy

- Keep the Airflow 3.3.2 and provider constraints from the approved functional baseline; do not add a database, broker, secret manager, proxy, or observability service for these NFRs.
- Keep the approved existing Docker network and service endpoints.
- Do not add a Bundle cleanup tool or change Airflow internals until Infrastructure Design and Code Generation establish the concrete mechanism for preserving active revisions.
- Keep health checks local and credential-safe. Exact probe commands belong to Infrastructure Design and Code Generation.
- Keep UI publication on the approved ports and all-interface binding. TLS termination is outside the accepted local scope.
- No tests or builds are run during this requirements stage.
