# Infrastructure Design Plan — Unit 3 Spark Runtime and Sample ETL

## Scope

Map Unit 3's approved generator, Spark/Hive/RustFS ETL, and Dremio JDBC exposure to concrete infrastructure in the existing single-host Compose project. Decide the one-shot workload boundary, image/runtime responsibilities, source/data/manifest storage, writer credential and ticket-cache mounts, service dependencies, readiness, private networking, and exact component integration interfaces. Do not implement Compose services or change application configuration in this stage.

The implementation must preserve scale factor 1, eight TPCH tables in both databases, non-destructive reruns, the writer's least-privilege identity, restricted secret handling, and separate ETL/JDBC outcomes. Do not add Airflow/Jenkins, monitoring infrastructure, a persistent scheduler, HA, or multi-host execution.

## Infrastructure Category Applicability

| Category | Applicability and evidence |
|---|---|
| Deployment environment | Applicable. Existing single-host Docker Compose project; no other environment is in scope. |
| Compute infrastructure | Applicable. Decide where generator, Spark loader, and JDBC adapter execute and how a one-shot invocation is launched. No persistent worker or scheduler. |
| Storage infrastructure | Applicable. Define generated TPCH input, persistent RustFS table objects, non-secret run manifest, and temporary ticket-cache locations. Preserve existing volumes and credentials. |
| Messaging infrastructure | Not applicable. Work is sequential and operator-triggered; no queue/event bus. |
| Networking infrastructure | Applicable. Workload calls KDC, Hive, RustFS, and Dremio through the private Compose network; no new host-published service port. |
| Monitoring infrastructure | Not applicable as a new component. Redacted command output and local logs are sufficient. |
| Shared infrastructure | Not applicable. No external scheduler, registry service, secret manager, or shared platform is required. |

## Infrastructure Design Checklist

- [x] Confirm one-shot execution boundary and generator/ETL/JDBC ordering.
- [x] Select runtime/image responsibility for Spark workload and any JDBC driver/client.
- [x] Map generated input files, persistent RustFS data, non-secret run manifest, and temporary ticket-cache lifecycles.
- [x] Define protected writer keytab, RustFS credential, and Dremio writer credential mounts independently.
- [x] Map service readiness dependencies and bounded retry behavior.
- [x] Define private network access and confirm no new host ports are needed.
- [x] Map database/table and Space/view creation responsibilities to concrete components.
- [x] Record Spark Kerberos, Hive/RustFS writer authorization, and Dremio JDBC capability gates.
- [x] Confirm scheduler, messaging, monitoring, and shared-infrastructure exclusions.
- [x] Generate Unit 3 infrastructure design and deployment architecture artifacts.
- [x] Validate against approved Functional Design, NFR Requirements, and NFR Design.

## Answer Resolution

All six answers select **A** and align with the approved design. The existing TPCH generator remains a profiled one-shot; a new profiled loader reuses the pinned Spark runtime, receives consumer-specific credentials, writes a non-secret manifest and ephemeral ticket cache to separate locations, and attempts Dremio JDBC only after ETL validation. The long-running Spark notebook/master service remains distinct from the ETL invocation.

## Questions

### Question 1 — One-shot workload execution model

How should the generator and ETL/JDBC steps be launched?

A) Add an explicit Compose one-shot workload profile/service, invoked by an operator after Unit 1/2 readiness. Keep it out of default startup and run generation, ETL, and JDBC steps sequentially with distinct results (recommended; gives a reproducible private-network runtime without adding a persistent service).

B) Run all generator/ETL/JDBC operations automatically on every normal Compose startup.

X) Other (describe after `[Answer]:`)

[Answer]:

### Question 2 — Spark runtime/image boundary

Where should the Unit 3 workload execute?

A) Reuse the existing pinned Spark image/runtime and mount the generator/loader code and data into a one-shot container; add only the JDBC client/driver dependency required by the existing Dremio interface (recommended; avoids introducing a second Spark distribution).

B) Build a new custom Spark distribution image with bundled code and all credentials baked into its runtime layers.

X) Other (describe after `[Answer]:`)

[Answer]:

### Question 3 — Input, output, manifest, and ticket-cache storage

How should local workload artifacts be stored?

A) Keep generated `.tbl` inputs in the existing workload data boundary, Iceberg table data in the existing RustFS persistent bucket, a non-secret run manifest in a clearly identified local output path, and the short-lived Kerberos cache in a separate restricted temporary path removed after each run (recommended; separates persistent data from ephemeral authentication).

B) Store the ticket cache and credentials alongside the persistent dataset so reruns can reuse them.

X) Other (describe after `[Answer]:`)

[Answer]:

### Question 4 — Credential mounts

How should the workload receive writer credentials?

A) Mount only the writer keytab and RustFS credential files read-only for ETL, then the Dremio writer password only for JDBC setup. Keep the temporary ticket cache writable but restricted, remove it on all exits, and do not mount admin/root/PostgreSQL credentials (recommended; enforces the approved consumer boundaries).

B) Mount the entire `.runtime/credentials` tree read-write into the workload for simplicity.

X) Other (describe after `[Answer]:`)

[Answer]:

### Question 5 — Service readiness and ordering

How should Compose represent readiness before each operation?

A) Require KDC, Hive Metastore, RustFS/bucket, Spark runtime, writer credential artifacts, and generated inputs before ETL; require Dremio readiness and successful ETL validation before JDBC setup. Use explicit operator-visible preflight and bounded retries only for transient availability (recommended; separates service health from capability).

B) Depend only on container start order and let the workload retry all errors indefinitely.

X) Other (describe after `[Answer]:`)

[Answer]:

### Question 6 — Dremio JDBC boundary and partial results

How should the Dremio integration execute and report failures?

A) Run the JDBC adapter after ETL as the non-admin writer, using the pinned Dremio JDBC interface and a separate credential mount. Record each Space/view outcome; if denied, preserve ETL output and return an overall partial result without admin fallback (recommended; matches approved NFR Design).

B) Run Dremio setup as administrator or roll back Hive/RustFS data when JDBC setup fails.

X) Other (describe after `[Answer]:`)

[Answer]:

## Feasibility Gates

- Confirm the selected Spark image can authenticate using a protected ticket cache in the actual local execution mode.
- Confirm writer DDL and RustFS writes are limited to the two approved databases/prefixes.
- Confirm Dremio JDBC driver/client compatibility and non-admin create-space/view behavior for the pinned Community version.
- Confirm temporary ticket caches are not retained in persistent volumes or manifests and are cleaned on failures/interruption.
- If a gate fails, record observed behavior and the smallest proposed adjustment for review; do not change pinned versions, data, or privilege scope silently.

## Extension Compliance Summary

- **Security Baseline**: Disabled by user choice. Credential separation, restricted mounts, secret redaction, and least privilege remain mandatory.
- **Property-Based Testing (Partial)**: Reassess if concrete infrastructure introduces a pure manifest/path transformation.
- **Resiliency Baseline**: Disabled by user choice. Bounded retries, safe reruns, and partial-state preservation remain required.

## Current Status

Unit 3 NFR Design answers are validated. Infrastructure Design artifacts are generated and ready for review; the Unit 3 Code Generation plan is prepared as the next stage. No application configuration has changed.
