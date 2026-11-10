# Unit 3 Code Generation Plan — StarRocks SQL Bootstrap and Catalog Access

## Unit Context

- **Unit:** Unit 3 — SQL Bootstrap and Catalog Access.
- **Stories:** US-01 through US-04, as scoped in the approved unit design.
- **Requirements:** FR-2, FR-3, FR-4, FR-5, FR-6, FR-7 and Unit 3 NFR-1 through NFR-5.
- **Workspace:** Brownfield Compose project at `/Users/carlosdiogo/code_repo/hive-dremio-rustfs`.
- **Dependencies:** Approved Unit 1 StarRocks Kerberos/RustFS identities, Unit 2 StarRocks FE/BE runtime, existing Hive Iceberg databases/tables, and operator-provided host MySQL-compatible CLI.
- **Approved design:** `aidlc-docs/current/construction/unit-3-starrocks-sql-bootstrap/{functional-design,nfr-requirements,nfr-design,infrastructure-design}/`.
- **Completion boundary:** Generate the host-side canary and bootstrap workflows plus operator documentation. No Compose/runtime changes or data-plane changes are included. Code generation does not constitute proof that credential-bearing SQL is safe; the real bootstrap must refuse to submit such SQL without a passing, current canary marker.

## Approved Contracts

- Connect from the host to existing FE SQL at `127.0.0.1:9030` using an installed MySQL-compatible CLI. Preflight fails with installation guidance if unavailable; do not add a Python SQL driver or Compose service.
- Preserve `.runtime/credentials/` values; generate only missing credentials under the existing `0700` directory / `0600` file convention and never print them.
- Keep the bootstrap and canary host-side. Keep SQL bootstrap implementation assets under `infra/starrocks/` and operator entrypoints under `scripts/`.
- Serialize mutating workflows with an owner-only project lock under ignored `.runtime/state/`; overlapping or ambiguous stale-lock state fails closed.
- A separate canary uses only unique disposable probe objects and deliberately non-secret marker values. It inspects the same relevant FE log/history surfaces and SQL path, cleans only its own objects, and records a non-secret marker bound to the effective FE image digest and relevant logging-configuration fingerprint.
- Bootstrap checks for a valid current marker before sending any real credential-bearing SQL. Missing, stale, malformed, failed, or uncertain canary result blocks submission.
- No secrets in process arguments, shell tracing, persistent SQL files, stdout/stderr, FE logs, query history, audit/profile records, tracked files, or Compose environment values.
- Never clear logs/history or delete pre-existing users, catalogs, grants, databases, tables, objects, or service state. No implicit password reset/rotation, automatic retries, rollback, or broad grant cleanup.
- No Compose changes, image builds, tests, canary execution, SQL execution, or service/data operations during Code Generation unless separately approved in a later Build and Test stage.

## Exact Application Files

1. `infra/starrocks/sql-bootstrap/` — implement the host-side bootstrap and canary helpers using a narrow structure (for example, shell entrypoints with reusable host helper code). Keep sensitive SQL off process arguments and persistent SQL files. Use defensive quoting, disabled tracing, redacted client failures, and cleanup traps. Exact internal filenames may be selected during generation without changing the approved interface.
2. `scripts/verify-starrocks-sql-secret-safety.sh` — operator entrypoint for the standalone non-secret canary; validates prerequisites, locks the FE/project state, probes relevant log/history surfaces, removes only uniquely named probe objects, and writes the protected non-secret image/config-bound marker only after complete success.
3. `scripts/bootstrap-starrocks-sql.sh` — operator entrypoint for host preflight and SQL reconciliation; requires the current successful canary marker before any credential-bearing statement, reuses protected credentials, preserves existing SQL state, serializes mutation, authenticates all target identities, and reports redacted results.
4. `README.md` — document host CLI prerequisite/install guidance, StarRocks readiness, canary-first workflow, bootstrap invocation, credentials and modes, access matrix, safe rerun/conflict handling, and the fact that secrets remain blocked if canary cannot prove safety.
5. `aidlc-docs/current/construction/unit-3-starrocks-sql-bootstrap/code/implementation-summary.md` — record generated files, flow, secret boundaries, canary/marker contract, requirements traceability, decisions deferred to Build and Test, and any infeasibility found. Markdown documentation only under `aidlc-docs/`.

No changes to `docker-compose.yml`, StarRocks FE/BE configuration, Unit 1 provisioning, existing credential files, or shared service/data state are permitted in this unit's Code Generation.

## Generation Steps

- [x] **Step 1 — Implement safe local coordination and preflight:** Added host CLI/FE/config checks, protected project paths, exclusive lock, and redacted failures before SQL mutation.
- [x] **Step 2 — Implement the non-secret canary:** Added unique non-secret user/catalog probes, password-authentication checks before and after alteration, client/profile/FE log scans, own-object cleanup, and a non-secret marker bound to effective FE image plus static/dynamic logging configuration.
- [x] **Step 3 — Implement fail-closed bootstrap gate:** Marker integrity and freshness are required before credential-bearing SQL. Missing, mismatched, malformed, or uninspectable state aborts without submitting real credentials.
- [x] **Step 4 — Implement additive catalog/account/grant reconciliation:** Added approved Hive-backed Iceberg catalog settings, create-on-absence SQL identities, scope checks, access grants, and authentication checks. Conflicts fail closed; no reset/revoke/rollback path was added.
- [x] **Step 5 — Document operator usage and implementation summary:** Updated README and added the Unit 3 implementation summary with limitations and Build and Test items.
- [x] **Step 6 — Review conformance and security boundaries:** Reviewed generated files against approved designs. No secrets, Compose/runtime edits, tests, canary execution, SQL, builds, or service/data operations were introduced or performed.
- [x] **Approval gate:** User approved the Code Generation plan on 2026-10-24 before implementation.

## Verification Boundary

Code Generation is complete under the approved plan. No tests, builds, Compose commands, canary probes, SQL, or service/data operations were run. Build and Test must later verify CLI compatibility, actual FE log/query-history behavior, marker invalidation, lock behavior, protected file modes, account/grant outcomes, and catalog connectivity. The real bootstrap remains fail-closed until the canary provides complete evidence for the effective pinned FE image and current relevant logging configuration. User review is required before Build and Test.

## Scope Exclusions

- Do not change Compose services, FE/BE lifecycle, image configuration, ports, volumes, or existing StarRocks data.
- Do not modify Unit 1 Kerberos/RustFS identity provisioning or Unit 2 StarRocks runtime.
- Do not modify the sibling Airflow/Jenkins project or add orchestration integration.
- Do not clear logs/history, drop pre-existing SQL objects, rotate credentials, revoke unrelated grants, retry automatically, or perform rollback.
- Do not claim secret-safe SQL behavior until the canary is implemented and passed against the exact runtime in Build and Test.
