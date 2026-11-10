# Logical Components — Unit 1 Identity Provisioning NFR Design

## Component View

The NFR design is implemented inside the existing operator CLI and provider scripts. These are logical responsibilities, not new deployable services.

| Logical component | Responsibility | NFR contribution |
|---|---|---|
| Provisioning CLI orchestrator | Invoke Kerberos and RustFS branches independently once, capture exit statuses, and return aggregate status. | Independent failure handling, bounded execution, operator reruns. |
| Kerberos provider branch | Create/reuse the StarRocks principal and keytab, validate TGT acquisition, and return a safe result category. | Identity validation, no implicit key rotation, provider-level status. |
| RustFS provider branch | Ensure the approved policy/account state, validate scoped list access, and return a safe result category. | Least privilege, drift detection, provider-level status. |
| Credential filesystem guard | Check expected paths and owner access; set or enforce directory/file modes without changing credential contents. | `0700` directories, `0600` files, safe local secret handling. |
| Redacted result formatter | Render allowlisted provider outcomes, safe status codes, action hints, and aggregate exit status. | Secret redaction, actionable diagnostics, no JSON contract. |
| Existing provider APIs and local credential store | Supply KDC/RustFS operations and ignored runtime credential files. | Reuse current dependencies; no additional persistent infrastructure. |

## Interaction Sequence

1. The operator runs `scripts/provision-identities.sh` after local credential bootstrap when required.
2. The CLI orchestrator validates credential path protection and prepares provider execution.
3. The Kerberos branch runs once and reports a safe outcome to the orchestrator.
4. The RustFS branch runs once even if Kerberos failed and reports a safe outcome.
5. The result formatter emits both provider outcomes and safe operator guidance.
6. The orchestrator returns success only if both branches succeeded; otherwise it returns failure while preserving successful provider resources.
7. The operator corrects the reported issue and invokes the command again; existing state is inspected and reused idempotently.

## Component Constraints

- Components are responsibilities within the existing Bash/Python CLI and provider scripts; they do not introduce separate containers or processes beyond current command invocation.
- The design adds no database, queue, cache, monitoring agent, external secret manager, or service UI.
- Provider result formatting must not receive or expose raw secret-bearing response bodies.
- Ownership and permission failures are fail-closed and require safe manual reconciliation when the invoking process cannot correct the mode or expected owner state.
- Provider success and failure remain separately visible even when the aggregate operation fails.
