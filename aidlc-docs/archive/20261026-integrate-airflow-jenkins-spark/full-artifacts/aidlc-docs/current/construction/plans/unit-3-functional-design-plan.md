# Unit 3 Functional Design Plan — Platform Compose Integration

## Unit Context

- **Unit**: Unit 3 — Platform Compose Integration.
- **Stories**: US-02, US-04, and US-05 cross-cutting deployment support.
- **Requirements**: FR-1 and NFR-5, plus the approved Airflow Bundle and Jenkins service contracts.
- **Dependencies**: Approved Unit 2 Functional/NFR/Infrastructure Design and completed Unit 2 Code Generation; existing Hive/RustFS/Spark Compose platform and `iceberg-poc-net`.
- **Workspace root**: `/Users/carlosdiogo/code_repo/hive-dremio-rustfs` (brownfield).
- **Inspected source**: `/Users/carlosdiogo/code_repo/airflow-spark-jenkins` for Airflow 3.3.2 Git Bundles, service topology, Jenkins, and current Docker configuration patterns. Its generated `.airflow-dag-bundles` directory is runtime cache, not source.
- **Service boundary**: Target Compose integration of Airflow 3 API server, LocalExecutor scheduler, DAG processor, triggerer, initializer, dedicated PostgreSQL, Jenkins, and runtime build/config files.
- **Preservation boundary**: Keep existing lakehouse services, network, published ports, credential files, and named data volumes. Do not reset or remove data.
- **Host interface decision**: Airflow UI host port `8085` and Jenkins UI host port `8098` bind all host interfaces; do not publish Jenkins inbound-agent port `50000`.

This plan covers functional behavior and service contracts. It does not authorize Compose edits, image builds, or service startup. Explicit approval of the generated Functional Design artifacts is required before NFR Requirements planning.

## Sequential Design Steps

### Step 1 — Define integrated Compose service behavior

- [x] Specify startup/dependency behavior for Airflow PostgreSQL, initialization, API server, scheduler, DAG processor, and triggerer.
- [x] Define Airflow's separate metadata database/volume ownership; distinguish it from Hive metastore PostgreSQL.
- [x] Specify Jenkins as validation-only with persistent home, selected Docker socket mount, and no Bundle publication or reference changes.
- [x] Preserve the existing `iceberg_net` key and `iceberg-poc-net` Docker network; state which services and run containers join it.
- [x] Define host port bindings, internal-only ports, and interface boundary from the approved Unit 2 Infrastructure Design.
- [x] Define service-level health/readiness expectations without claiming that process health proves Bundle, Docker, Kerberos, or Spark run readiness.

### Step 2 — Define host-path, secret, and Bundle configuration behavior

- [x] Specify the host-visible project root and identical Bundle storage path mapping needed by the DAG processor, scheduler, and Docker daemon.
- [x] Define `LAKEHOUSE_PROJECT_ROOT`, `LAKEHOUSE_BUNDLE_HOST_ROOT`, and `LAKEHOUSE_BUNDLE_CONTAINER_ROOT` ownership and fail-closed behavior for missing or mismatched paths.
- [x] Define how the target Git remote URL and Git credentials are supplied at deployment time; leave the remote configurable because the target project has no configured remote.
- [x] Preserve `lakehouse-main` and `lakehouse-uat` Bundle definitions so production and UAT DAGs are created. Keep their workload execution disabled and prevent fallback to dev.
- [x] Specify how Airflow web/admin bootstrap and API/Fernet secrets are supplied without reusing the sibling stack's `admin/admin` defaults or exposing secret values in source-controlled configuration.
- [x] Keep writer keytab and RustFS writer secrets out of Airflow services; only the scheduler receives host file paths needed for Docker bind creation. API server, DAG processor, triggerer, initializer, and Jenkins receive no writer credentials.

### Step 3 — Define image/configuration ownership and persistence

- [x] Select the maintained Airflow image/configuration from the inspected Airflow 3.3.2 setup while preserving version/constraints and required Git, Docker, FAB, and PostgreSQL providers.
- [x] Define Jenkins image/configuration ownership and validation-only command surface without adding Bundle publication or deployment behavior.
- [x] Define separate named volumes for Airflow PostgreSQL and Jenkins home, and Airflow logs if required by the selected service topology.
- [x] Explicitly preserve all existing lakehouse data volumes, networks, service ports, and credential sources.
- [x] Specify startup/stop behavior that does not implicitly remove named volumes or reset lakehouse state.

### Step 4 — Generate Functional Design artifacts

- [x] Generate `aidlc-docs/current/construction/unit-3/functional-design/business-logic-model.md`.
- [x] Generate `aidlc-docs/current/construction/unit-3/functional-design/business-rules.md`.
- [x] Generate `aidlc-docs/current/construction/unit-3/functional-design/domain-entities.md`.
- [x] Update `aidlc-docs/current/aidlc-state.md` and `aidlc-docs/current/audit.md` with the review gate.
- [x] Present all generated artifacts for explicit user approval before Unit 3 NFR Requirements planning.

## Design Constraints

- Preserve the approved all-interface HTTP UI bindings and document that TLS termination is not included.
- Keep the Docker socket only on the Airflow scheduler and approved Jenkins service; no socket on API server, DAG processor, triggerer, initializer, or PostgreSQL.
- Do not enable UAT/prod workload execution or use the writer identity for UI authentication. DAG registration in those bundles is required.
- Do not copy `.airflow-dag-bundles` runtime cache contents from the sibling project.
- Do not start/stop services, build images, change Compose, or reset volumes during Functional Design.

## Approval Gate

Functional Design artifacts are generated. Review them and provide explicit approval before Unit 3 NFR Requirements planning.

**Status**: Approved by the user on 2026-10-26. Functional Design artifacts are complete; proceeding to Unit 3 NFR Requirements planning.
