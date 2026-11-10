# NFR Design Patterns — Unit 1 Identity Provisioning

## Design Scope

This design applies to the operator-invoked StarRocks identity provisioning workflow. It maps approved Unit 1 NFRs to patterns within the existing Bash/Python CLI and provider APIs. It adds no service, daemon, queue, monitoring system, or orchestration framework.

## Provider Outcome Aggregation

Use a sequential, independent-branch pattern in the existing orchestration entry point:

1. Run the Kerberos provisioning/validation branch in a conditional that captures its exit status without allowing shell `errexit` behavior to skip the next branch.
2. Run the RustFS provisioning/validation branch the same way, regardless of the Kerberos result.
3. Record a safe provider status for each branch.
4. Return aggregate success only when both provider branches succeed; otherwise return nonzero after both have been attempted.

Each branch is invoked once per command run. Do not add an automatic retry loop, delay/backoff, rollback, circuit breaker, or persistent recovery queue. Successful resources remain in place. A later operator invocation re-inspects and validates existing resources, then resumes idempotently.

## Safe Diagnostics Pattern

Use an allowlist for all operator-visible provider failures:

- Provider name and safe identity/resource name.
- Outcome category such as `created`, `already-present`, `validated`, `authentication-failed`, `permission-denied`, `resource-conflict`, `unavailable`, or `unknown-error`.
- Numeric HTTP status or a Kerberos/tool exit category when safe and available.
- A short action hint: retry after service recovery, inspect configuration, or reconcile existing state manually.

Discard raw provider response bodies and raw command output. Adapters may extract only explicitly approved fields such as numeric HTTP status and known error codes; never display response messages, signed headers, tokens, secret values, or keytab contents. Do not rely on secret-string replacement as the primary redaction boundary. Diagnostics are concise console output, with per-provider statuses followed by the aggregate result.

## Credential Filesystem Guard

Before using StarRocks credential references, validate that paths are regular files/directories at the expected locations and that the expected operator/runtime owner can access them. Ensure credential directories have mode `0700` and secret/keytab files have mode `0600`:

- Create new directories/files with a restrictive umask and explicit modes.
- Correct existing permission bits with `chmod` without reading, replacing, rotating, or rewriting credential contents.
- Do not silently change ownership to another account. If the provisioner cannot establish the expected owner or required mode, fail closed with a safe diagnostic instructing the operator to reconcile ownership/permissions.
- Keep credentials in the existing ignored `.runtime/credentials/` paths and do not copy them into logs, generated configuration, or tracked files.

This pattern implements the selected permission correction option while preserving the approved no-implicit-rotation rule.

## Idempotent Recovery and Failure Preservation

Treat each provider as an independently reported state transition. If one provider fails, keep resources successfully created or validated by the other. Do not delete existing resources to simulate rollback. Report the failed provider category and safe next action; a new invocation is the recovery mechanism.

Existing credential or policy drift is a reconciliation-required outcome. Do not overwrite a mismatched credential or broaden/rewrite an existing policy automatically.

## Scale and Performance

Keep the provider workflow sequential and bounded to the fixed identity additions. The unit has no hard completion-time target, so no parallel worker, cache, batching layer, or scaling subsystem is justified. Retain existing provider request timeouts and validation checks.

## NFR Traceability

| Requirement | Design pattern |
|---|---|
| NFR-1.1, NFR-1.2 | Operator-triggered invocation and idempotent subsequent rerun |
| NFR-1.3, NFR-1.4, NFR-4.2 | Independent provider branches and aggregate status after both attempts |
| NFR-2.1, NFR-2.2 | Sequential bounded workflow; no scaling/performance subsystem |
| NFR-3.1, NFR-3.2 | Filesystem guard and ignored runtime credential paths |
| NFR-3.3, NFR-3.4 | Allowlisted diagnostics; raw bodies and command output discarded |
| NFR-3.5, NFR-3.6, NFR-4.4 | No implicit rotation; fail closed on drift; retain scoped policy |
| NFR-4.1, NFR-4.3 | Idempotent rerun; one attempt per provider per invocation |
| NFR-4.5, NFR-5.1, NFR-5.2, NFR-5.3, NFR-5.4 | Existing CLI/provider stack and documented operator guidance; no UI/monitoring |

## Deferred Design

StarRocks runtime ticket renewal, FE/BE resilience, query performance, SQL grants, and catalog/storage integration patterns remain with Units 2 and 3.
