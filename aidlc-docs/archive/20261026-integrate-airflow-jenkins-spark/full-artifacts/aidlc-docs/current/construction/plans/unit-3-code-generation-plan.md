# Unit 3 Code Generation Plan — Platform Compose Integration

## Unit Context

- **Unit**: Unit 3 — Platform Compose Integration.
- **Stories**: US-02, US-04, and US-05 cross-cutting deployment integration.
- **Requirements**: FR-1, FR-6, FR-8, NFR-1, NFR-2, NFR-3, and NFR-5; U3-NFR-01 through U3-NFR-08.
- **Dependencies**: Approved Unit 3 Functional Design, NFR Requirements, NFR Design, and Infrastructure Design; completed Unit 2 Bundle runner and Unit 1 Spark runtime.
- **Workspace root**: `/Users/carlosdiogo/code_repo/hive-dremio-rustfs` (brownfield).
- **Maintained source**: `/Users/carlosdiogo/code_repo/airflow-spark-jenkins` for Airflow 3.3.2 service topology and Jenkins conventions. Do not copy its weak `admin/admin`, blank Fernet, default AWS credentials, published SSH/agent ports, Spark-based Airflow controller image, or generated Bundle cache.
- **Existing target**: `docker-compose.yml` already defines `iceberg_net` / `iceberg-poc-net`, existing lakehouse services/volumes, and a JupyterHub Docker socket mount. Preserve them.
- **Service boundary**: Add Airflow services, dedicated PostgreSQL, Jenkins validation service, image/configuration support, safe secret provisioning references, and documentation. Do not change Unit 1/2 workload logic.
- **Data boundary**: Existing Hive, RustFS, Spark, metastore, KDC, JupyterHub, and StarRocks state is preserved. No volume reset or migration is included.

This plan is the source of truth for Unit 3 Code Generation. It permits the implementation files listed below only after explicit plan approval. Do not run tests, build images, start/stop services, or manipulate volumes during Code Generation; Build and Test owns verification.

## Sequential Generation Steps

### Step 1 — Add a dedicated Airflow runtime image and configuration

- [x] Add a target Airflow image based on a pinned official Apache Airflow `3.3.2` Python `3.10` image digest; keep it separate from the Spark image.
- [x] Add provider requirements for Git Bundles, Docker API integration, FAB authentication, and PostgreSQL, pinned through the official Airflow 3.3.2 constraints; do not install unpinned packages.
- [x] Configure Airflow 3 LocalExecutor and the approved API server, scheduler, DAG processor, triggerer, and initializer commands.
- [x] Configure the maintained `lakehouse-main` (`main`) and `lakehouse-uat` (`uat`) Git Bundles with `lakehouse_git`, a 300-second refresh, and sparse dirs `dags`, `configs`, and `notebooks`. Production/UAT workload configurations remain disabled and fail closed.
- [x] Use Airflow-supported `_CMD` configuration for file-backed metadata DB, Fernet, API, and JWT secrets only where supported by Airflow 3.3.2. Do not place secret values in Compose environment literals, image layers, or logs.
- [x] Bootstrap the Airflow administrator idempotently using a supported mechanism that keeps the password out of shell arguments and logs. If this cannot be implemented without exposing the password, return with the concrete gap for approval rather than weakening the boundary.

### Step 2 — Integrate Airflow and Jenkins in Compose

- [x] Add Airflow PostgreSQL, one-shot initializer, API server, LocalExecutor scheduler, DAG processor, and triggerer services, all on existing `iceberg_net`.
- [x] Reuse the existing digest-pinned PostgreSQL 16 base image while defining an Airflow-only database/password and new `airflow-postgres-data` named volume.
- [x] Add Airflow service health checks and dependencies: PostgreSQL `pg_isready`; initializer after database health; application components after initializer success; API `/api/v2/version` readiness with a 240-second start period, 10-second interval, five-second timeout, and three-failure threshold; Jenkins independent local HTTP health.
- [x] Inspect Airflow `/api/v2/monitor/health` JSON component values where component status is required; do not treat its HTTP 200 alone as complete Airflow health.
- [x] Add Jenkins service using a pinned immutable official Jenkins LTS image, network `iceberg_net`, persistent `jenkins-home`, all-interface `8098:8080`, and the approved Docker socket. Do not publish port `50000` or add a Docker daemon package unless a validated CI requirement needs it.
- [x] Add Airflow all-interface UI binding `8085:8080`; do not add any other public ports.
- [x] Preserve the existing JupyterHub Docker socket mount and all existing services/profiles/ports/credentials/volumes. New socket mounts are limited to Airflow scheduler and Jenkins; no Airflow API/processor/triggerer/initializer/PostgreSQL socket.
- [x] Add only new Airflow/Jenkins secrets and volumes; retain the existing `iceberg_net` external identity and all lakehouse storage ownership.

