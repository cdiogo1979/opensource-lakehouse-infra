# NFR Design Plan — Unit 4: Dremio Source and Query Identity

## Scope

Translate the approved Unit 4 NFRs into design patterns and logical component responsibilities for the Dremio query identity and authorization demonstration. Preserve the existing local Compose deployment, pinned service versions, Dremio source settings, and credentials. No application or runtime changes occur in this stage.

## NFR design checklist

- [x] Define failure classification and manual recovery behavior for the four authorization scenarios.
- [x] Define the fixed-scale serial query execution pattern and explicitly exclude performance/availability objectives.
- [x] Define the credential boundary and redacted evidence handling across Dremio, Hive, and local artifacts.
- [x] Map responsibilities to existing logical components; determine whether any new component is required.
- [x] Resolve design questions and generate NFR design artifacts.

## Existing decisions

- Fixed scope: two Dremio query users, two Hive databases, and the current sample tables/views; no latency or throughput SLA.
- Single-host/manual recovery; preserve persistent data and rerun only safe failed query checks.
- Use distinct local Dremio accounts, preserve Kerberos service identity and the current RustFS writer key.
- Keep only minimal, local, redacted evidence; no formal retention period or new audit service.
- Security Baseline and Resiliency Baseline extensions are disabled. The approved security and recovery requirements above remain mandatory.

## Current Status

Unit 4 NFR Requirements were approved by the user on 2026-10-23. The user selected A for all five NFR Design questions. The design artifacts are complete and ready for review. No runtime files, credentials, or data were changed.
