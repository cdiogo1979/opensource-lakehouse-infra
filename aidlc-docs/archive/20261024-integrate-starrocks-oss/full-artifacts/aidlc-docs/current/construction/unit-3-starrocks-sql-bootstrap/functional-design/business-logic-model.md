# Unit 3 Business Logic Model — SQL Bootstrap and Catalog Access

## Purpose

Define how the operator-facing bootstrap establishes the StarRocks Iceberg catalog and SQL access for the approved identities. StarRocks uses its dedicated Kerberos and RustFS service identities for catalog and object access; SQL users are separate credentials and are authorized by StarRocks.

## Actors and Responsibilities

- **Platform operator:** Starts the bootstrap after Unit 2 reports FE/BE ready, keeps the protected credential directory available, and resolves fail-closed diagnostics.
- **SQL bootstrap:** Validates prerequisites, loads or creates protected SQL password files, inspects StarRocks state, and reconciles only the approved catalog and access configuration.
- **StarRocks FE/BE:** Provides the SQL endpoint, Iceberg external catalog, and execution for reads/writes.
- **Hive Metastore and RustFS:** Provide Iceberg metadata and table objects through StarRocks's dedicated service identities.
- **SQL principals:** `admin`, `user_a`, `user_b`, and `write_service_account` authenticate to StarRocks and receive the approved SQL privileges.

## Bootstrap Lifecycle

1. **Preflight:** Confirm FE/BE readiness, the configured SQL endpoint, the Unit 1 Kerberos and RustFS credential references, and the expected protected credential directory. Do not print credential values.
2. **Credential preparation:** Ensure a separate protected password file exists for built-in `root`, `admin`, `user_a`, `user_b`, and `write_service_account`. Generate a value only when its file is absent. Existing files remain unchanged.
3. **Root account establishment:** On the initial bootstrap, set the built-in `root` password from its protected file. On reruns, authenticate with that stored root credential. If the server's current credential cannot be reconciled with the file, stop without changing account passwords or resetting StarRocks state.
4. **Inspect target state:** Inspect the Iceberg catalog, target users/roles, and effective grants. Determine whether the state is absent, already compliant, safely missing an intended item, or conflicting/broader than the approved state.
5. **Catalog reconciliation:** Create the StarRocks Iceberg external catalog if absent, using the existing Hive Metastore and RustFS configuration. If present, preserve it when compliant; add only known-safe missing settings. A conflicting catalog definition fails with a redacted diagnostic.
6. **Principal and privilege reconciliation:** Create missing SQL principals and apply the approved database-level permissions. Preserve unrelated grants and objects. Existing broader or conflicting target access fails closed; do not silently revoke permissions or alter unrelated state.
7. **Credential consistency check:** Authenticate each target SQL identity using its protected password file. If an existing account does not match its file, report the identity and remediation category without revealing the password, then stop. Do not reset the password or replace the file.
8. **Complete:** Report success only when the catalog and target access matrix are in the intended state and SQL authentication checks pass. Report only safe status and identity names.

## Access Matrix

| SQL identity | `databaseA` | `databaseB` | Administration |
|---|---|---|---|
| `user_a` | Read | Denied | None |
| `user_b` | Read | Read | None |
| `write_service_account` | Read and DML write to existing tables | Read and DML write to existing tables | None |
| `admin` | Full StarRocks access | Full StarRocks access | Full StarRocks administration |

The writer's selected scope excludes database/table creation, alteration, and drop. The existing ETL identity used in Kerberos/RustFS remains `write-service-account`; only the StarRocks SQL name uses underscores where needed.

## Failure Handling

- **FE/BE unavailable or required service credential missing:** Stop before SQL mutations; keep all files and data intact.
- **Missing password file:** Generate and persist a strong value using the protected local credential convention; never emit the value.
- **Existing SQL account/password mismatch:** Fail closed. Preserve both account state and credential file so an operator can resolve the drift explicitly.
- **Existing broader/conflicting grant or catalog:** Fail closed with a redacted diagnostic. Do not attempt broad cleanup or revoke unrelated permissions.
- **Partial safe reconciliation failure:** Preserve completed non-destructive changes and report which named operation failed, without secrets. Rerun is safe after the cause is resolved.
- **HMS/RustFS connectivity failure:** Do not classify it as an authorization failure. Report dependency connectivity separately from SQL grant checks.

## Scope and Traceability

- **FR-2 / FR-3:** Register the existing Hive-backed Iceberg catalog and support querying/writing existing Iceberg tables.
- **FR-4 / FR-5:** Use dedicated StarRocks RustFS and Kerberos service identities; these are not SQL principals.
- **FR-6:** Create SQL identities and enforce the approved database access matrix.
- **FR-7 / NFR-1:** Preserve existing services/data and protect credentials from tracked files and output.
- **NFR-2:** Safe reruns preserve existing password files, unrelated grants, and catalog/data objects.
- **US-01 through US-04:** Query, writer access, SQL authorization, and dedicated service credentials.

Build and Test must verify the integration and all allow/deny cases. This model defines behavior; it does not claim the bootstrap has been implemented or verified.
