# NFR Requirements Plan — Unit 4: Dremio Source and Query Identity

## Scope

Assess the non-functional requirements for the Unit 4 Dremio identity and authorization validation path. Preserve the approved single-host local PoC, Dremio 26.0.5 Community, Hive 3.1.3, Kerberos, the existing RustFS source credential, and the functional allow/deny matrix. No runtime changes or credential rotation are part of this stage.

## Existing constraints

- Unit 1/3 designs specify a single-host local PoC with no uptime, performance, or horizontal-scale SLA.
- Existing services and versions are pinned; no new authorization service or component is approved.
- Distinct Dremio query users must be used, and the effective Hive identity and allow/deny result must be observable.
- Diagnostics must redact passwords, S3 keys, keytabs, ticket contents, and credential-bearing URLs.
- The current Hive Metastore/RustFS authorization path is a feasibility gate. An unavailable authorization outcome must not be described as a pass.
- Security Baseline and Resiliency Baseline extensions are disabled; Property-Based Testing is partial and no pure transformation requiring that extension is introduced by this unit.

## NFR assessment checklist

- [x] Confirm the local PoC load and performance target; avoid inventing production targets.
- [x] Confirm availability, restart, and state-preservation expectations for authorization validation.
- [x] Confirm security, credential handling, logging, and evidence-retention requirements.
- [x] Confirm maintainability and compatibility constraints for the pinned Dremio/Hive setup.
- [x] Resolve all answers and ambiguities; produce NFR requirements and technology decisions.

## Questions

Answer each question in `unit-4-nfr-requirements-questions.md`. Recommendations preserve the already-approved local PoC scope.

## Current Status

Functional Design was approved by the user on 2026-10-23. The user selected A for all four NFR questions. Requirements and technology decisions are complete and ready for review. No runtime files, credentials, or data were changed.
