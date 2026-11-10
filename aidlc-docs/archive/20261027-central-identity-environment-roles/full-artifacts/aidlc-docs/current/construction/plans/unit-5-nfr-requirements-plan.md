# Unit 5 NFR Requirements Plan — Ranger and StarRocks Authorization

## Unit and approved functional baseline

Unit 5 adds Ranger-backed SQL authorization to the existing StarRocks OSS 4.1.6 Hive external-catalog path. FreeIPA is the intended identity source; FreeIPA LDAP authentication/group lookup and Ranger UserSync are the working design direction. Ranger Admin policies map the approved groups to SQL permissions. StarRocks' separate FE/BE service identity accesses HMS/RustFS after query authorization. Direct Spark-to-RustFS access remains governed by the user's RustFS identity, outside Ranger.

The role matrix and rules are in `construction/unit-5/functional-design/`. Developer reads all environments and writes only development; analyst reads production only and cannot write; `write-service-account` is non-interactive and receives only approved DML write actions across environments; authorized administrator privileges are preserved. Schema/security DDL remains administrator-only by default. Exact StarRocks/Ranger compatibility, LDAP group propagation, external-catalog resources/actions, and Ranger outage/cache behavior have not yet been verified.

This stage sets measurable quality requirements for future Unit 5 implementation and tests. It does not add or start Ranger services, alter StarRocks grants, create users/groups/policies, change LDAP/KDC settings, rotate credentials, modify RustFS, or touch production data or named volumes.

## NFR assessment checklist

- [x] Review the approved Unit 5 functional artifacts and record the identity, SQL authorization, storage service identity, and direct Spark boundaries.
- [x] Inspect the pinned StarRocks profile and current component versions without changing runtime state.
- [x] Confirm supported local identity/group scale and concurrent SQL session assumptions: A.
- [x] Confirm Ranger decision latency and finite timeout/retry expectations: A.
- [x] Confirm Ranger Admin, UserSync, LDAP, and StarRocks outage/fail-closed requirements, including cached-policy behavior: A.
- [x] Confirm role-removal propagation requirements across FreeIPA, UserSync, Ranger policy polling, and active SQL sessions: A.
- [x] Confirm LDAP/API transport security, secret storage, service identity isolation, and administrative access requirements: A.
- [x] Confirm audit fields, destination, rotation, access controls, and retention expectations: A.
- [x] Confirm policy/configuration backup and isolated restore evidence required before future policy changes: A.
- [x] Confirm exact-version compatibility policy and whether changes to the pinned StarRocks stack are allowed: A.
- [x] Confirm verification is restricted to isolated test state: A.
- [x] Generate `construction/unit-5/nfr-requirements/nfr-requirements.md` and `tech-stack-decisions.md` for review before Unit 5 NFR Design.

## Assessment boundaries

- **Scale/performance**: Local proof of concept with four identity profiles and a small set of Hive catalog databases. No throughput, concurrency, or query latency SLA is currently approved.
- **Availability/recovery**: Ranger Admin, LDAP/UserSync, StarRocks FE/BE, HMS, and RustFS are dependencies. Failure must not create an alternate identity or broaden SQL access. StarRocks Ranger policy cache semantics must be measured rather than assumed.
- **Revocation/consistency**: Revocation crosses FreeIPA group updates, UserSync, Ranger Admin policy state, FE policy polling/cache, and existing SQL sessions. Measure the complete chain and test both fresh logins and active sessions.
- **Security**: LDAP and policy endpoints require protected transport where supported. Ranger Admin/UserSync/StarRocks service credentials must remain outside source, ordinary environment literals, command output, SQL, and logs. Human SQL identity and StarRocks storage identity remain separate.
- **Auditability**: Capture enough information to explain StarRocks allow/deny outcomes and distinguish authentication, group lookup, Ranger, HMS, and RustFS failures. Do not log passwords, keys, tickets, or sensitive SQL literals.
- **Preservation/recovery**: Preserve existing StarRocks FE/BE volumes, HMS metadata, RustFS buckets/objects, and all user workspaces. Unit 5 test data is synthetic and disposable. Backup/restore should target isolated Ranger state before policy testing.
- **Compatibility**: StarRocks remains pinned to 4.1.6. The official Ranger download page currently identifies 2.9.0 as stable; evaluate it as a candidate, not as a presumed-compatible pin. StarRocks docs list Ranger 2.1.0+ as a minimum but do not certify this exact combination. Keep all plugin/service-definition artifacts pinned and verified before implementation.
- **Verification**: NFRs add boundedness, outage/revocation behavior, confidentiality, audit evidence, and recoverability. Functional allow/deny behavior remains defined by Unit 5 Functional Design.

## Questions

Choose one option for each question. Option A is recommended for this local proof of concept. Choose `X` and describe the requirement if none fits.

### Question 1 — Scale and concurrency

What scale should the Ranger/StarRocks authorization path support?

A) Fixed local PoC: current StarRocks cluster, four approved identity profiles, current environment databases, and a small manual extension; no concurrency or throughput commitment. **(Recommended)**

B) Set identity counts, concurrent SQL sessions, growth assumptions, and load profile in `X`.

