# Unit 1 NFR Requirements Plan — Identity Provisioning

## Unit Context

Unit 1 provisions the dedicated StarRocks Kerberos principal/keytab and RustFS identity/policy through the existing identity-provisioning workflow. The approved functional design requires independent attempts for both providers, redacted per-provider outcomes, an overall failure if either provider fails, preservation of successful resources for retry, and no implicit credential rotation.

This is a local Docker Compose proof of concept. NFR answers should define requirements for this provisioning operation and avoid silently expanding the approved identity scope or changing runtime responsibilities assigned to later units.

## NFR Requirements Tasks

- [x] Review Unit 1 functional design and trace its failure, retry, credential, and validation behavior to applicable NFRs.
- [x] Resolve availability and recovery expectations for the local provisioning operation.
- [x] Resolve expected scale and any completion-time requirements.
- [x] Resolve secret handling, diagnostic redaction, and filesystem protection requirements.
- [x] Resolve retry, observability, and operator-facing diagnostic expectations.
- [x] Confirm implementation stack constraints and maintenance expectations.
- [x] Check all answers for completeness, contradictions, and ambiguity; create clarification questions if needed.
- [x] Generate `construction/unit-1-identity-provisioning/nfr-requirements/nfr-requirements.md` and `tech-stack-decisions.md` after answers are resolved.
- [x] Validate traceability and present the NFR Requirements artifacts for explicit approval.
- [x] Record user approval and advance to Unit 1 NFR Design.

## Questions

Fill each `[Answer]:` line with an option letter. Choose the last option, `Other`, and describe your choice if none of the listed options fits.

### Question 1 — Availability and recovery

What availability and recovery target applies to identity provisioning in this local PoC?

A) Operator-triggered best effort: no uptime or recovery-time objective; rerun the idempotent command after correcting a failure.

B) Require the provisioning command to recover automatically from transient provider failures within the same invocation, with a bounded retry policy.

C) Define an explicit availability or recovery-time target for this operation.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 2 — Scale

What identity and policy scale should Unit 1 support?

A) The small, fixed local PoC set, including the existing platform identities plus one StarRocks Kerberos identity and one StarRocks RustFS identity/policy.

B) A growing configurable set of service identities and policies managed through the same provisioner.

C) A defined larger scale; provide expected identity counts and growth in `Other`.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 3 — Provisioning performance

What completion-time requirement applies to the provisioning command?

A) Functional completion only; no hard latency target, and provider calls may take as long as needed to return reliable results.

B) Set a maximum wall-clock duration for the full command, including both independent provider attempts; provide the target in `Other`.

C) Set per-provider time limits and bounded retries; provide values in `Other`.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 4 — Local credential protection

What filesystem protection should apply to StarRocks keytab and RustFS secret material on the host?

A) Follow the existing credential convention: credential directories owner-only (`0700`), secret/keytab files owner read/write only (`0600`), ignored by Git, and never print credential contents.

B) Keep the existing file permissions and Git exclusion, and additionally encrypt credential files at rest using a specified local mechanism.

C) Use a different permission or storage policy; describe the required owner, mode, and storage location in `Other`.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 5 — Diagnostics and secret redaction

What should operators see when Kerberos and/or RustFS provisioning fails?

A) A concise status per provider, actionable error context, and retry/reconciliation guidance; redact passwords, access secrets, keytab contents, tokens, and sensitive request headers.

B) The same redaction and provider statuses, plus structured machine-readable JSON output for automation.

C) Minimal pass/fail output only; detailed diagnostics remain in service logs.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 6 — Retry and failure handling

What retry behavior should apply to transient provider errors?

A) Do not retry automatically; attempt both providers once, preserve successful changes, return both statuses, and let the operator correct the cause and rerun.

B) Retry only errors classified as transient using a bounded backoff; still attempt the other provider and preserve successful changes.

C) Retry every provider error a bounded number of times before returning the aggregate result.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 7 — Implementation and dependencies

How should Unit 1 handle implementation stack and dependencies?

A) Extend the existing Bash/Python provisioner and its current command-line/provider libraries; add no new orchestration framework.

B) Add a small dedicated orchestration tool while continuing to reuse existing provider scripts and libraries; describe the tool in `Other`.

C) Replace the existing provisioning stack with a specified alternative; describe it in `Other`.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 8 — Maintenance and operator interface

What maintenance and usability expectations apply?

A) Keep the current CLI workflow; document prerequisites, invocation, provider-specific outcomes, safe reruns, and manual reconciliation. No UI or accessibility requirement applies.

B) Also provide a stable machine-readable status/exit-code contract for future automation, without adding Airflow/Jenkins in this intent.

C) Add an operator UI or interactive wizard; describe the scope in `Other`.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

## Applicability Notes

- User-facing UI accessibility is not applicable unless Question 8 introduces a UI.
- StarRocks runtime availability, Kerberos ticket renewal during service operation, query performance, and SQL authorization are owned by later units; do not assign them to this provisioning unit.
- Security Baseline was declined for the intent. Unit-specific approved credential protection and redaction requirements still apply.
- Existing identity resources must not be implicitly rotated or deleted; this unit's NFRs must preserve that approved behavior.
- No application or runtime configuration is changed during NFR Requirements planning.
