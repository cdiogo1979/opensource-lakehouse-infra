# Infrastructure Design — Unit 3 SQL Bootstrap and Catalog Access

## Purpose and Boundary

This design maps the approved Unit 3 bootstrap to the existing local StarRocks runtime. An operator invokes a host-side workflow which connects to the existing StarRocks FE SQL listener at `127.0.0.1:9030`. The workflow reconciles only the approved Iceberg catalog, native SQL accounts, and privileges. It does not alter Compose services, FE/BE lifecycle, shared Hive/RustFS/Spark services, or existing data.

The design is for the local PoC. Airflow/Jenkins integration, unattended scheduling, production HA, and a new logging or monitoring service are out of scope.

## Infrastructure Components

| Component | Placement | Responsibility |
|---|---|---|
| Operator entrypoint | Host project workflow, documented under `scripts/` | Runs preflight, obtains the lock, selects the canary/bootstrap operation, and presents redacted status. |
| MySQL-compatible CLI | Installed on operator host | Connects to FE at `127.0.0.1:9030`. Preflight checks availability and prints installation guidance if unavailable. No new Python driver or Compose service is introduced. |
| StarRocks FE | Existing `starrocks-fe` Compose service | Receives SQL over the existing loopback-published port and stores catalog/account/privilege metadata in its existing persistent volume. |
| Protected credential store | Ignored host `.runtime/credentials/` | Holds existing/generated credential files using owner-only directory and file modes. Existing values are preserved. |
| Bootstrap lock and canary marker | Ignored host `.runtime/state/` | Serializes mutating bootstrap operations and stores only non-secret canary metadata. |
| Existing platform dependencies | Existing Compose services | Hive Metastore, Kerberos, RustFS, and PostgreSQL remain unchanged and are reached by FE/BE using Unit 1/2 configuration. |

The repository does not currently declare a host MySQL-compatible client. Operators must install a compatible CLI as a host prerequisite. Its exact supported product/version and invocation flags are implementation choices for Code Generation, and must be documented and preflighted there.

## Operator Workflows

### Secret-Exposure Canary

The operator runs a dedicated canary command before the real bootstrap. The canary:

1. Confirms the expected FE is reachable, records its immutable image digest, and fingerprints the relevant FE logging configuration.
2. Acquires the same project-local mutation lock used by bootstrap.
3. Generates invocation-unique probe names and uses only deliberately non-secret marker values. It must not read or use real credential files.
4. Exercises the same client and SQL submission path intended for credential-bearing DDL, then inspects FE logs and available query, profile, audit, and client-diagnostic surfaces for marker exposure. It must fail if an expected inspection surface cannot be checked or the marker appears where a secret would be unsafe.
5. Removes only probe objects created by that invocation. It never clears or rewrites FE logs/history or deletes pre-existing SQL state.
6. Writes a restrictive, non-secret pass marker under ignored `.runtime/state/` only after all checks and cleanup succeed. The marker records the result, FE image digest, and relevant logging-configuration fingerprint; it contains no password, hash/verifier, RustFS key, Kerberos material, SQL response, or other secret.

An absent, malformed, failed, or stale marker blocks bootstrap before it submits real credential-bearing SQL. A changed FE image digest or relevant logging configuration invalidates the marker. Any uncertainty is a failure. Canary cleanup failure also blocks bootstrap and requires operator resolution; no unrelated object is removed.

The canary is a designed verification gate only. It has not been executed, and no claim is made that StarRocks 4.1.6 suppresses or redacts credential-bearing SQL. If the canary cannot establish the approved no-secret behavior for the exact pinned image/configuration, stop and seek an explicit requirements/design resolution before real credential-bearing DDL.

### Credential and Catalog Bootstrap

After the canary gate passes, the operator invokes the host bootstrap. It verifies FE readiness, CLI availability, credential file locations/modes, canary marker freshness, and lock ownership before SQL mutation. It reads protected values without printing them and ensures files are created only when absent, following the existing project convention. It reconciles only the approved catalog, identities, and privilege matrix. Conflicts, mismatched credentials, broader grants, or connectivity failures stop with redacted categories; completed additive changes remain for a safe rerun.

Credential-bearing SQL must be supplied through a private, non-persistent input path. It must never be included in command arguments, shell tracing, persistent SQL files, stdout/stderr, FE diagnostics, query history, or audit/profile records. A host-side client does not itself guarantee FE-side secrecy; the canary is therefore mandatory before any real secret-bearing statement. If the implementation cannot meet these constraints with the selected client, bootstrap fails closed.

## Lock and Local State

- Lock location: project-local ignored `.runtime/state/`, owner-only and associated with this project/FE endpoint.
- The lock is acquired before creating credential files or submitting mutation SQL and held through final verification/cleanup.
- A second invocation exits as busy without mutation. Ambiguous stale lock state fails closed and requires operator resolution; automatic stale-lock breaking is not permitted.
- State marker and lock files contain only operational metadata. Neither is an audit log or a durable report store.
- Temporary SQL input, if required by the chosen CLI, must be private, short-lived, excluded from tracked paths, removed on normal/error exit, and never contain reusable diagnostic output. The implementation must demonstrate that it does not persist after completion; if this cannot be ensured, choose another input mechanism.

## Network and Runtime Contracts

- Host-to-FE SQL: `127.0.0.1:9030`, using the existing Compose port mapping.
- No new listener, service, volume, image, or network is added.
- FE-to-HMS/RustFS continues using the existing StarRocks service identities and Compose endpoints. SQL users are StarRocks authorization principals and do not impersonate Kerberos/RustFS identities.
- Compose FE/BE lifecycle and persistent volumes remain owned by Unit 2. The bootstrap neither starts/stops services nor changes volumes.

## Failure and Preservation Behavior

| Condition | Required behavior |
|---|---|
| Host SQL CLI missing | Stop before mutation and give installation guidance. |
| FE unavailable | Stop before mutation with a redacted readiness category. |
| Lock busy or ambiguous | Stop without credential or SQL mutation. |
| Canary absent, failed, stale, or unable to inspect a required surface | Stop before real credential-bearing SQL. |
| Credential or catalog/grant drift | Preserve existing state and stop with a redacted conflict category. |
| SQL/dependency operation fails | Report safe operation/category, preserve completed additive changes, do not auto-retry or rollback. |
| Canary cleanup fails | Do not write a passing marker; preserve logs and unrelated state; require operator cleanup/resolution. |

No routine operation drops/recreates users, catalogs, grants, databases, tables, RustFS objects, or platform services. No automatic password rotation, broad grant revocation, volume deletion, or log cleanup is allowed.

## Security Controls

- Runtime credentials remain in ignored `.runtime/credentials/`; directory mode `0700`, file mode `0600`.
- Use no secrets in Compose environment values, tracked configuration, process arguments, shell tracing, persistent SQL files, or console output.
- Redact SQL client errors and server responses before printing. Do not return raw SQL or secret-bearing server response bodies.
- Do not assume FE logs/history redact SQL. Real credential-bearing DDL remains gated until demonstrated safe against the exact image and logging configuration.
- The canary result marker is non-secret and scoped to exact image/config fingerprints.

## Traceability

This design implements the approved Unit 3 Functional Design, NFR Requirements NFR-1 through NFR-5, NFR Design single-run/fail-closed patterns, and Infrastructure Design answers Q1 A and Q2 A. It preserves the existing Unit 2 `starrocks-fe` endpoint and Unit 1 service-identity boundary. Runtime behavior remains unverified until the dedicated canary and later Build and Test are performed.