### Step 3 — Add protected deployment secret and path references

- [x] Add an idempotent provisioning helper for absent Airflow-specific secret files under ignored `.runtime/credentials`; use secure random values, mode `0600`, and refuse to overwrite existing files unless a separately approved rotation action is added. Do not run the helper during Code Generation.
- [x] Add required non-secret path/config inputs for `LAKEHOUSE_PROJECT_ROOT`, `LAKEHOUSE_BUNDLE_HOST_ROOT`, and `LAKEHOUSE_BUNDLE_CONTAINER_ROOT`; validate absolute path consistency and fail closed. Do not guess a fallback.
- [x] Ensure the Airflow DAG processor and scheduler mount the Bundle checkout at the same container path and the Docker daemon sees the same host directory. Use ignored `.runtime/airflow-dag-bundles`; do not copy sibling runtime Bundle caches.
- [x] Mount Airflow-only secret files read-only where needed and preserve host mode `0600`. Specify/run processes with a UID/GID that can read the files; do not loosen permissions to compensate for identity mismatch.
- [x] Keep writer keytab/RustFS credential values out of every Airflow service and Jenkins. Do not alter existing Unit 2 driver/worker credential mounts.
- [x] Keep automatic Git Bundle pruning disabled. Do not implement custom revision deletion unless a later approved design and implementation prove race-safe active-run references and coordination.

### Step 4 — Document and summarize the integration

- [x] Update `README.md` with Airflow/Jenkins URLs, first-start prerequisites, secret provisioning command (without running it), deployment path variables, and the maintained Bundle list/connection requirement.
- [x] Document that Airflow health covers service responsiveness, not Spark/Kerberos/metastore/RustFS readiness; document all-interface HTTP exposure and no TLS termination.
- [x] Document Docker socket boundaries and the retained pre-existing JupyterHub socket mount.
- [x] Create `aidlc-docs/current/construction/unit-3/code/code-summary.md` listing changed files, requirement traceability, deliberate Bundle cleanup disablement, exclusions, and Build and Test gaps.
- [x] Update AI-DLC state, audit, and checklist. Do not add or run tests, build images, start/stop services, inspect secret contents, or reset/remove volumes.

## Explicitly Excluded

- Changes to Spark entrypoint, Unit 2 DAG factory/workload, writer identities, Kerberos principals/keytabs, RustFS credentials, Hive catalogs/data, or StarRocks.
- Any edit to existing service behavior unrelated to Compose integration, including existing JupyterHub socket mount, network name, published ports, and data volumes.
- Bundle publishing/ref mutation, Jenkins deployment behavior, Jenkins inbound-agent port, TLS/reverse proxy, external secret manager, backup service, message broker, monitoring stack, fixed CPU/memory limits, and performance/capacity claims.
- Tests, image builds, service startup/shutdown, credential generation execution, and volume operations.

## Build and Test Handoff

The later integrated Build and Test stage must verify:

- Rendered Compose preserves existing services, profiles, ports, secret mappings, network, and volumes while adding the approved Airflow/Jenkins resources.
- Airflow secrets are generated only when the operator runs the helper, remain mode `0600`, are not overwritten, mount read-only, and do not leak through process arguments/logs.
- Airflow PostgreSQL and initializer dependencies work; API becomes healthy within five minutes; probe intervals and failure counts match requirements.
- Airflow/Jenkins data survives ordinary container recreation and stop/start without changing lakehouse volumes.
- All new service network paths, Docker socket boundaries, UI port bindings, and absence of host port `50000` match design; existing JupyterHub socket mount remains.
- Git Bundle source config loads exactly main and UAT; container/host paths resolve identically; driver receives pinned Bundle read-only; UAT/prod execution remains fail-closed.
- The post-start DAG registration check sees `main-init_environment` in `lakehouse-main` (production) and `uat-init_environment` in `lakehouse-uat` before this integration is accepted.
- Bundle pruning is absent/disabled unless a future approved implementation proves it safe with active runs.
- Unit 2 readiness, writer identity, data write, and cleanup behavior still work after Compose integration.

No test is added or run during Code Generation. Do not report design-level checks as runtime validation.

## Approval Gate

Review this complete plan. Explicit approval is required before edits to Compose, Dockerfiles, Airflow/Jenkins configuration, secret-provisioning support, README, or code-summary artifacts.

**Status**: Approved and generated on 2026-10-26. See `../unit-3/code/code-summary.md`. Build and Test remains pending.

## Approved Revision — Bundle List and DAG Registration Check

The user explicitly revised the approved dev-only Bundle restriction: preserve the existing sibling list (`lakehouse-main` + `lakehouse-uat`) and verify that production/UAT DAGs are registered. This revision does not enable running UAT or production workloads. The code change is limited to the Bundle JSON/validator, documentation, and a post-start DAG registration check; it does not change Spark identity or workload behavior.
