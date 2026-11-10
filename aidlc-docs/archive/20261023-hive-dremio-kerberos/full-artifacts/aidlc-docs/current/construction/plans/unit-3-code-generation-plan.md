# Code Generation Plan — Unit 3 Spark Runtime and Sample ETL

## Scope

Implement the approved Unit 3 infrastructure design in the existing local Compose project. Add the one-shot workload invocation, adapt the TPCH generator/loader to Hive-backed Iceberg and RustFS as `write-service-account`, implement non-destructive validation and manifest reporting, and attempt Dremio Spaces/views over the pinned JDBC interface. Preserve all existing persistent data and credential boundaries.

No Airflow/Jenkins, reader grant, JupyterHub, Dremio Hive source, end-user authorization demonstration, or automatic destructive cleanup is included.

## Code Generation Checklist

- [x] Map each infrastructure design artifact to concrete source/configuration files and responsibilities.
- [x] Adapt TPCH generator output to a runtime-only input path separate from persistent table data.
- [x] Adapt the Spark loader from Nessie/`tpch` to Hive Metastore and both databases with safe ensure/validate behavior.
- [x] Implement protected writer keytab-to-ticket-cache setup and cleanup for all exit paths.
- [x] Wire only writer-scoped RustFS credentials into the ETL consumer.
- [x] Add Dremio JDBC Space/view step using the non-admin writer and no replace/admin fallback.
- [x] Add profile-gated one-shot orchestration, preflight, and distinct ETL/JDBC results.
- [x] Add redacted run-manifest output and operator documentation.
- [x] Reconcile code with approved design/NFR artifacts and report unresolved feasibility gates.

## Questions

### Question 1 — Source changes

How should implementation be scoped relative to existing workload files?

A) Modify the existing `tpch-generator` output path and `tpch/load_tpch.py`, adding only the small wrapper/config files needed for the approved one-shot flow (recommended; reuses existing workload ownership and avoids duplicate loaders).

B) Leave existing scripts unchanged and add a separate parallel Unit 3 implementation.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 2 — Dremio driver artifact

How should the JDBC client be supplied to the reused Spark image?

A) Build from the pinned Dremio 26.0.5 image as a source stage and copy only its bundled legacy JDBC driver JAR into the workload image, after confirming the path. Keep the Spark runtime image/version unchanged and verify Java compatibility at build/test time (recommended; ties the client artifact to the pinned server).

B) Download an unpinned latest JDBC driver at container startup.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 3 — Code-generation completion boundary

How should unsupported JDBC or authorization behavior be handled in generated code?

A) Implement observable capability checks and truthful partial/blocked results while preserving successful data and writer privileges; stop for review if the exact pinned interface cannot be exercised (recommended; follows approved feasibility gates).

B) Broaden writer/admin access or change component versions automatically until the workload succeeds.

X) Other (describe after `[Answer]:`)

[Answer]:A

## Verification Boundaries

- Code Generation should add no sample data or run destructive operations against the persistent stack.
- Build and Test must validate Compose rendering, image build, keytab/cache lifecycle, Hive/RustFS write permissions, idempotent existing-state behavior, and Dremio JDBC permissions before claiming Unit 3 acceptance.
- Any unsupported required behavior must be summarized for review; do not silently alter the approved version, credential, or privilege boundary.

## Current Status

Unit 3 Code Generation answers are validated and the implementation is generated. ETL and Dremio JDBC run in separate one-shot containers so each receives only its required credentials. No build, Compose validation, sample-data generation, ETL, or runtime test was run in this stage. Review `aidlc-docs/current/construction/unit-3-spark-etl/code/implementation-summary.md`; the Build and Test plan is ready for approval.
