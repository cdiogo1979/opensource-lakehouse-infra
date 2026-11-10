# Unit 2 Infrastructure Design Plan — Airflow Bundle Runner

## Approved Baseline

Unit 2 Functional Design and NFR Design are approved. Airflow and Jenkins join the existing Compose project and `iceberg-poc-net`, while the existing KDC, Hive Metastore, PostgreSQL, RustFS, Spark, JupyterHub, TPCH tooling, and StarRocks services and named data volumes remain intact. Airflow retains its dedicated PostgreSQL metadata service/volume. The Airflow scheduler owns the existing Docker Engine boundary for run containers; Jenkins keeps its approved socket mount, with the unused-by-current-pipeline host-control risk documented.

Each admitted DAG run creates one Spark driver and one worker-only container from the approved local derived Spark image, with separate private credential caches and read-only writer credential mounts. Both use the shared `spark` master endpoint on `iceberg-poc-net`; the worker is not guaranteed exclusive executor placement. Airflow admits at most two active runs. The driver is shut down while the worker is decommissioned and drained within the same 60-second cleanup budget; if foreign executors remain at the deadline, the worker is stopped/removed and a sanitized drain-timeout event warns of possible impact to another run. Multi-catalog compatibility remains a later integrated Build and Test gate.

## Infrastructure Design Checklist

- [x] Read the approved Unit 2 Functional Design, NFR Requirements, NFR Design, Unit 1 Infrastructure Design, and application Compose/service contracts.
- [x] Confirm the deployment target is the local Docker Compose lakehouse; preserve existing service and data ownership.
- [x] Map Airflow API, scheduler, DAG processor, triggerer, initializer, dedicated PostgreSQL, and Jenkins to Compose service boundaries.
- [x] Map the driver's and worker-only container modes to the pinned local Spark image, shared network, master endpoint, read-only credentials, private tmpfs caches, health/readiness, and cleanup lifecycle.
- [x] Define service dependencies, host path visibility for Docker-created bind mounts, persistent Airflow/Jenkins volumes, and existing named-volume protections.
- [x] Resolve host port exposure preference: user selected all-interface host bindings for Airflow and Jenkins web ports; do not publish the Jenkins inbound-agent port.
- [x] Document Docker socket ownership and the approved Jenkins socket exposure risk.
- [x] Assess compute, storage, networking, monitoring, messaging applicability, and shared-infrastructure impact.
- [x] Identify pinned Spark worker decommission/occupancy behavior as an implementation verification gate; do not assume it works based on script presence.
- [x] Generate `aidlc-docs/current/construction/unit-2/infrastructure-design/infrastructure-design.md` and `deployment-architecture.md`.
- [x] Present Infrastructure Design for explicit approval before Unit 2 Code Generation.

## Infrastructure Design Questions

Host interface exposure is resolved below. The question is retained as the decision record.

### Question 1 — Host access to Airflow and Jenkins

How should the Airflow and Jenkins web interfaces be published on the host?

A) Bind both interfaces to loopback only: Airflow `127.0.0.1:8085` → container port `8080`, Jenkins `127.0.0.1:8098` → container port `8080`. Do not publish the Jenkins inbound-agent port because the approved local setup uses the web UI and does not require inbound agents. (Recommended.)

B) Bind the same host ports to all host interfaces for LAN access.

X) Other (specify bind address, host ports, and whether Jenkins inbound agents need a published port).

**[Answer]:** B

## Design Boundaries

- Airflow service startup depends on its dedicated PostgreSQL and successful initialization. The operator UI can remain available even if lakehouse services are unavailable; run readiness must fail closed when the target Spark/Kerberos prerequisites are not ready.
- The scheduler needs the Docker socket to create/remove both run containers. API server and DAG processor do not receive it. Preserve the selected Jenkins socket mount and record its broad Docker daemon control despite no current pipeline use.
- Docker-created containers require daemon-host-visible absolute bind sources for the run-pinned Bundle and credential files. Keep credential values outside Airflow environment variables and Git Bundle content.
- Keep the Airflow metadata volume and Jenkins home volume separate from Hive metastore PostgreSQL and all existing lakehouse volumes.
- Use the Compose service DNS name `spark` and port `7077` for the shared master. Confirm the worker's master URL and driver connectivity against the actual Compose service and network during implementation verification.
- Do not introduce a new queue service, worker scheduler, per-run Spark master, strict executor affinity, credential identity, or capacity claim.
- Verify that the pinned Spark worker can be decommissioned, inspected for foreign executor occupancy, and removed by the current Docker control boundary. The selected timeout can interrupt another application and must be observable.
- Preserve UAT/prod as unset, fail-closed Airflow endpoints. Hive catalog metadata alone does not configure their runtime endpoints.

## Approval Gate

After the host exposure answer is resolved, generate the Unit 2 infrastructure design artifacts and request explicit approval before Code Generation.

**Status**: Infrastructure design generated; awaiting explicit approval.