X) Other (describe scale and concurrency).

[Answer]:A

### Question 2 — Authorization latency and timeouts

What performance requirement should apply to Ranger decisions?

A) Correctness first; no end-to-end SQL latency SLA. Use finite connect/read timeouts and bounded retries for LDAP/UserSync/Ranger calls, avoid retry storms, and record sanitized decision timing. **(Recommended)**

B) Specify a maximum authorization latency and expected load profile in `X`.

X) Other (describe timing requirements).

[Answer]:A

### Question 3 — Dependency outage and availability

What should happen when LDAP, Ranger Admin, or the FE policy connection is unavailable?

A) Single-host best effort with no HA/RTO guarantee. No new or uncached authorization may be assumed allowed. Test and document how StarRocks handles last-known-good cached policies during Ranger outages; do not claim outage fail-closed behavior until verified. Recovery is operator-led and preserves data. **(Recommended)**

B) Require an explicit availability target, stale-policy maximum, fail-closed behavior, and recovery targets in `X`.

X) Other (describe availability and outage requirements).

[Answer]:A

### Question 4 — Group revocation and policy freshness

How quickly must FreeIPA group removal stop new StarRocks access?

A) No unverified immediate-revocation claim. Configure finite UserSync and FE policy-poll intervals where supported, measure end-to-end revocation for a new login and an active SQL session, and document the observed worst case; no hard latency SLA. **(Recommended)**

B) Require a maximum revocation delay and active-session termination behavior in `X`.

X) Other (describe propagation requirements).

[Answer]:A

### Question 5 — Credential and transport security

What minimum security posture applies to LDAP, Ranger, and StarRocks credentials?

A) Use LDAPS/TLS with certificate validation for FreeIPA and TLS for Ranger API/policy endpoints where supported by the selected OSS components. Store bind/admin credentials in protected secret files or the approved secret manager; never place them in source, ordinary environment values, command arguments, SQL output, or logs. Keep StarRocks service identity separate from end-user SQL identity. **(Recommended)**

B) Require TLS on every internal path and specify certificate issuance/rotation and client-authentication requirements in `X`.

X) Other (describe credential and transport requirements).

[Answer]:A

### Question 6 — Audit coverage and retention

What audit evidence is required for Ranger/StarRocks decisions?

A) Capture sanitized principal, group context where available, resource, action, allow/deny outcome, policy/service identifier, timestamp, and bounded reason. Keep protected local test logs with rotation; no production retention SLA or centralized audit commitment. **(Recommended)**

B) Define an immutable destination, access model, tamper protection, and retention period in `X`.

X) Other (describe audit/retention requirements).

[Answer]:A

### Question 7 — Policy backup and recovery

What evidence is required before future Ranger policy changes?

A) Export and protect the Ranger service definition and policy state before test mutations; verify restore in isolated state. Preserve existing StarRocks/HMS/RustFS data and volumes; no RPO/RTO or production rollback automation commitment. **(Recommended)**

B) Define Ranger database backup frequency, RPO/RTO, restore drill, and production rollback process in `X`.

X) Other (describe preservation/recovery requirements).

[Answer]:A

### Question 8 — Version and architecture changes

How should exact-stack compatibility findings be handled?

A) Keep StarRocks 4.1.6 pinned. Evaluate Apache Ranger 2.9.0 as a candidate because it is currently listed as stable, but pin Ranger and all StarRocks plugin/service-definition artifacts only after exact compatibility evidence. Any StarRocks/Ranger version, gateway, authorization-service, or plugin architecture change requires explicit approval. **(Recommended)**

B) Approve a specific Ranger/StarRocks version change or additional authorization component now; state the exact scope and compatibility evidence in `X`.

X) Other (describe change policy).

[Answer]:A

### Question 9 — Isolation of verification

Where may Unit 5 NFR/Build tests run?

A) Only on isolated FreeIPA/Ranger test state, disposable StarRocks FE/BE volumes, and synthetic tables/objects. Do not connect experimental Ranger/UserSync to production FreeIPA, RustFS production, or existing StarRocks volumes. **(Recommended)**

B) Identify a production-connected test boundary and its safeguards in `X`.

X) Other (describe the test boundary).

[Answer]:A

## Approval gate

Complete the NFR answers and approve the generated NFR Requirements and technology decisions before Unit 5 NFR Design. This plan authorizes documentation only. It does not authorize package installation, image builds, Compose/network changes, Ranger service creation, StarRocks SQL grants, FreeIPA membership edits, credential/keytab changes, service operations, production policy changes, or data/workspace changes.

## Answers and completion

The user completed the plan with the recommended answers A/A/A/A/A/A/A/A/A. The NFR specification and technology decisions are generated for review. No SLA, HA/RTO/RPO, hard revocation bound, or production audit-retention commitment was added. Ranger 2.9.0 remains an evaluation candidate; exact compatibility with StarRocks 4.1.6 is not established.

## Source references

- [StarRocks Ranger integration](https://docs.starrocks.io/docs/administration/user_privs/authorization/ranger_plugin/)
- [Apache Ranger downloads](https://ranger.apache.org/download.html)
