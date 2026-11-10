# Application Design Plan

## Scope

This stage defines high-level component responsibilities, interfaces, and orchestration for the approved Hive/Kerberos PoC. It uses the approved requirements, user stories, reverse-engineering artifacts, and execution plan. Detailed authorization rules and service configuration are left for per-unit Functional and Infrastructure Design.

The design must preserve these boundaries: `write-service-account` runs the sample Spark ETL and creates both Hive databases/tables in RustFS; the same user can create an object in a designated Dremio Space over JDBC; Airflow/Jenkins integration remains deferred; test-user allow/deny behavior is demonstrated through Dremio and Jupyter Spark.

## Design Questions

### Question 1 — Sample ETL boundary

How should the sample ETL that creates `databaseA`, `databaseB`, and their tables fit the existing workload services?

A) Extend the existing one-shot `tpch-loader` to create/populate both Hive databases as `write-service-account` (recommended; keeps the existing loader boundary).

B) Add a separate one-shot `sample-etl` service and keep the TPCH loader as a separate workload.

X) Other (please describe after [Answer]: below)

[Answer]: A

### Question 2 — Authorization and identity bootstrap ownership

Where should creation of principals, user mappings, and database/storage permissions be coordinated?

A) Keep each policy with its owning component configuration and use the existing startup/init flow only to sequence setup (recommended; avoids a new policy service boundary).

B) Add a dedicated one-shot provisioning service to create users and apply database/storage permissions.

X) Other (please describe after [Answer]: below)

[Answer]: B

### Question 3 — Dremio writer Space setup

How should the existing Dremio Space required for JDBC object creation be provided?

A) Have the Dremio administrator pre-create a dedicated Space named `etl_write`; the writer creates objects inside it (recommended; matches the requirement for an existing Space).

B) Use a Space that the operator has already created and provide its name in local configuration.

C) Create a dedicated Space automatically during setup if the selected Dremio Community version permits it.

X) Other (please describe after [Answer]: below)

[Answer]: X create two spaces , one matching to each database. the objects of the underlying database should be reflected there as views

## Answer Analysis

- **Q1**: Extend the existing `tpch-loader` boundary for the one-shot sample ETL; it will create and populate both Hive databases as `write-service-account`.
- **Q2**: Add a dedicated one-shot provisioning service for identities and database/storage permissions. This supersedes the execution plan's initial recommendation to keep all setup within component configuration; the service will orchestrate component-owned interfaces and must not become a new runtime authorization authority.
- **Q3**: Create two Dremio Spaces, `databaseA` and `databaseB`, corresponding to the Hive databases, and represent their underlying objects there as views.
- **Q4**: Create one view for every Hive table in its corresponding Dremio Space as part of the sample ETL. `write-service-account` creates those views over JDBC.
- **Feasibility note**: Space-level access for the two Dremio users and non-admin JDBC view creation must be validated against the selected Dremio Community version. Do not use administrator privileges to conceal a missing capability.

## Application Design Checklist

- [x] Review the approved requirements, stories, reverse-engineering artifacts, execution plan, and relevant canonical knowledge paths.
- [x] Validate all answers and resolve ambiguity before requesting approval.
- [x] Obtain approval for the application-design approach.
- [x] Define components, responsibilities, and high-level interfaces in `components.md`.
- [x] Define high-level component method/operation signatures and inputs/outputs in `component-methods.md`; defer detailed rules to Functional Design.
- [x] Define orchestration services and interactions in `services.md`.
- [x] Define dependency relationships and communication patterns in `component-dependency.md`.
- [x] Consolidate the design in `application-design.md`.
- [x] Check consistency with approved scope, component ownership, identity flows, and deferred Airflow/Jenkins integration.

## Extension Compliance Summary

- **Security Baseline**: N/A — disabled by user choice. The approved functional security requirements are represented in the design boundaries.
- **Property-Based Testing (Partial)**: N/A for this high-level design stage; no code or pure transformation functions were introduced. Reassess applicable functions during Functional Design.
- **Resiliency Baseline**: N/A — disabled by user choice.

## Planned Artifacts

- `aidlc-docs/current/inception/application-design/components.md`
- `aidlc-docs/current/inception/application-design/component-methods.md`
- `aidlc-docs/current/inception/application-design/services.md`
- `aidlc-docs/current/inception/application-design/component-dependency.md`
- `aidlc-docs/current/inception/application-design/application-design.md`

## Current Status

All four answers and the revised execution-plan inventory are approved. The five Application Design artifacts have been generated and checked against the approved requirements, user stories, identity boundaries, and deferred scope. Waiting for review and approval of the design artifacts before proceeding to Units Generation. No application configuration has been changed.
