# NFR Design Plan — Unit 2 Identity and Permission Provisioning

## Scope

Translate the approved Unit 2 NFR requirements into logical implementation patterns for provisioning readiness, component-specific credential delivery, retries, failure recovery, operator reporting, and identity setup sequencing. Concrete Compose syntax, account-management commands/APIs, file names, mounts, healthcheck commands, and policy documents remain for Infrastructure Design and Code Generation.

The design must preserve the fixed local identity set, distinct component credentials, restricted ignored runtime storage, explicit credential rotation, fail-fast behavior, safe reruns, redacted output, and deferred post-ETL reader grants. It must not claim support for a component API or Hive/RustFS authorization behavior that has not been verified.

## NFR Design Checklist

- [x] Select readiness and dependency-gating patterns for one-shot identity provisioning.
- [x] Select local credential delivery and consumer isolation patterns.
- [x] Select safe rerun, retry, rotation, and partial-failure patterns.
- [x] Define logical component adapters and provisioning result/reporting flow.
- [x] Confirm no persistent identity service, monitoring, HA, or scaling component is needed.
- [x] Generate Unit 2 NFR design patterns and logical-component artifacts.
- [x] Validate the design against approved Unit 2 NFR and Functional Design artifacts.

## Design Questions

### Question 1 — Provisioner dependency gating

How should identity setup be gated on component readiness?

A) Run an explicit one-shot provisioner only after the required KDC, Hive Metastore, PostgreSQL, RustFS, and Dremio setup prerequisites are ready. Distinguish service health from successful account setup; dependent ETL remains blocked if a required identity/permission step fails (recommended; follows approved NFRs).

B) Start provisioning as soon as Compose containers are running and retry all failed account operations until they succeed.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 2 — Credential delivery

How should provisioner credentials and created credentials be handled?

A) Read only the component admin/setup credential files required for each step from the protected ignored runtime directory; write generated credentials/keytabs there with restricted permissions; pass file references rather than values; mount inputs read-only where supported (recommended; preserves separation and limits exposure).

B) Pass credentials through command-line arguments or broad environment variables for simpler scripting.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 3 — Idempotency, retries, and rotation

How should repeated provisioning and transient failures work?

A) Use ensure-style component operations that detect existing identities and preserve their credentials. Retry only bounded dependency-availability checks and known-safe idempotent requests. Handle credential rotation through a separate explicit action (recommended; aligns with approved NFRs).

B) Recreate accounts and rotate secrets on every run to force consistency.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 4 — Partial failure and recovery

What should the run do after a required component operation fails?

A) Stop at the failing required operation, return an incomplete/failed result with a redacted diagnostic, and preserve completed state for an idempotent rerun. Never automatically delete identities or persistent data (recommended; follows approved Functional Design).

B) Continue all remaining steps and automatically roll back successful changes if any step fails.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — Logical adapter and execution topology

How should component-owned setup operations be organized?

A) Keep small component-specific adapters behind one explicit one-shot operator action. Do not add a persistent identity service or central policy engine; an unsupported adapter capability stops the required flow and is returned as a feasibility blocker (recommended; matches the approved boundary).

B) Add a persistent identity-management service that owns and reconciles all component accounts.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 6 — Provisioning report

Where and how should the result be reported?

A) Write concise per-identity/per-component statuses to the operator's command output and container logs, with secret-safe diagnostics; do not persist a second credential-bearing account database (recommended; sufficient for one local operator).

B) Persist a separate report/state file or database for every provisioning run; specify retention and access controls.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 7 — Performance and scale pattern

How should setup ordering and concurrency be designed?

A) Provision the fixed PoC identities sequentially in dependency order. Avoid concurrency and optimization unless measurement reveals a need (recommended; no throughput target exists).

B) Provision identities concurrently or design for bulk scale; specify expected volume and failure-isolation requirements.

X) Other (describe after `[Answer]:`)

[Answer]:A

## Applicability Notes

- Security Baseline and Resiliency Baseline extensions are disabled. The approved functional and NFR controls remain required.
- No availability, performance, bulk provisioning, or horizontal scaling target exists for this local PoC.
- Component-specific API and policy support remains an Infrastructure Design/Code Generation verification gate.

## Extension Compliance Summary

- **Security Baseline**: Not enabled. Credential separation, restricted runtime files, read-only delivery, and secret-safe output remain mandatory.
- **Property-Based Testing (Partial)**: Not applicable to this design-only stage; reassess only if new pure transformation logic is introduced.
- **Resiliency Baseline**: Not enabled. Safe reruns, fail-fast behavior, and preservation of partial state follow approved requirements.

## Current Status

All seven answers select the recommended patterns and are consistent with approved Unit 2 Functional Design and NFR Requirements. Unit 2 NFR Design artifacts are generated and ready for review. No application configuration has changed.
