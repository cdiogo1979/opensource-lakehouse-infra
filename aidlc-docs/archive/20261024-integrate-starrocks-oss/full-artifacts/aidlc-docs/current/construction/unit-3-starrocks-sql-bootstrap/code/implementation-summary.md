# Implementation Summary — Unit 3 StarRocks SQL Bootstrap

## Generated Paths

- `scripts/verify-starrocks-sql-secret-safety.sh` — operator entrypoint for the standalone non-secret FE diagnostics canary.
- `scripts/bootstrap-starrocks-sql.sh` — operator entrypoint for the fail-closed host bootstrap.
- `infra/starrocks/sql-bootstrap/runner.py` — shared host-side implementation for lock/preflight, MySQL CLI submission, image/config marker validation, canary scanning, and additive SQL reconciliation.
- `README.md` — host prerequisite, canary-first run order, credential handling, access matrix, rerun, and conflict guidance.

Build and Test added the minimal StarRocks Hive Kerberos configs and corrected FE/BE startup/reconciliation behavior. No credential values, sample table contents, or shared data volumes were changed.

## Behavior Implemented

- Requires the host `mysql` CLI (or a non-secret `MYSQL_CLI` executable path override) and uses the existing loopback FE SQL port.
- Serializes canary/bootstrap operations using an exclusive owner-only lock under ignored `.runtime/state/`. An existing lock is treated as active or ambiguous and blocks. Normal exit removes the lock; interruption leaves it for operator resolution.
- Passes SQL to the CLI through stdin. For password authentication, creates a `0600` temporary MySQL option file in the owner-only ignored state directory and unlinks it immediately after the client exits. Does not place password material in process arguments or print raw SQL/client/server output.
- Canary uses only generated, deliberately non-secret values; exercises CREATE/ALTER USER and verifies authentication before and after alteration through protected temporary client option files. It does not retrieve password verifiers. It also exercises credential-bearing Iceberg catalog DDL, scans recent FE container output, configured FE log directories, and `SHOW PROFILELIST` output, and drops only probe objects whose create operations returned success. An incomplete check or cleanup does not produce a marker.
- Successful canary marker stores only schema/result, effective image ID, SHA-256 fingerprint of FE `fe.conf` plus dynamic `ADMIN SHOW FRONTEND CONFIG LIKE '%log%'` output, and verification time. Bootstrap blocks if the marker is missing, malformed, not mode `0600`, or bound to different image/config state. StarRocks documents that the FE config command masks configured passwords, secret keys, and tokens in its value output.
- Bootstrap preserves existing credential files; creates missing passwords as 256-bit random hex; protects directories/files; checks existing identities authenticate; and refuses credential drift, catalog conflict, or broad/unrecognized grants.
- Registers or verifies the `iceberg` external Iceberg catalog using existing Hive Metastore and RustFS endpoints and the dedicated Unit 1 RustFS identity. It does not create or alter Hive databases/tables.
- Existing catalog reconciliation parses the first `SHOW CATALOGS` column and accounts for StarRocks masking catalog credentials in `SHOW CREATE CATALOG`; it validates static properties and a read-only query of an existing sample table without printing secret values.
- SQL calls use separate MySQL connections; operations that depend on `SET CATALOG` now keep that statement and its following grants in the same client session. External catalog table listing uses fully qualified names.
- `ensure-backend` registers/verifies the BE from the host with the protected SQL credential. FE health uses `/api/health`, avoiding an unauthenticated SQL healthcheck after root is secured.
- Creates/reuses native SQL identities and applies the approved access matrix. Writer SELECT is database scoped while INSERT/UPDATE/DELETE are granted per currently listed table; an existing writer DML grant outside that set fails closed. Each target identity is authenticated before reporting success.
- Least-privilege validation permits StarRocks' built-in `public` role grant on `information_schema` only; other `public` grants fail closed because they could widen access beyond the approved Iceberg catalog matrix.

## Security and Feasibility Limits

- The no-secret-in-FE-diagnostics requirement remains limited to the current FE image/configuration and scanned surfaces. The canary passed during Build and Test before credential-bearing DDL.
- The canary scans FE container output, every readable file in the configured audit/profile log directories (and the standard FE log directory), and returned cached query profile statements. It fails when these surfaces cannot be inspected. Any additional query/audit/history surface exposed by the pinned runtime must be included in Build and Test review; if coverage is incomplete, treat the canary as not passed.
- A matching canary marker does not prove that credentials are absent from every possible system surface. It is limited to the exact fingerprinted FE image/configuration and inspected surfaces.
- A killed process may leave the lock and a temporary client-input file. The lock intentionally blocks reruns until manually resolved; after lock resolution, the next run removes only the helper's named temporary files.
- Positive writer DML/readback and Spark interoperability remain unverified. The tested read/deny matrix and catalog query passed; no sample-table rows were changed.

Configuration inspection follows the StarRocks [`ADMIN SHOW FRONTEND CONFIG`](https://docs.starrocks.io/docs/sql-reference/sql-statements/cluster-management/config_vars/ADMIN_SHOW_CONFIG/) output contract. Catalog and account SQL forms follow the StarRocks [Iceberg catalog](https://docs.starrocks.io/docs/data_source/catalog/iceberg/), [CREATE USER](https://docs.starrocks.io/docs/sql-reference/sql-statements/account-management/CREATE_USER/), and [GRANT](https://docs.starrocks.io/docs/sql-reference/sql-statements/account-management/GRANT/) references; pinned-image compatibility still requires Build and Test.

## Traceability

Implements the approved Unit 3 Functional Design, NFR Requirements, NFR Design, Infrastructure Design answers Q1 A/Q2 A, and Code Generation Plan. Trace points include host-side execution, loopback SQL, create-on-absence credentials, single-run lock, redacted failures, canary marker freshness, non-destructive reconciliation, and the `user_a` / `user_b` / `write_service_account` / `admin` access matrix.

## Verification Status

Build and Test verified the secret-safety canary, catalog discovery and sample reads, identity authentication, the approved read/deny matrix, zero-row write denial for readers, service health, and local source/config syntax. Positive writer DML/readback, Spark interoperability, persistence across a controlled restart, and notebook workspace preservation remain open.
