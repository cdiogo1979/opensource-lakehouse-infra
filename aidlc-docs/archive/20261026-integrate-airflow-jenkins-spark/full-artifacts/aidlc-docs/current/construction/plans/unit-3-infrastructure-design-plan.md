# Unit 3 Infrastructure Design Plan — Platform Compose Integration

## Approved Baseline

Unit 3 Functional Design, NFR Requirements, and NFR Design are approved. This unit integrates Airflow 3.3.2, a dedicated Airflow PostgreSQL service, Git Bundle storage, and validation-only Jenkins into the target local Compose lakehouse while preserving existing services and data volumes.

Approved infrastructure constraints include Airflow UI `8085:8080` and Jenkins UI `8098:8080` on all host interfaces; no Jenkins agent port `50000`; existing `iceberg_net` key and `iceberg-poc-net` Docker name; Docker socket on the Airflow scheduler and separately approved Jenkins among the new services, while retaining the existing JupyterHub socket mount; writer credentials excluded from Airflow services and Jenkins; and the maintained `lakehouse-main`/`lakehouse-uat` Git Bundle list. These bundles create production and UAT DAGs; their workload configurations remain disabled until endpoints and credentials are approved. No TLS termination, volume reset, HA, backup/restore, CPU/memory limits, or capacity guarantee is in scope.

Unit 2 owns the run driver/worker lifecycle and its five-minute readiness/60-second cleanup limits. Unit 3 must wire services, networks, paths, health dependencies, and volumes to that contract.

## Infrastructure Design Checklist

- [x] Read approved Unit 3 Functional Design, NFR Requirements, NFR Design, target Compose topology, and the maintained sibling Airflow/Jenkins configuration.
- [x] Confirm this stage is design-only; no Compose mutation, build, service startup, volume operation, or tests are authorized here.
- [x] Map Airflow API, scheduler, DAG processor, triggerer, initializer, dedicated PostgreSQL, and Jenkins to services, image/config ownership, networks, and dependencies.
- [x] Define images and provider/version constraints using the maintained Airflow 3.3.2 configuration; identify any required implementation delta for explicit review.
- [x] Specify concrete PostgreSQL/API/Jenkins health checks, initializer gating, and the five-minute API health deadline without making health imply workload readiness.
- [x] Define Airflow/Jenkins named volumes, runtime Bundle checkout path, project-root mapping, and preservation of all existing lakehouse volumes.
- [x] Define deployment secret source locations, host mode/ownership, container UID/GID access, read-only mounts, and missing-secret handling.
- [x] Define a race-safe Bundle revision reference/cleanup mechanism; if the Airflow Bundle/runtime interfaces cannot support safe pruning, specify fail-safe disabled pruning rather than guessing.
- [x] Verify container host-path visibility from both Compose services and the Docker daemon for scheduler-created run containers.
- [x] Confirm the network key/name, existing service DNS endpoints, host port bindings, no-agent-port rule, and exact Docker socket mounts.
- [x] Assess compute, storage, network, monitoring, and persistence impact; record non-applicable categories without inventing requirements.
- [x] Generate `aidlc-docs/current/construction/unit-3/infrastructure-design/infrastructure-design.md` and `deployment-architecture.md`.
- [x] Validate against Functional Design rules, U3-NFR-01 through U3-NFR-08, Unit 2 run contracts, and existing Compose preservation requirements.
- [x] Present Infrastructure Design for explicit approval before Unit 3 Code Generation.

## Design Boundaries

- Inspect the existing target Compose file before specifying service merges. Preserve current network identity, ports, volume names, credential sources, and service configuration.
- Keep Airflow metadata PostgreSQL independent from Hive Metastore PostgreSQL.
- Use the configured target Git remote as a deployment input; do not invent a remote URL or commit Git credentials.
- Use identical Bundle mount paths in the DAG processor and scheduler, plus a daemon-visible host source for the Docker-created driver. Fail closed on mapping mismatch.
- Preserve required host secret mode `0600` and read-only container mounts. Align runtime UID/GID explicitly; do not loosen permissions to fix access failures.
- Automatic Bundle pruning is permitted only if active-run references and an atomic coordination mechanism can be proven across fetch, run pinning, and deletion. Otherwise configure no pruning and document the gap for approval/Build and Test.
- Preserve all approved socket and host exposure decisions, including the documented broad host-control risk of Docker socket access.
- Do not add an agent port, TLS proxy, backup system, external secrets service, queue, new runtime package, capacity target, or unapproved restart behavior.
- Do not edit `docker-compose.yml`, Dockerfiles, scripts, or runtime configuration during this planning stage.

## Approval Gate

Review and approve this plan before generating Unit 3 Infrastructure Design artifacts.

**Status**: Approved by the user on 2026-10-26. Proceeding to Unit 3 Code Generation planning.

## Approved Bundle Revision — 2026-10-26

The user directed that the Bundle configuration list remain the same as `airflow-spark-jenkins` and that verification assert UAT and production DAG creation. The approved list therefore has exactly `lakehouse-main` tracking `main` and `lakehouse-uat` tracking `uat`, both using the existing Git URL, `lakehouse_git`, 300-second refresh, and sparse directories `dags`, `configs`, and `notebooks`. The main bundle maps to production DAG IDs with the `main-` prefix; the UAT bundle maps to `uat-` IDs. UAT/prod execution stays disabled and fails closed. The implementation must include a DAG-registration verification check.
