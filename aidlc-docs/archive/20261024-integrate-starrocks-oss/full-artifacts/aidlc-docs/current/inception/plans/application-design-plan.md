# Application Design Plan — StarRocks OSS Integration

## Purpose and Scope

Define the high-level components, component interfaces, and service orchestration needed to add StarRocks OSS to the existing Hive Metastore, Iceberg, RustFS, Kerberos, and Spark/Jupyter environment. Preserve the approved boundary that Airflow/Jenkins integration and Ranger are out of scope. Detailed behavior, grants, retry rules, and configuration values will be specified during Construction Functional and Infrastructure Design.

## Baseline Decisions to Preserve

- StarRocks is an additive analytical SQL engine; Hive Metastore remains the Iceberg catalog and Spark/Jupyter remain supported.
- StarRocks uses a dedicated Kerberos service identity for Hive Metastore access and a dedicated RustFS identity scoped to the Iceberg warehouse.
- Per-user Kerberos propagation through StarRocks is not required. Native StarRocks SQL users and roles enforce the approved access matrix.
- The intended access matrix is `user_a` read databaseA only, `user_b` read both databases, `write_service_account` read/write both, and `admin` full StarRocks access.
- Deployment is one StarRocks FE and one BE with persistent state; host-published endpoints remain loopback-only.
- Existing shared metadata, object data, services, and the sibling Airflow/Jenkins project are preserved.

## Planning Tasks

- [x] Review approved requirements, stories, and current canonical application and functional design.
- [x] Resolve the component-boundary, interface, orchestration, dependency, and design-constraint questions below.
- [x] Analyze answers for ambiguity, conflict, or missing rules; add follow-up questions if needed.
- [x] Obtain explicit approval of this Application Design plan before producing design artifacts.
- [x] Define components and their high-level responsibilities and interfaces in `inception/application-design/components.md`.
- [x] Define component method signatures, input/output contracts, and purposes in `inception/application-design/component-methods.md`.
- [x] Define services and orchestration patterns in `inception/application-design/services.md`.
- [x] Define component dependencies, communication patterns, and data flow in `inception/application-design/component-dependency.md`.
- [x] Consolidate the above into `inception/application-design/application-design.md`.
- [x] Validate completeness and consistency against the approved requirements, stories, and canonical baseline.
- [x] Present the artifacts for explicit design approval before proceeding to Units Generation; design approved.

## Application Design Questions

Fill each `[Answer]:` line with an option letter. Choose `D) Other` and describe your choice if no listed option fits.

### Question 1 — Component boundaries

How should the new StarRocks integration be divided into logical components for design and later implementation units?

A) StarRocks runtime (FE/BE and config), identity provisioning (Kerberos/RustFS), and SQL bootstrap (catalog/users/roles/grants) as separate components

B) StarRocks runtime and SQL bootstrap as one component, with identity provisioning separate

C) One StarRocks integration component covering runtime, identities, and SQL bootstrap; keep shared platform services as dependencies

D) Other (describe after `[Answer]:`)

[Answer]:A

### Question 2 — Component interfaces

What interface style should the design use between the Compose/runtime, identity provisioning, and StarRocks bootstrap components?

A) File and environment contracts: generated credentials/configuration are mounted or passed through environment variables, and bootstrap uses StarRocks SQL

B) Explicit command-line contracts: provisioning and bootstrap expose scripts/commands with documented inputs, outputs, and exit status

C) Both: command-line entry points orchestrate operations while files/environment and SQL define the service-level contracts

D) Other (describe after `[Answer]:`)

[Answer]:A

### Question 3 — Service orchestration

How should initial setup coordinate identity readiness, StarRocks readiness, and catalog/account bootstrap?

A) Compose health/dependency ordering plus a separate explicit, repeatable bootstrap command after services start

B) Compose health/dependency ordering plus an idempotent bootstrap service that runs automatically when FE is ready

C) Manual operator sequence documented as commands, with health checks but no automated bootstrap orchestration

D) Other (describe after `[Answer]:`)

[Answer]:A

### Question 4 — Dependency and credential ownership

Where should the StarRocks service identity and RustFS credential contracts be owned?

A) The existing identity provisioner owns credential creation/policy; StarRocks consumes mounted keytab/config and environment or mounted S3 credentials

B) A StarRocks-specific provisioner owns both identities and policies; the existing provisioner remains unchanged

C) Split ownership: existing KDC/provisioning scripts own the Kerberos principal, while a StarRocks-specific step owns the RustFS identity and policy

D) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — Design constraints

Which constraints should shape the component interfaces and deployment boundary?

A) Keep implementation Compose-native and local: mounted config/secrets, health checks, and loopback host ports; avoid adding a control-plane API

B) Add a small local control/bootstrap API to manage catalog and SQL access, in addition to Compose services

C) Keep the runtime Compose-native, and allow a narrowly scoped helper API only if StarRocks cannot provide a needed bootstrap operation through SQL

D) Other (describe after `[Answer]:`)

[Answer]:A

## Approval Gate

Answers are complete and no ambiguity or conflict was found. Review this plan and explicitly approve it before design artifacts are generated. The artifacts will then be presented for a separate design approval before Units Generation.
