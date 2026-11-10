# Unit 5 NFR Design Plan — Ranger and StarRocks Authorization

## Approved baseline

The approved Unit 5 NFR requirements are in `construction/unit-5/nfr-requirements/`. The PoC supports the current StarRocks 4.1.6 environment and a small set of identity profiles without throughput, latency, availability, revocation, retention, RPO, or RTO SLAs. LDAP/Ranger calls must be bounded; authentication and unknown/new authorization decisions cannot fall back to a broader role. Cached-policy outage behavior and end-to-end group revocation must be measured, not assumed. LDAPS/TLS, protected credentials, sanitized local audit with rotation, isolated Ranger-state backup/restore, version pinning, and disposable test state are required.

The approved functional design keeps three decisions separate: FreeIPA authenticates users and owns group membership; Ranger authorizes SQL through StarRocks; RustFS enforces direct Spark S3 operations. StarRocks FE/BE uses a distinct service identity for HMS/RustFS reads after end-user Ranger authorization. StarRocks remains pinned at 4.1.6. Apache Ranger 2.9.0 is only a compatibility candidate; no exact combination is yet established.

## NFR design checklist

- [x] Trace every NFR requirement to a design pattern and logical component responsibility.
- [x] Define principal binding from FreeIPA authentication through StarRocks session and Ranger authorization; distinguish it from the StarRocks storage identity.
- [x] Define the group/authorization boundary across FreeIPA, Ranger UserSync, Ranger Admin policies, and the StarRocks FE integration.
- [x] Define bounded dependency calls, retry classification, and fail-closed behavior for LDAP, UserSync, Ranger Admin, StarRocks, HMS, and RustFS.
- [x] Define policy polling/cache and group-revocation measurement; distinguish policy-service outage from cached-policy decisions.
- [x] Define the security boundary for LDAP/TLS, Ranger endpoint credentials, StarRocks backend credentials, and audit data.
- [x] Define audit records for allow/deny decisions, bounded reasons, and redaction rules without asserting a retention SLA.
- [x] Define isolated backup/restore and before/after preservation checks for Ranger policies and disposable StarRocks state.
- [x] Define verification/stop conditions for exact StarRocks 4.1.6/Ranger compatibility, external catalog resource mapping, and SQL action coverage.
- [x] Record technology, service, and runtime details for Infrastructure Design without pinning unverified versions or authorizing implementation.
- [x] Generate `construction/unit-5/nfr-design/nfr-design-patterns.md` and `logical-components.md`.
- [x] Present NFR Design artifacts for review before Unit 5 Infrastructure Design.

## Design questions and proposed patterns

1. **Identity binding:** Carry the authenticated FreeIPA username to the Ranger plugin unchanged; map only approved role groups. Never replace the requester with the StarRocks FE/BE storage identity for the Ranger decision.
2. **Layered authorization:** Ranger authorizes StarRocks SQL requests. On allow, StarRocks uses its own backend credentials for HMS/RustFS. Direct Spark remains a separate user-credential-to-RustFS flow; Ranger is not consulted.
3. **Default denial:** Unknown users, unresolved/conflicting groups, unknown resources/actions, and new uncached decisions are denied. Existing native grants must not form an alternate allow path in isolated test state.
4. **Bounded dependency handling:** Use finite connection/read timeouts and bounded retry only for safe transient failures. Authentication, authorization, invalid identity, malformed responses, and unknown resource mappings stop without retry or fallback.
5. **Cache/outage behavior:** Treat StarRocks FE policy cache as a distinct control. Measure cached and uncached decisions during Ranger outage, policy refresh, restart, and group removal. Do not claim fail-closed behavior for existing cached entries unless tests prove it.
6. **Revocation:** Measure from FreeIPA group removal through UserSync and FE policy refresh for both new and existing SQL sessions. Report observed behavior and delay; no hard bound is selected.
7. **Audit and redaction:** Record principal, group context where available, resource, action, decision, policy/service identifier, timestamp, and bounded reason. Keep test logs protected/rotated and exclude secrets, tickets, object data, and sensitive query literals.
8. **Preservation:** Export Ranger service definitions and policies before isolated mutation; prove restore in isolated state. Preserve existing StarRocks/HMS/RustFS data and named volumes; remove only unique synthetic test resources.
9. **Compatibility stop gate:** If Ranger cannot correctly authorize the Hive external catalog or the pinned StarRocks integration cannot use FreeIPA group identity, stop before implementation and return for architecture review. Do not substitute native grants or a Hive plugin claim for the failing boundary.

## Design boundaries

- NFR Design is documentation only. Do not add/start Ranger, change Compose, install packages/plugins, edit StarRocks configuration/grants, create identities/policies, or run tests.
- Do not use production FreeIPA, RustFS, StarRocks volumes, buckets, or data for compatibility experiments.
- Do not change StarRocks 4.1.6, choose Ranger 2.9.0 as final pin, or add Solr/HA/gateway components without exact compatibility evidence and explicit architecture approval.
- Do not claim that Ranger secures direct Spark-to-RustFS operations.
- Infrastructure Design may specify network, storage, secret mounts, health checks, timeout configuration, and pinned images only after NFR Design approval; uncertain enforcement semantics remain Build and Test gates.

## Approval gate

The user approved this Unit 5 NFR Design Plan on 2026-10-27 and requested continuation. The NFR Design artifacts have been generated. Review `construction/unit-5/nfr-design/nfr-design-patterns.md` and `logical-components.md` before Unit 5 Infrastructure Design. Production FreeIPA, production RustFS policies, StarRocks production grants, service migration, and KDC cutover remain separately gated and are not authorized here.

## Superseding direction — 2026-10-28

The user has chosen StarRocks native roles/grants mapped to FreeIPA LDAP groups, without Ranger. This replaces the Ranger-specific NFR implementation plan above. Current patterns are recorded in `construction/unit-5/nfr-design/nfr-design-patterns.md` and `logical-components.md`; cache/revocation behavior, exclusive role-group membership, LDAP secret transport, direct Spark/RustFS separation, and test-only target isolation remain applicable. Ranger-specific UserSync, policy-cache, Ranger outage, and Ranger audit tests are no longer required.
