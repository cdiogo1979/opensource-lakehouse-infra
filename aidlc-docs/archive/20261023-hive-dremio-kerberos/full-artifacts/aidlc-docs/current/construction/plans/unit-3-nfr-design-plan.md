# NFR Design Plan — Unit 3 Spark Runtime and Sample ETL

## Scope

Translate the approved Unit 3 NFR requirements into logical patterns for dependency readiness, short-lived writer credentials, Spark catalog/storage configuration, safe ETL reruns, separate Dremio JDBC outcomes, and operator reporting. Concrete Compose syntax, mounts, environment variables, health commands, JDBC implementation, and retry durations remain Infrastructure Design/Code Generation decisions.

The design must preserve the fixed TPCH scale factor 1, eight tables per database, non-destructive persistence, writer least privilege, redacted output, and partial-result semantics. It must not claim keytab login, Hive/RustFS authorization, or Dremio Community JDBC support that has not been verified.

## NFR Design Checklist

- [x] Select readiness and dependency-gating patterns for generator, Spark ETL, and Dremio JDBC setup.
- [x] Select protected keytab/ticket-cache and RustFS credential delivery patterns.
- [x] Define safe rerun, conflict detection, bounded retry, and partial-failure patterns.
- [x] Define logical generator/loader/JDBC adapters and result/manifest flow.
- [x] Confirm no scheduler, monitoring service, HA, or scaling component is required.
- [x] Generate Unit 3 NFR design patterns and logical-component artifacts.
- [x] Validate the design against approved Unit 3 NFR Requirements and Functional Design.

## Answer Resolution

All six answers select **A** and align with the approved Unit 3 Functional Design and NFR Requirements. The workload is sequential and one-shot; credentials are delivered through consumer-specific restricted references; matching objects are validated without replacement; ETL and JDBC outcomes remain separate; and no scheduler, monitoring service, or scale-out topology is added.

## Questions

### Question 1 — Dependency gating

How should the one-shot workload handle service readiness?

A) Gate generation/loading on required Spark, KDC, Hive, RustFS/bucket, and writer-credential readiness; gate JDBC setup separately on Dremio readiness and successful ETL validation. Health and workload capability remain distinct (recommended; supports clear partial results).

B) Start all workload steps as soon as containers are running and retry all failures.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 2 — Credential delivery

How should the writer's Kerberos and RustFS credentials reach the workload?

A) Mount the writer keytab and RustFS credential files read-only to the one-shot workload; acquire a short-lived ticket into a restricted temporary cache and pass the cache reference to the Spark process. Remove the cache on all exit paths and never pass credential values in command arguments/logs (recommended; matches approved NFRs).

B) Pass credentials as ordinary environment variables or command arguments and retain the ticket cache for reuse.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 3 — Rerun and conflict handling

How should logical components recognize existing data?

A) Use ensure/validate operations: create missing objects, validate matching schema/count/targets, and stop on conflicts without overwrite. Retry only bounded transient readiness/availability operations (recommended; preserves persistent state).

B) Recreate existing tables and Dremio objects on each invocation to guarantee matching state.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 4 — Partial failure and reporting

How should the workload report results if Hive ETL succeeds but Dremio JDBC setup fails?

A) Keep the Hive/RustFS result, report ETL as complete and JDBC as failed, set overall state to partial, and allow an idempotent rerun of only validated outstanding work. Do not retry as admin (recommended; preserves the approved identity boundary).

B) Roll back successful Hive/RustFS work automatically when any JDBC operation fails.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — Logical component organization

How should the generator, ETL loader, and JDBC setup be separated?

A) Keep source generation, Hive/RustFS loading/validation, and Dremio JDBC exposure as distinct logical steps with a shared non-secret run manifest. Do not add a persistent scheduler or separate report database (recommended; supports isolated retries and clear ownership).

B) Combine all operations into one opaque script with only a final success/failure flag.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 6 — Scale and execution topology

What execution topology should the logical design target?

A) One sequential invocation on the existing local Compose host at scale factor 1. Avoid concurrent writers, distributed scheduling, and performance optimization without a measured need (recommended; follows approved NFRs).

B) Design for concurrent ETL jobs or multi-host scheduling; specify the required volume and isolation behavior.

X) Other (describe after `[Answer]:`)

[Answer]:A

## Applicability Notes

- Security Baseline and Resiliency Baseline extensions are disabled. Approved credential isolation, non-destructive reruns, bounded retry, and partial-result handling remain required.
- No performance SLA, HA, bulk data scale, or multi-host target exists.
- Writer keytab behavior, Hive/RustFS authorization, and non-admin Dremio JDBC permissions remain build-and-test feasibility gates.

## Extension Compliance Summary

- **Security Baseline**: Not enabled. Restricted credential delivery and secret-safe output remain mandatory.
- **Property-Based Testing (Partial)**: Reassess only if the design introduces pure manifest/path transformations.
- **Resiliency Baseline**: Not enabled. Safe reruns and partial-state preservation remain required by functional/NFR requirements.

## Current Status

All six Unit 3 NFR Design answers select the recommended patterns and are consistent with approved Functional Design and NFR Requirements. NFR design artifacts are generated and ready for review. The Unit 3 Infrastructure Design plan is prepared as the next stage. No application configuration has changed.
