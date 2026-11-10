# Build and Test Plan — Unit 3 Spark ETL and Dremio JDBC

## Objective

Build and verify the generated workload path against the existing local stack while preserving all persistent volumes, credentials, and existing catalog/object data. The plan exercises the opt-in generator, non-destructive Hive/RustFS ETL as `write-service-account`, and separate Dremio JDBC Space/view phase.

## Preconditions

- User approves this Build and Test plan.
- Unit 1 and Unit 2 services are available; identity provisioning completed successfully.
- `.runtime/identity-provisioning/rustfs-ready`, the writer keytab, writer RustFS key files, and Dremio writer password exist and match the provisioned identities.
- Dremio local `write-service-account` exists and is not an administrator.
- Existing data and volumes are preserved. No credential rotation, volume reset, table drop, object deletion, or admin fallback is authorized by this plan.

## Verification sequence

### 1. Preflight and static configuration

- Inspect required runtime credential file presence/modes without displaying contents.
- Run local bootstrap only if needed and confirm it preserves existing credential files.
- Validate Compose rendering and inspect the workload service mounts/environment names without printing secret values.
- Confirm normal Compose startup excludes workload services, generator has no credentials, ETL gets only writer keytab/RustFS credentials, and JDBC gets only the Dremio writer password.

**Pass:** Compose parses; service boundaries and runtime-only paths match the design.

### 2. Build the derived workload image

- Build `tpch-generator` and `tpch-loader` images; `tpch-jdbc` uses the same derived image.
- Confirm the image contains `kinit`, Java 17, and the Dremio legacy JDBC driver copied from the pinned 26.0.5 image.
- Do not print credential values or add them to build context/image layers.

**Pass:** both images build with pinned bases and required tools/artifact.

### 3. Generate and preflight inputs

- Run `./scripts/run-tpch-workload.sh` only after confirming the existing volume state and that the generated runtime input directory is separate from `tpch/data`.
- Verify exactly the required eight non-empty `.tbl` inputs are available to the ETL container as read-only files.

**Pass:** generation succeeds under `.runtime/workload/tpch-data`; repository fixtures and persistent platform data remain untouched.

### 4. Kerberos, Hive and RustFS ETL

- Verify the ETL phase obtains the ticket using the writer keytab and the temporary cache is removed on normal exit; inspect only ticket principal/metadata, never keytab contents or credential values.
- Verify Spark's effective identity is `write-service-account` and the loader creates the two requested Hive databases/tables in RustFS-backed Iceberg storage.
- Confirm expected schemas and row counts in the manifest. Rerun only if current tables match the expected schema/count; conflicting existing state must fail closed and be reported without modification.

**Pass:** both databases and all eight tables are present with expected schema/count; writer identity is effective; no existing data was replaced; ticket cache is gone before JDBC phase.

### 5. Dremio JDBC and manifest

- Confirm JDBC runs in its separate service with no keytab/cache or RustFS secrets.
- Verify writer authentication and attempt the two Spaces and one view per table. Confirm existing objects are validated and conflicting objects are reported without replacement.
- Record capability errors and per-object results. A missing `hive` source or denied non-admin operation may yield `overall=partial`; do not retry as admin and do not roll back successful ETL.
- Inspect the manifest for run ID, ETL/JDBC state, identity, schemas/counts, and redacted diagnostics. Confirm no passwords, keys, tickets, or credential-bearing URLs are present.

**Pass:** all supported operations report their true state; successful ETL remains intact if Dremio fails; result manifest is mode-restricted and secret-free.

## Stop conditions

- Any missing/mismatched credential, unexpected effective user, unexpected broad permission, existing schema/count conflict, credential leak, mutation outside runtime input and intended target databases, or unexplained replacement/deletion.
- Derived image cannot build with the pinned versions or the JDBC artifact cannot load.
- Any operation would require resetting volumes, deleting current objects, broadening writer privileges, or using Dremio admin.

On a stop condition, preserve all state and record the observed failure plus smallest proposed remediation. Do not invoke `scripts/clean.sh`.

## Explicit exclusions

- No Airflow/Jenkins, JupyterHub, reader authorization demo, or automatic volume reset.
- The operator creates the Dremio Hive source manually; the workload never provisions or modifies the source configuration.
- No benchmark or security scan.

## Completion artifact

Record executed commands, redacted outcomes, and remaining gates in `aidlc-docs/current/construction/build-and-test/unit-3-build-and-test-summary.md`. Mark Unit 3 Build and Test complete only when its acceptance gates pass; otherwise retain partial status and remediation actions.

## Approval status

**Approved by the user on 2026-10-23; executed successfully.** Compose rendering, image builds, Kerberos writer identity, Hive/RustFS ETL, and JDBC view creation passed. Dremio 26.0.5 does not support `CREATE SPACE` through this SQL path, so the user created both Spaces manually. The Hive source required Dremio Kerberos configuration and RustFS S3A credentials. The first JDBC retry identified missing Hive Metastore server-side proxy authorization for Dremio; a restricted subnet and principal allowlist was added to `infra/hive/core-site.xml.in`. After restarting Hive, the JDBC phase created all 16 views as `write-service-account`. Per-user cross-engine allow/deny scenarios remain outside this plan's completed gates.
