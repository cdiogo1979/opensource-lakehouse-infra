# Infrastructure Design Plan — Unit 1 Foundation

## Scope

Map Unit 1's approved logical foundation to concrete services and deployment choices in the existing single-host Docker Compose PoC: Hive Metastore, metastore PostgreSQL, the disposable Kerberos KDC, RustFS, bucket initialization, credential/runtime-file handling, networks, volumes, and lifecycle/readiness integration. Existing NFR constraints require loopback-only host exposure, one instance per service, local ignored credentials, safe retries, and persistent state. Later units own the identity provisioner, ETL, Dremio source/JDBC objects, and Jupyter user sessions; this plan records only the shared infrastructure contracts those units must consume.

The design must not claim that Hive storage-based authorization is proven over RustFS or that Dremio/Spark preserve effective users. Version compatibility and those authorization outcomes remain feasibility gates. No application configuration is changed during planning.

## Infrastructure Category Applicability

| Category | Applicability and evidence |
|---|---|
| Deployment environment | Applicable. Approved NFRs and execution plan select one local Docker Compose host; confirm developer-host assumptions and whether deployment remains strictly local. |
| Compute infrastructure | Applicable. Concrete KDC and Hive Metastore image/runtime choices and local resource assumptions are deferred. One instance per service is fixed; no scaling question is reopened. |
| Storage infrastructure | Applicable. Exact metastore PostgreSQL version, metadata/warehouse persistence boundaries, RustFS/bucket configuration, and volume lifecycle require concrete mapping. |
| Messaging infrastructure | Not applicable. No message broker, queue, event bus, or asynchronous service integration exists in the approved Unit 1 design; the Compose dependency graph provides startup ordering. |
| Networking infrastructure | Applicable. Compose-internal service topology is established; loopback-only published ports are mandatory. Confirm host port preservation and local access needs. |
| Monitoring infrastructure | Not applicable as an added platform. Approved requirements explicitly exclude monitoring/alerting stacks; Compose health/status and actionable logs are the selected pattern. |
| Shared infrastructure | Not applicable. This is one isolated Compose project for one operator, with no shared environment or multi-tenancy requirement. Stateful volumes and credentials remain project-local. |

## Infrastructure Design Checklist

- [x] Confirm local deployment and host prerequisites for the foundation.
- [x] Select concrete candidate service images/versions and persistence choices, preserving pinned RustFS where compatible.
- [x] Define runtime credentials/keytab generation, storage and read-only mount boundaries.
- [x] Define internal network, loopback host ports, dependency order, and readiness contracts.
- [x] Confirm messaging, monitoring, and shared-infrastructure exclusions with applicability rationale.
- [x] Generate `aidlc-docs/current/construction/unit-1-foundation/infrastructure-design/infrastructure-design.md`.
- [x] Generate `aidlc-docs/current/construction/unit-1-foundation/infrastructure-design/deployment-architecture.md`.
- [x] Validate concrete choices against approved Functional Design, NFR Requirements, NFR Design, and feasibility gates.

## Planning Questions

### Question 1 — Deployment environment

Which environment should the infrastructure target?

A) Keep the approved single developer workstation and Docker Compose project as the only target; no LAN/remote deployment or cloud target (recommended; matches the approved local-only boundary).

B) Add a second deployment target; name the environment and its additional boundary.

X) Other (describe after `[Answer]:`)

[Answer]:A — Keep Hive 3.1.3 and accept archived/EOL status and amd64 emulation on the current arm64 host for this local PoC.

### Question 2 — Compute images and resource assumptions

How should concrete Hive/KDC service images and local resource configuration be selected?

A) Choose maintained, reproducible pinned image versions that satisfy the Hive 3.x, Kerberos, Java, and client compatibility gates; retain the existing Dremio/Spark/RustFS pins where compatible and document minimum practical local resources rather than setting a performance target (recommended; preserves repeatability and approved NFR scope).

