# Tech Stack Decisions — Unit 1 Identity Provisioning

## Decision Summary

| Area | Decision | Rationale |
|---|---|---|
| Operator interface | Existing `scripts/provision-identities.sh` CLI | Preserves the approved all-platform identity workflow and its established operator entry point. |
| Orchestration | Existing Bash scripts | Kerberos principal/keytab provisioning and provider sequencing already use shell scripts in this repository. |
| RustFS provisioning | Existing Python identity provisioner and provider libraries | Reuses established RustFS account, policy, and S3-compatible validation code. |
| Dependencies | Existing command-line tools and Python/provider dependencies | Avoids adding a new orchestration framework or replacing current identity tooling. |
| Credential storage | Existing ignored `.runtime/credentials/` convention | Keeps runtime secrets outside tracked project files and follows the chosen `0700` directory / `0600` file modes. |
| Results | Human-readable per-provider statuses and aggregate process exit status | Supports manual local operation and safe retry/reconciliation; JSON output was not requested. |
| Retry policy | One attempt per provider per invocation; operator reruns after correction | Keeps failure handling explicit and avoids implicit repeated requests. |

## Constraints and Contracts

- Unit 1 extends rather than replaces the existing Bash/Python identity-provisioning stack.
- Kerberos and RustFS provider branches execute independently; the aggregate command fails when either branch fails.
- Successful provider resources remain intact if the other branch fails.
- Existing credentials and principal keys are reused; the normal command does not rotate or delete them.
- Secret-bearing values and responses must be redacted from console output and logs.
- The existing full provisioning workflow continues to own its Hive configuration rendering and restart behavior.
- No new framework, user interface, JSON status contract, monitoring service, or automatic retry mechanism is introduced.

## Deferred Decisions

- StarRocks FE/BE image, service configuration, and runtime dependencies belong to Unit 2.
- Kerberos ticket renewal during StarRocks runtime belongs to Unit 2 NFR and Infrastructure Design.
- StarRocks SQL accounts, grants, and bootstrap interfaces belong to Unit 3.
