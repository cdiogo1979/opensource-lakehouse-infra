# Tech Stack Decisions — Unit 3 SQL Bootstrap and Catalog Access

## Decision Summary

| Area | Decision | Rationale |
|---|---|---|
| Operating model | Operator-invoked local workflow; no scheduler or service | Matches the selected PoC scope; Airflow/Jenkins integration is deferred. |
| SQL engine and endpoint | Existing StarRocks OSS FE SQL endpoint in the Docker Compose network | Reuses Unit 2 runtime; FE/BE lifecycle is not owned by this unit. |
| Catalog | StarRocks Iceberg external catalog backed by the existing Hive Metastore | Keeps existing Hive metadata and RustFS Iceberg objects as the source of truth. |
| Credential storage | Existing ignored `.runtime/credentials/` convention with `0700` directories and `0600` password files | Consistent with project local credential handling; password contents are created only when absent and preserved on reruns. |
| Password generation | Reuse the project's existing local OpenSSL-based cryptographic random generation capability; exact invocation and SQL escaping are implementation details for later design | Avoids adding a password-generation dependency and aligns with existing bootstrap tooling. |
| Invocation coordination | Enforce one active mutating run per target FE/credential directory; choose the concrete local lock mechanism during NFR/Infrastructure Design | Prevents inspect/reconcile races without a new service. |
| Retry behavior | One attempt per SQL operation; operator corrects the cause and reruns | Selected manual operation with idempotent, fail-closed reconciliation. |
| Diagnostics | Redacted stdout/stderr only; no persistent audit or logging service | Fits the local PoC and avoids storing additional operational data. |
| Implementation boundary | Extend the existing repository workflow and supported Bash/Python/SQL tooling; do not add an orchestration framework or Compose service | Keeps bootstrap concerns local and leaves scheduled orchestration for later. |

## Constraints and Contracts

- Unit 3 consumes the Unit 1 StarRocks Kerberos and RustFS service credentials and the Unit 2 FE/BE runtime; it does not provision or rotate those identities.
- StarRocks SQL principals are distinct from the StarRocks service identities.
- Password files are individually protected and ignored; no credential value or secret-bearing response is written to tracked files or diagnostics.
- The external catalog points to existing HMS metadata and RustFS objects. Bootstrap is additive and does not delete or recreate shared state.
- A second concurrent bootstrap run exits without mutation.
- `write_service_account` may perform DML on existing tables only. The approved SQL permission matrix remains the authorization contract.
- Query/write compatibility and allow/deny outcomes are not implied by these technology choices; they require integrated verification.

## Deferred Decisions

- Exact bootstrap command and SQL client invocation, including whether SQL statements run from the host or an existing container.
- Concrete lock implementation and cleanup semantics after interruption.
- Exact StarRocks SQL statement ordering and supported privilege syntax for the pinned OSS release.
- Safe SQL handling/quoting for generated password values; secrets must not be exposed through command arguments or output.
- Compatibility with the selected StarRocks image, secured HMS, Iceberg features, and RustFS; verify in Build and Test before considering the unit complete.