B) Require a named vendor/distribution or explicit resource limit; specify the preferred Hive/KDC image source and host limits.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 3 — Metastore database and persistent storage

How should metadata and object data be persisted?

A) Use a separately version-pinned PostgreSQL service and named volumes for its Hive metadata and RustFS object data; keep Hive metadata separate from RustFS objects, and preserve both on stop/restart (recommended; matches Functional Design and NFRs).

B) Use a different metadata database or persistence model; specify it and the migration/retention expectation.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 4 — Local network and published ports

How should existing host ports and service access be handled?

A) Keep required developer access on the existing configured host port numbers where possible, bind every published port explicitly to `127.0.0.1`, and use Compose DNS for service-to-service traffic (recommended; satisfies the approved exposure boundary while minimizing operator changes).

B) Change specific host ports or avoid publishing specific services; describe the access needs.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — Credential and keytab provisioning boundary

Where should foundation credentials and keytabs be created and supplied?

A) Generate them through an explicit local bootstrap step into a git-ignored, host-restricted runtime directory; mount only consumer-specific files read-only, keep separate service credentials, and fail startup if required inputs are missing (recommended; follows approved NFR Design).

B) Use file-backed Docker Compose secrets for credentials/keytabs where supported; specify any local source-file handling exception.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 6 — Messaging, monitoring, and shared infrastructure

Should any shared or supporting infrastructure be added to Unit 1?

A) Add no broker/queue, monitoring/alerting stack, or shared service. Use Compose health/status, local logs, one project network, project-owned volumes, and local runtime credentials (recommended; these categories are excluded or not applicable in the approved design).

B) Add a named component or shared service and describe its owner, purpose, and isolation boundary.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 7 — Initialization and dependency ordering

How should the infrastructure encode one-shot setup and downstream readiness?

A) Gate service consumers on health/readiness and one-shot dependents on successful completion; bound retries to safe idempotent operations, and keep overall readiness false after a required initializer fails (recommended; directly follows approved NFR Design).

B) Use a different startup/recovery model; describe how it preserves state and prevents premature downstream work.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Follow-up Question 8 — Hive 3.x support and host architecture

The requested Hive 3.x line's latest release, 3.1.3, is archived/EOL by Apache; the official `apache/hive:3.1.3` image is published for amd64 only. The current development host reports arm64. This conflicts with Question 2's selected requirement to use maintained images, and using this image here would require amd64 emulation without upstream fixes.

Which constraint should the Infrastructure Design prioritize?

A) Keep Hive 3.1.3 for this local PoC, explicitly accept its archived/EOL status and amd64 emulation on this arm64 host, and retain the version as a compatibility candidate subject to integration verification (recommended only if Hive 3.x is a hard requirement).

B) Amend the Hive 3.x requirement and evaluate the currently active Apache Hive 4.2.1 standalone Metastore image, which has amd64 and arm64 variants; this requires reviewing the major-version change against Spark 3.5.5, Iceberg 1.8.1, and Dremio 26.0.5 before implementation.

C) Use a named vendor-supported, patched Hive 3.x distribution; specify the vendor and confirm its image is available for this Compose/arm64 development target. This may require a commercial subscription.

X) Other (describe after `[Answer]:`)

[Answer]:A

## Current Status

Infrastructure Design answers and follow-up are complete. The approved local PoC accepts Hive 3.1.3's archived/EOL status and amd64 emulation on the current arm64 host. Design artifacts are complete and await explicit user approval. Compatibility and authorization outcomes remain unverified feasibility gates. No application configuration has been changed.

## Extension Compliance Summary

- **Security Baseline**: Disabled. Approved local credential separation, ignored runtime storage, loopback-only exposure, and redacted logs are specified as infrastructure requirements.
- **Property-Based Testing**: Partial extension; not applicable to infrastructure design artifacts because no code or tests are introduced.
- **Resiliency Baseline**: Disabled. Approved fail-closed readiness, bounded idempotent retries, and persistent-state recovery rules are reflected in the service graph.
