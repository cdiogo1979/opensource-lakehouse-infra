# Unit 3 Spark Runtime and Sample ETL — NFR Design Patterns

## Scope

These patterns translate approved Unit 3 NFRs into logical implementation guidance. They do not prescribe concrete Compose syntax, image tags, credential filenames, JDBC driver setup, healthcheck commands, or retry durations. They do not certify Hive writer authorization, Spark keytab login, or Dremio Community JDBC permissions.

## Readiness and Dependency Gating

- Keep generation, Hive/RustFS ETL, and Dremio JDBC exposure as distinct sequential steps in one operator-triggered run.
- Before ETL writes, require the Spark runtime, KDC, Hive Metastore, RustFS/bucket, writer credential references, and all eight input files for the selected scale factor to be ready.
- Distinguish service health from capability: a healthy Metastore does not prove writer DDL/storage access; successful Dremio login does not prove Space/view creation permission.
- Gate the JDBC phase separately on valid ETL results and Dremio readiness. Skip JDBC setup when ETL validation fails and record `not_attempted`.
- Do not add scheduler, queue, persistent worker, monitoring service, or HA components.

## Component Separation and Execution Order

1. **Generator adapter:** produces the existing TPCH `.tbl` inputs at scale factor 1 and reports the source file set. It has no Hive, RustFS, or Dremio credentials.
2. **ETL adapter:** obtains the writer's short-lived Kerberos ticket, configures Spark for the Hive Iceberg catalog and RustFS, creates/validates database/table state, and records schema/count results.
3. **Dremio JDBC adapter:** runs only after ETL validation, authenticates as the non-admin writer, and ensures matching Spaces/views without replacing conflicting objects.
4. **Run coordinator/report:** sequences adapters once, correlates their non-secret results with a run ID, and computes `complete`, `partial`, or `failed` overall state.

The steps run sequentially on the existing local Compose host. There is no concurrent writer or distributed scheduling requirement.

## Credential Isolation and Ticket Lifecycle

- Expose only the writer keytab and RustFS credentials to the ETL workload, and only the writer's Dremio password to the JDBC step. Keep input files read-only where supported.
- Acquire a short-lived ticket into a restricted temporary cache before Spark starts and provide a cache reference, not the ticket contents or password, to the process.
- Use the protected pre-authenticated cache approach for the verified local Spark mode. Keep Spark standalone keytab login as a separate compatibility gate until tested in the actual execution mode.
- Remove temporary ticket-cache material on normal completion, error, interruption, and container shutdown. Do not copy it into persistent data/report locations.
- Do not expose RustFS root, PostgreSQL metastore, or component-admin credentials to ETL/JDBC adapters.

## Safe Ensure and Validation Pattern

- Model each database/table/Space/view as `missing`, `created`, `already_valid`, `conflict`, or `failed`.
- Create only missing objects. Validate matching existing Hive tables by schema and expected row count; validate Dremio views against their expected Hive target.
- Stop on schema/count/target conflict and report it. Never use `createOrReplace`, drop, truncate, append, or automatic repair for an existing object.
- Retry only bounded readiness/availability operations and known-safe idempotent checks. Authentication, authorization, and conflict failures are not transient retries.
- Preserve successful earlier objects for a safe rerun; no automatic rollback or cleanup of databases, Iceberg objects, or Dremio views.

## Partial Failure and Reporting

- Treat Hive/RustFS ETL and Dremio JDBC exposure as separate result domains.
- If ETL fails, stop further data writes and skip JDBC setup. Report `failed` plus per-object state.
- If ETL passes but JDBC operations are denied, preserve the data, mark ETL `complete`, JDBC `failed`, and overall run `partial`. Never retry as admin or elevate the writer.
- Emit a non-secret manifest with run ID, effective identity, scale factor, source/table/database identifiers, expected/observed schemas and counts, RustFS prefix, and Dremio object states.
- Diagnostics include component, operation, status code/SQLState where available, and safe context; redact passwords, keys, keytab/ticket contents, and secret-bearing URLs.
- Operator command output and container logs are sufficient. No report database or monitoring stack is added.

## Local Operation and Feasibility Boundary

- Keep service traffic on the private Compose network and published ports loopback-only.
- Preserve approved component versions until verified evidence justifies a reviewed change.
- Spark keytab login, writer Hive/RustFS permissions, and Dremio non-admin Space/view creation remain explicit gates. Report the smallest proposed adjustment if a pinned component cannot satisfy the approved boundary.
- These patterns support a local PoC only; they do not claim production-grade scheduling, secret management, availability, or authorization enforcement.

## NFR Traceability

| Design concern | Approved requirements |
|---|---|
| Fixed scale, one host, no throughput SLA | U3-NFR-01 to U3-NFR-03 |
| Readiness, durable data, retry, and partial results | U3-NFR-04 to U3-NFR-10 |
| Writer identity and credential isolation | U3-NFR-11 to U3-NFR-15 |
| Version compatibility and capability gates | U3-NFR-16 to U3-NFR-19 |
| Manifest, outcome states, and redacted diagnostics | U3-NFR-20 to U3-NFR-23 |
| Component separation and one-shot operation | U3-NFR-24 to U3-NFR-26 |

## Extension Applicability

- Security Baseline: disabled; credential isolation, redaction, and least privilege remain mandatory.
- Property-Based Testing: partial; reassess if implementation adds pure manifest/path transformations.
- Resiliency Baseline: disabled; the approved safe rerun and partial-failure rules still apply.
