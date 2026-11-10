# Unit 3 Infrastructure Design Plan — SQL Bootstrap and Catalog Access

## Unit Context

Map the approved Unit 3 SQL bootstrap onto the existing StarRocks 4.1.6 Compose runtime without changing the shared lakehouse services or data. The bootstrap is host-side and connects to the FE through the existing loopback SQL endpoint (`127.0.0.1:9030`). It must use the protected local credentials, enforce a single active run, and refuse credential-bearing DDL until the secret-exposure gate passes.

Approved infrastructure constraints:

- Reuse the existing `starrocks-fe` service, StarRocks 4.1.6 image, Compose network, and loopback-only SQL endpoint; do not add another StarRocks service or alter FE/BE lifecycle.
- Keep bootstrap assets under `infra/starrocks/` with a documented host entrypoint under the project operator workflow; do not put SQL bootstrap secrets into Compose environment values, tracked config, or command-line arguments.
- Use the existing ignored `.runtime/credentials/` files and the approved `0700` directory / `0600` file convention. Do not replace existing values.
- Serialize mutations using an owner-only host lock under ignored `.runtime/` state. Ambiguous lock state fails closed.
- Verify credential-bearing SQL behavior using only non-secret canary values against the pinned FE image before the actual bootstrap sends secrets. Store only non-secret verification metadata if the selected approach requires a marker.
- No new monitoring, logging, scheduler, persistent helper service, or Airflow/Jenkins integration.
- Do not edit Compose runtime configuration, build images, start/stop services, modify data, or run tests during this Infrastructure Design planning stage.

## Documentation and Workspace Findings

- The existing Compose configuration publishes FE SQL at `127.0.0.1:9030`; it does not expose the port to the LAN.
- The FE container currently invokes the bundled `mysql` CLI for health checks, but the approved Unit 3 execution boundary is host-side. The repository does not currently declare a host MySQL client or Python MySQL driver dependency; this needs an explicit dependency decision.
- StarRocks 4.1.6 supports catalog/user DDL that accepts credential-bearing values, and StarRocks logs can include SQL text. See the official [CREATE USER](https://docs.starrocks.io/docs/sql-reference/sql-statements/account-management/CREATE_USER/), [Iceberg catalog](https://docs.starrocks.io/docs/data_source/catalog/iceberg/), and [logging](https://docs.starrocks.io/docs/administration/management/logs/) documentation. The exact log behavior must be checked against the pinned image.
- The existing project credential generator uses OpenSSL random bytes, a restrictive umask, a temporary file, and an atomic no-overwrite move in `scripts/bootstrap-local.sh`; a Unit 3 implementation should reuse the local convention without changing existing values.

## Infrastructure Design Tasks

- [x] **Step 1 — Map the approved NFR Design:** Reuse the existing FE SQL port and host-side boundary; no new long-running Compose component is needed.
- [x] **Step 2 — Identify infrastructure components:** Host bootstrap entrypoint, SQL client dependency, protected credential store, project lock, canary verification gate, and existing FE endpoint.
- [x] **Step 3 — Identify remaining choices:** Prepare questions for host SQL client/dependency and the lifecycle of the non-secret canary verification result.
- [x] **Step 4 — Resolve questions:** Q1 A requires a host MySQL-compatible CLI and safe non-argument input; Q2 A requires a separate canary command and a non-secret marker bound to the FE image and relevant logging configuration. Both preserve the approved no-secret-in-diagnostics rule.
- [x] **Step 5 — Generate infrastructure design artifacts:** Created `infrastructure-design.md` and `deployment-architecture.md` under `aidlc-docs/current/construction/unit-3-starrocks-sql-bootstrap/infrastructure-design/`.
- [x] **Step 6 — Validate and present:** Traced the design to the approved Functional Design, NFR Requirements, NFR Design, and existing Compose contracts.
- [x] **Approval gate:** User approved Infrastructure Design and continued on 2026-10-24; Code Generation planning is active.

## Questions

Fill each `[Answer]:` line with an option letter. If an option would weaken an approved security requirement, do not select it; describe the requested requirement change explicitly instead.

### Question 1 — Host SQL client and dependency

The bootstrap must run on the host and connect to `127.0.0.1:9030`. Which SQL client contract should Infrastructure Design use?

A) Require the MySQL-compatible CLI to be installed on the host; preflight checks for it and exits with installation guidance if missing. Keep passwords out of process arguments and provide any sensitive SQL input without creating persistent SQL files.

B) Add a pinned Python MySQL-protocol driver to the project's host-side bootstrap environment; connect from an in-process client and read passwords directly from protected files. No new Compose service is added.

C) Other (describe below).

[Answer]:A

### Question 2 — Canary verification gate lifecycle

How should non-secret canary verification of FE log/query-history behavior run before credential-bearing DDL?

A) Run a dedicated operator command against the pinned FE image and current FE logging configuration. It creates only uniquely named disposable probe state with non-secret marker values, inspects relevant logs/history, cleans up only its own probe objects, and records a non-secret pass marker bound to the FE image digest and relevant logging-configuration fingerprint. The real bootstrap refuses to proceed if the marker is absent or stale.

B) Run the canary probe automatically on every bootstrap invocation before any credential-bearing DDL; do not retain a pass marker. The bootstrap proceeds only when the current probe passes.

C) Other (describe below).

[Answer]:A

### Answer Review and Design Status

- **Q1 A:** The operator host must provide a MySQL-protocol-compatible CLI. Bootstrap preflight fails with installation guidance when missing. Sensitive SQL is supplied through a private, non-persistent input path; credentials must not appear in argv, shell tracing, persistent SQL files, or console output.
- **Q2 A:** A separate operator-run canary checks the pinned FE image and current relevant logging configuration. It uses unique disposable names and non-secret marker values, inspects FE logs and available query/profile/history surfaces, and cleans up only its own objects. Its state marker contains only a result, image digest, and fingerprint of relevant logging configuration. Bootstrap fails closed if the marker is missing, invalid, stale, or mismatched.
- **Artifacts ready:** `infrastructure-design/infrastructure-design.md` and `infrastructure-design/deployment-architecture.md`.
- **Approval:** User approved the Infrastructure Design on 2026-10-24. The canary has not been run; no secret-safety result is claimed.

## Fixed Security and Preservation Constraints

- The canary marker, if selected, contains no password, hash/verifier, RustFS key, ticket, or other secret. It is not an audit log and is stored only under ignored `.runtime/` state.
- Canary values are intentionally non-secret, unique markers. A probe failure or unexpected marker handling blocks real credential-bearing DDL.
- Probe cleanup may remove only objects created by that probe invocation. Existing users, catalogs, roles, grants, databases, tables, logs, and data are preserved.
- The host SQL client must not expose credentials in process arguments, shell tracing, persistent temporary SQL files, stdout/stderr, FE logs, or query/audit history.
- Bootstrap operations remain one-shot per SQL statement, additive, and fail-closed. The host lock is acquired before credential creation or SQL mutation.
- No implementation, Compose edits, SQL execution, canary execution, tests, image builds, or service/data operations occur in this planning stage.
