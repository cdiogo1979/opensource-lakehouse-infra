# Unit 3 NFR Design Plan — Platform Compose Integration

## Approved Baseline

Unit 3 Functional Design and NFR Requirements were approved on 2026-10-26. The local Compose integration uses Airflow 3.3.2 with a dedicated PostgreSQL service, Git DAG Bundles, and validation-only Jenkins while preserving the existing lakehouse services and named data volumes.

The accepted NFR targets are: Airflow API healthy within five minutes after Airflow PostgreSQL health and successful initialization; 10-second health probes with five-second timeout and three consecutive failures for Airflow PostgreSQL/API/Jenkins; dedicated named-volume persistence through normal recreation and stop/start without backup/restore claims; retain active Bundle revisions and allow cleanup of inactive revisions older than 30 days; required Airflow bootstrap/API/Fernet secret files mode `0600` and read-only in containers; and no fixed CPU/memory limits or capacity claim.

Previously approved constraints remain fixed: all-interface Airflow UI port `8085`, Jenkins UI port `8098`, no Jenkins agent port `50000`, scheduler-only Airflow Docker socket plus the separately approved Jenkins socket, `iceberg-poc-net`, UAT/production workload execution disabled, no TLS termination, no volume reset, and Unit 2's existing run lifecycle limits. The user has since directed the implementation to preserve main and UAT Bundle definitions and verify DAG registration from both.

## Design Checklist

- [x] Read the approved Unit 3 Functional Design, NFR Requirements, technology decisions, and Unit 2 lifecycle/infrastructure contracts.
- [x] Trace dependencies for Airflow PostgreSQL, initializer, API, scheduler, DAG processor, triggerer, and Jenkins.
- [x] Define health-check design and startup deadline behavior for PostgreSQL, Airflow API, Jenkins, and the one-shot initializer.
- [x] Define persistence and recovery behavior for Airflow PostgreSQL and Jenkins named volumes without introducing backup/restore promises.
- [x] Design safe Bundle revision retention that never prunes active run revisions and handles concurrent cleanup/fetch/run activity.
- [x] Define secret-file ownership, container UID/GID access, read-only mounts, missing-secret startup failure, and sanitized diagnostics.
- [x] Define Docker socket, host-path, and network trust boundaries without broadening approved mounts.
- [x] Define local service failure states and operator-visible behavior without adding automatic restart, HA, or capacity claims.
- [x] Generate `aidlc-docs/current/construction/unit-3/nfr-design/nfr-design-patterns.md` and `logical-components.md`.
- [x] Validate alignment with Unit 3 Functional Design, U3-NFR-01 through U3-NFR-08, and existing Unit 2 limits.
- [x] Present the NFR Design for explicit approval before Unit 3 Infrastructure Design.

## Design Constraints

- Preserve the five-minute API readiness deadline, health-probe interval/timeout/failure count, 30-day inactive revision cleanup eligibility, and mode `0600` secret-source requirement.
- Retain all Bundle revisions referenced by active runs; cleanup must be race-safe with Bundle fetches and run creation. Do not change remote Git references.
- Ensure the configured container identity can read its mounted secret files while preserving owner-only host permissions and read-only container mounts; do not weaken permissions to work around UID/GID mismatch.
- Treat the Docker socket as broad host control. Keep it on only the approved services and do not claim it is least privilege.
- Keep health checks local and credential-safe. They do not prove workload readiness.
- Do not introduce new services, packages, proxies, backup systems, resource limits, restart policies, or performance claims unless already approved or required by a concrete implementation decision returned for approval.
- Do not edit Compose, build images, start services, reset volumes, or run tests during NFR Design.

## Approval Gate

The NFR Design artifacts are generated. Explicit user approval is required before Unit 3 Infrastructure Design.

**Status**: Approved by the user on 2026-10-26. Proceeding to Unit 3 Infrastructure Design planning.
