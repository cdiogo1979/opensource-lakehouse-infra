# Unit 1 NFR Design Plan — Identity Provisioning

## Unit Context

The approved NFR Requirements define a manually invoked local PoC provisioner. It uses the current Bash/Python identity stack, attempts Kerberos and RustFS independently once each, returns redacted provider statuses and aggregate failure, preserves successful resources, and does not automatically retry or rotate credentials. Credential directories and files must have owner-only `0700` and `0600` permissions respectively.

## NFR Design Tasks

- [x] Map each approved Unit 1 NFR to a concrete pattern or logical component.
- [x] Resolve provider-branch orchestration and aggregate status patterns without changing the one-attempt behavior.
- [x] Resolve how the command prevents secret leakage while producing actionable diagnostics.
- [x] Resolve enforcement behavior for credential filesystem modes, including existing files.
- [x] Confirm the local CLI component boundary and absence of additional resilience/scaling infrastructure.
- [x] Check answers for completeness, consistency, and ambiguity; prepare clarifications if needed.
- [x] Generate `construction/unit-1-identity-provisioning/nfr-design/nfr-design-patterns.md` and `logical-components.md`.
- [x] Validate NFR traceability and present the design for explicit approval.
- [x] Record user approval and advance to Unit 1 Infrastructure Design.

## Questions

Fill each `[Answer]:` line with an option letter. Choose the last option, `Other`, and describe your choice if none of the listed options fits.

### Question 1 — Independent provider execution pattern

How should the existing shell orchestration guarantee the RustFS branch is attempted even if Kerberos provisioning exits unsuccessfully, while each provider is still attempted only once?

A) Run each provider in an explicit status-capturing conditional, save its exit status, continue to the other provider, then return a nonzero aggregate status if either failed.

B) Run each provider in a child process and capture its exit code/output separately; aggregate both statuses in the parent command.

C) Refactor the provider flow into a Python coordinator that invokes the existing Kerberos and RustFS commands and aggregates their results.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 2 — Diagnostic redaction pattern

How should actionable errors be produced without leaking provider response content or credential material?

A) Emit fixed, allowlisted provider/error categories with safe identifiers and HTTP/Kerberos status codes; discard raw provider response bodies and command output unless specifically parsed into approved fields.

B) Sanitize raw error text using known-secret replacement and generic token/header scrubbing, then truncate it before display.

C) Return only fixed provider-level failure categories; do not include provider error text or status details.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 3 — Credential permission enforcement

How should the provisioner handle StarRocks credential paths whose permissions do not satisfy the approved `0700` directory and `0600` file modes?

A) Apply the required modes to the StarRocks credential directory and files, without changing credential contents; fail if ownership or mode correction cannot be completed.

B) Fail closed and report the incorrect mode; require an operator to correct permissions manually, without changing filesystem metadata.

C) Apply modes only to newly created paths; warn but allow existing paths with broader modes.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 4 — Retry and recovery mechanism

Which recovery pattern best implements the approved one-attempt-per-provider and operator-rerun requirement?

A) No retry loop or backoff. Return each provider's result; a subsequent invocation re-inspects state and idempotently resumes missing work.

B) Add a circuit breaker to suppress provider calls after repeated failures across invocations.

C) Add a persistent recovery queue for unfinished provider work.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 5 — Scaling and performance pattern

Which design is appropriate for the fixed small PoC identity set and absence of hard timing targets?

A) Keep provisioning sequential and bounded to the configured StarRocks identity additions; add no parallel worker, cache, or scaling subsystem.

B) Parallelize independent identity operations to reduce elapsed time.

C) Introduce a configurable batch/concurrency mechanism for future identity growth.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 6 — Logical components and infrastructure

What runtime/infrastructure components should Unit 1 add for these NFRs?

A) No new persistent or background component. Keep the existing CLI, provider-specific commands, protected local credential files, and provider APIs; report results to the invoking operator.

B) Add a local audit log component with structured persistent provider outcomes.

C) Add an external monitoring/alerting or secrets-management service as part of this unit.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

## Applicability Notes

- Resilience applies as independent single attempts, preservation of successful state, and a safe idempotent operator rerun. Automatic retry, circuit breakers, and persistent queues conflict with approved NFR requirements unless explicitly revised.
- Scalability applies only to the bounded PoC identity set; distributed scaling mechanisms are not implied.
- Performance has no hard latency target; the current provider validation timeouts and operational behavior remain unless changed by an explicit answer.
- Security design must enforce the approved file/directory modes, redaction, least privilege, no implicit rotation, and existing ignored credential paths. Security Baseline remains declined, but these Unit 1 requirements are binding.
- Logical components should reuse the existing Bash/Python CLI and provider services; no new background process is implied.
- No application or runtime configuration is changed during NFR Design planning.
