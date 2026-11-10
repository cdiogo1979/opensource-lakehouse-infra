# NFR Requirements — Unit 1 Identity Provisioning

## Scope

These requirements apply to provisioning the dedicated StarRocks Kerberos and RustFS identities through the existing local identity-provisioning workflow. They refine the approved Unit 1 functional design. StarRocks runtime availability, ticket renewal during service operation, SQL authorization, query performance, and Iceberg write behavior remain owned by later units.

## Availability and Recovery

- **NFR-1.1 — Operator-triggered operation:** No uptime or recovery-time objective applies to this local proof of concept. An operator invokes provisioning when needed.
- **NFR-1.2 — Safe recovery:** After correcting a provider or local configuration error, an operator can rerun the existing provisioning command. The rerun inspects existing state and completes or validates missing work without deleting successful resources from a prior partial run.
- **NFR-1.3 — Independent provider attempts:** Kerberos and RustFS provisioning are each attempted once per invocation, independently. Failure in one branch does not suppress the other branch.
- **NFR-1.4 — Aggregate status:** The command returns failure if either provider branch fails and reports each provider's result. No automatic retry or rollback is performed.

## Scale and Performance

- **NFR-2.1 — Bounded PoC scope:** Support the existing small, fixed platform identity set plus one StarRocks Kerberos identity and one StarRocks RustFS identity/policy. No dynamic identity fleet or horizontal scaling requirement applies.
- **NFR-2.2 — Completion time:** Functional completion and reliable provider validation are required; no hard wall-clock or per-provider latency target is imposed.

## Security and Credential Handling

- **NFR-3.1 — Host permissions:** Credential directories are owner-only (`0700`) and StarRocks secret/keytab files are owner read/write only (`0600`), following the existing local credential convention.
- **NFR-3.2 — Repository exclusion:** Runtime credentials remain under ignored `.runtime/credentials/` paths and must not be committed.
- **NFR-3.3 — No credential output:** Passwords, RustFS secret keys, keytab contents, Kerberos tickets, signed request headers, and secret-bearing response bodies are never printed or logged.
- **NFR-3.4 — Actionable redacted diagnostics:** On failure, output identifies Kerberos and RustFS outcomes separately and gives safe error context with retry or manual-reconciliation guidance, while preserving the redaction requirements above.
- **NFR-3.5 — No implicit rotation:** Provisioning does not replace existing credentials or principal keys. Authentication or policy drift fails closed and requires operator reconciliation.
- **NFR-3.6 — Least privilege:** The StarRocks RustFS identity remains scoped to the approved `databaseA` and `databaseB` prefixes. This NFR does not broaden the permissions approved in Functional Design.

## Reliability and Operations

- **NFR-4.1 — Idempotent rerun:** Repeated invocation with valid existing resources must validate and reuse them without changing secret material.
- **NFR-4.2 — Partial completion preservation:** Resources successfully provisioned by either provider remain available if the other provider fails. The operator receives provider-level statuses and an aggregate failure result.
- **NFR-4.3 — No automatic retry:** Each provider is attempted once. Operators correct transient or configuration causes and rerun; failed state is not automatically retried in-process.
- **NFR-4.4 — Manual reconciliation:** Conflicting existing credentials or policy state is reported as requiring manual reconciliation; provisioning must not silently rewrite it.
- **NFR-4.5 — Observability scope:** This operator-invoked PoC command requires actionable console diagnostics and provider outcomes. No background monitoring, metrics service, alerting, or machine-readable JSON output is required.

## Maintainability and Usability

- **NFR-5.1 — Existing command-line workflow:** Keep `scripts/provision-identities.sh` as the operator entry point and retain its existing orchestration behavior, including Hive configuration rendering/restart after successful full provisioning.
- **NFR-5.2 — Existing implementation stack:** Extend the current Bash/Python provisioner and its existing command-line/provider libraries. Do not add an orchestration framework or replace the stack.
- **NFR-5.3 — Operational documentation:** Document prerequisites, local credential bootstrap, invocation, per-provider outcomes, safe reruns, redacted diagnostics, and manual reconciliation steps.
- **NFR-5.4 — No UI:** No graphical interface or accessibility requirements apply to this command-line infrastructure unit.

## Verification Criteria

1. Inspect the generated credential directory and file modes: directories are `0700`, and StarRocks secret/keytab files are `0600`.
2. Confirm `.runtime/credentials/` remains excluded from version control and no credential contents are emitted by provisioning output.
3. Exercise a successful provision and rerun; the second run reuses existing credentials and reports validated/already-present state without rotation.
4. Exercise Kerberos-only and RustFS-only failures independently; confirm both branches are attempted, the successful side is preserved, provider statuses are redacted, and aggregate status is failure.
5. Confirm conflicting pre-existing credential or policy state fails closed and is not silently replaced.
6. Confirm the command performs no automatic retry and provides enough safe context for an operator to correct the issue and rerun.

## Traceability

These requirements refine approved Functional Design rules for identity separation, filesystem-safe credentials, provider validation, failure handling, and idempotent recovery. They support FR-4/FR-5 and intent NFR-1/NFR-2. Query-time TGT lifecycle and StarRocks service behavior are deferred to Unit 2; SQL-user provisioning and authorization are deferred to Unit 3.
