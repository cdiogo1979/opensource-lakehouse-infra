# Unit 3 NFR Requirements Plan — Platform Compose Integration

## Unit and Approved Functional Baseline

This stage defines measurable quality requirements for integrating Airflow 3, its dedicated PostgreSQL, Git DAG Bundles, Jenkins, and the existing Compose lakehouse. The approved Unit 3 Functional Design covers startup dependencies, host-visible Bundle paths, credential boundaries, named-volume ownership, UI ports, and preservation of the existing lakehouse state.

Fixed decisions carried forward: Airflow UI is published as `8085:8080` and Jenkins UI as `8098:8080` on all host interfaces; Jenkins agent port `50000` is not published; only the Airflow scheduler and approved Jenkins service receive Docker socket access; the maintained `lakehouse-main` and `lakehouse-uat` Bundles are configured for production/UAT DAG registration, while UAT/prod workload execution remains disabled; Jenkins performs validation only; no TLS termination, volume reset, or production availability/capacity claim is included. These are design constraints, not open NFR questions.

Unit 2 owns run-level admission, five-minute paired readiness, 60-second paired cleanup, pinned workload behavior, and writer identity lifecycle. Unit 3 requirements must compose with those existing contracts without duplicating or weakening them.

## NFR Assessment Checklist

- [x] Read approved Unit 3 Functional Design, requirements, stories, Unit of Work, and existing Unit 2 NFR contracts.
- [x] Separate fixed infrastructure decisions from open measurable quality targets.
- [x] Assess availability and recovery for the local Compose PoC; no HA, RTO/RPO, or uptime objective is approved.
- [x] Identify questions for service readiness, persistent state, Bundle checkout safety, secret handling, and local resource scope.
- [x] Review answers and resolve any ambiguity or conflict before generating NFR Requirements. Answers A/A/A/A/A/A are clear and consistent with the approved Functional Design.
- [x] Generate `aidlc-docs/current/construction/unit-3/nfr-requirements/nfr-requirements.md`.
- [x] Generate `aidlc-docs/current/construction/unit-3/nfr-requirements/tech-stack-decisions.md`.
- [x] Validate against Unit 3 Functional Design, US-02/04/05, FR-1/6/8, and NFR-1/2/3/5.
- [x] Present the generated NFR Requirements for explicit approval before Unit 3 NFR Design.

## Assessment Boundaries

- **Availability/recovery**: Local single-host Compose only. No HA, automatic host recovery, external backups, uptime target, or disaster recovery objective has been approved.
- **Startup/readiness**: Define measurable service-level readiness for Airflow PostgreSQL, initialization, Airflow components, and Jenkins. Do not treat process health as Bundle or workload readiness.
- **Persistence**: Preserve named volume contents during ordinary lifecycle. The user has not requested backup/restore guarantees.
- **Bundle storage**: Keep run-pinned revisions available for active runs. Define any retention/cleanup bound without removing a revision still referenced by a run.
- **Security**: Existing credential isolation, read-only mounts, protected bootstrap secrets, host-path validation, and Docker socket boundaries remain explicit. The Security Baseline extension is disabled; this does not waive the approved requirements.
- **Scalability/performance**: No numeric throughput, latency, or capacity claim. Unit 2's existing maximum of two concurrent DAG runs is authoritative.
- **Property-based testing**: Apply only to eligible pure functions or serialization round-trips; do not force it on Compose orchestration or service lifecycle.

## NFR Questions

Please fill each `[Answer]:` tag. If no option fits, select X and describe the target.

### Question 1 — Integrated service readiness deadline

After `docker compose up`, how long may the Airflow control plane take to become ready after its dedicated PostgreSQL reports healthy and `airflow-init` succeeds?

A) Require Airflow API health within 5 minutes; if it misses the deadline, report the service unhealthy and leave diagnosis/restart to the operator. Jenkins readiness is independent. (Recommended for this local PoC.)
B) Require Airflow API health within 10 minutes; if it misses the deadline, report the service unhealthy and leave diagnosis/restart to the operator.
X) Other (provide a deadline and recovery behavior after `[Answer]:`).

**[Answer]:**A

### Question 2 — Health-check cadence and failure threshold

What service-health probe behavior should be required for Airflow PostgreSQL, Airflow API, and Jenkins?

A) Probe PostgreSQL/API/Jenkins every 10 seconds with a 5-second timeout; mark unhealthy after 3 consecutive failures. Keep the Airflow initializer's successful exit as a startup dependency, not a recurring health check. (Recommended.)
B) Probe every 30 seconds with a 10-second timeout; mark unhealthy after 3 consecutive failures.
X) Other (specify interval, timeout, and failure threshold after `[Answer]:`).

**[Answer]:**A

### Question 3 — Persistent state and recovery objective

Which persistence guarantee is required for Airflow metadata and Jenkins home in this local PoC?

A) Require data to survive ordinary container recreation and Compose stop/start through their dedicated named volumes; no backup, restore, or host-loss recovery guarantee. (Recommended; matches approved scope.)
B) Require operator-managed backup and documented restore procedures for both volumes, with an explicit recovery point and recovery time target.
X) Other (specify persistence, backup, and recovery targets after `[Answer]:`).

**[Answer]:**A

### Question 4 — Bundle revision retention

How should local Bundle checkout retention behave as new revisions are fetched?

A) Keep revisions needed by active runs; prune only inactive revisions older than 30 days, and report cleanup failures without blocking active runs. (Recommended.)
B) Do not automatically prune any Bundle revision; require operator cleanup.
X) Other (provide a retention bound and active-run safety rule after `[Answer]:`).

**[Answer]:**A

### Question 5 — Deployment secret file protection

What minimum file protection should apply to Airflow bootstrap/API/Fernet secret sources and Git credentials supplied at deployment time?

A) Require host files to be owner-readable only (mode `0600`), mount read-only where file mounts are used, exclude values from source control and diagnostics, and fail initialization if required secrets are missing. (Recommended.)
B) Require read-only mounts and source-control/log exclusion, but defer exact host mode and missing-secret failure behavior to deployment configuration.
X) Other (specify modes, mount behavior, and missing-secret handling after `[Answer]:`).

**[Answer]:**A

### Question 6 — Local resource limits and capacity statements

What resource policy should Unit 3 apply to the new Airflow/Jenkins/PostgreSQL services?

A) Preserve the existing host sizing and avoid fixed per-container CPU/memory limits in this PoC; record that no capacity guarantee is made. (Recommended.)
B) Set explicit CPU and memory limits for each new service (provide values after `[Answer]:`) and fail/report health if the limits prevent readiness.
X) Other (describe resource policy and any measurable capacity target after `[Answer]:`).

**[Answer]:**A

## Approval Gate

After answers are reviewed and ambiguities resolved, generate the Unit 3 NFR Requirements and technology decision artifacts. Request explicit approval before proceeding to Unit 3 NFR Design.

**Status**: Answers A/A/A/A/A/A recorded; NFR Requirements artifacts approved by the user on 2026-10-26. Proceeding to Unit 3 NFR Design planning.
