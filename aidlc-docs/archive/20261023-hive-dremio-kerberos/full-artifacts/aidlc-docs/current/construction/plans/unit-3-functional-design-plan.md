# Functional Design Plan — Unit 3: Spark Runtime and Sample ETL

## Scope

This plan covers the existing Spark runtime, TPCH generator/loader, and the requested Dremio JDBC Space/view creation. Unit 3 consumes the Unit 1 Hive Metastore/RustFS foundation and Unit 2 `write-service-account` identity. It creates and populates `databaseA` and `databaseB` with Iceberg tables using the writer identity, then attempts matching Dremio Spaces and views without elevating the writer. Detailed images, Compose wiring, secret mounts, health checks, and deployment commands belong to later design stages. No application configuration changes are made in this stage.

Primary stories: US-CAT-02 and US-JDBC-01. Related stories: US-CAT-01, US-ID-01, US-AUTH-02, and US-DOC-01.

## Approved scope and constraints

- Replace the Spark/TPCH workload's Nessie catalog path with the already-running Hive Metastore catalog and RustFS storage configuration.
- Run ETL as `write-service-account`, using its Kerberos identity and separate RustFS credentials. Do not use `admin`, RustFS root, or PostgreSQL metastore credentials for ETL.
- Create and populate `databaseA` and `databaseB`; preserve the approved sample-data intent from the existing TPCH generator/loader.
- Create matching Dremio Spaces and a view for each Hive table over JDBC if the non-admin writer can do so with supported Dremio Community permissions. Never silently promote the writer to platform admin.
- Make reruns predictable and observable. Preserve existing data unless a separately approved cleanup/reset action is requested.
- Airflow/Jenkins orchestration is deferred. No Airflow/Jenkins services or integration are part of Unit 3.
- Unit 2 verified Spark-to-Hive namespace access using a Kerberos ticket cache in local mode. Keytab acquisition/renewal and the effective authorization path remain explicit verification items.

## Functional Design Checklist

- [x] Review Unit 3 stories, approved requirements, Unit 1/2 contracts, and current Spark/TPCH scripts.
- [x] Define Hive catalog selection and RustFS warehouse/table location behavior.
- [x] Define ETL identity, Kerberos credential acquisition, and separate RustFS credential delivery.
- [x] Define database/table contents and the manifest/reporting contract.
- [x] Define idempotent rerun, partial failure, and safe cleanup behavior.
- [x] Define Dremio JDBC authentication, Space/view naming, table-to-view mapping, and unsupported-permission behavior.
- [x] Define integration checks for Hive metadata, RustFS objects, Dremio visibility, and effective writer identity.
- [x] Generate Unit 3 functional design artifacts and validate them against approved scope.

## Answer Resolution

All five answers select **A** and are consistent with the approved requirements and Unit 1/2 contracts. The current TPCH schema defines eight tables; the design loads the same table set into both databases for comparable later access checks. Existing loader use of `createOrReplace` is explicitly superseded by the approved safe-rerun contract: matching tables are validated and left unchanged; conflicts fail without destructive repair. Kerberos keytab login remains an execution-mode gate and the design uses a protected pre-authenticated ticket cache for the verified local-mode path.

## Design Questions

### Question 1 — Sample database/table content

What should the existing TPCH workload create in the two databases?

A) Use the existing TPCH generator and loader to populate both databases with the selected existing table set, recording the exact table and row-count manifest during design (recommended; reuses the current workload and gives later query units stable inputs).

B) Create only a minimal hand-authored sample table in each database.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 2 — ETL rerun behavior

How should reruns behave when databases, tables, or data already exist?

A) Make setup idempotent: create missing databases/tables and load only when the target is empty or already at the expected state; detect conflicting/partial state and fail with a clear report. Do not drop or overwrite existing tables automatically (recommended; preserves persistent data).

B) Drop and recreate both sample databases on every run.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 3 — Kerberos credential use for the one-shot ETL

How should the local one-shot Spark ETL obtain the writer's Kerberos credentials?

A) Use the provisioned writer keytab to acquire a short-lived ticket for this isolated local ETL invocation, keep the cache/task-local credentials protected, and destroy temporary credentials at completion. Treat Spark standalone/local keytab login behavior as a compatibility gate and document any required pre-authenticated ticket-cache flow (recommended; avoids embedding passwords).

B) Use a manually acquired ticket cache only; the ETL command does not perform keytab login.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 4 — Dremio JDBC Space/view permission failure

What should the loader do if the non-admin writer can authenticate but Dremio Community denies Space or view creation?

A) Complete Hive/RustFS ETL, report JDBC Space/view creation as a distinct failed integration gate with the exact unsupported permission, and preserve the successful data. Do not retry as admin or mark JDBC setup complete (recommended; keeps the approved identity boundary intact).

B) Stop before ETL if the JDBC preflight cannot create a test object.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — Dremio object naming and JDBC view mapping

How should Hive databases/tables map to Dremio Spaces and views?

A) Use one Space per Hive database (`databaseA`, `databaseB`) and create one view per Hive table with a deterministic same-name mapping, recording every attempted/created object and the corresponding Hive path (recommended; directly follows the approved application design).

B) Create one shared Space and prefix view names with their Hive database.

X) Other (describe after `[Answer]:`)

[Answer]:A

## Feasibility Gates

- Confirm the selected Spark distribution can use the pinned Hive Metastore and Iceberg versions with Kerberos/SASL and RustFS S3A configuration.
- Demonstrate writer principal acquisition in the actual Spark execution mode; the Unit 2 local-mode test succeeded using a pre-authenticated ticket cache, while standalone `--principal/--keytab` did not acquire the ticket.
- Confirm the writer can create databases/tables in Hive and write only the approved RustFS prefixes; do not infer authorization from successful authentication.
- Verify Dremio Community behavior for non-admin JDBC Space/view creation. Preserve successful ETL results if this separate integration capability is denied.
- Keep cleanup non-destructive by default; destructive database/table cleanup requires a separately approved operation.

## Extension Compliance Summary

- **Security Baseline**: Disabled by user choice. Approved credential separation, secret redaction, local-only scope, and least privilege remain mandatory.
- **Property-Based Testing (Partial)**: Reassess if the design introduces a pure data-manifest or naming transformation; no tests are introduced in this planning step.
- **Resiliency Baseline**: Disabled by user choice. Safe retries and partial-result reporting remain required functional behavior.

## Current Status

Unit 2 Build and Test is complete. Unit 3 Functional Design was approved by the user on 2026-10-23 together with the Unit 3 NFR Requirements artifacts. Proceeded to Unit 3 NFR Design. No application configuration has been changed.
