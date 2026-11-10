# Unit 3 NFR Requirements Plan — Hive Metastore and Direct Spark Authorization

## Unit and Approved Functional Baseline

Unit 3 defines direct Spark data authorization through RustFS object requests. The user accepts cross-environment Hive Metastore metadata visibility. The role matrix, environment locations, and fail-closed rules are in `construction/unit-3/functional-design/`. Production stays in `lake`; development (including `lhdev*`) uses `lake-dev`; UAT uses `lake-uat`. Developer reads all and writes dev only; analyst reads prod only and cannot write; `write-service-account` reads/writes all three; the existing `admin` mapping is preserved. Analyst metadata DDL restrictions are not established by this design.

The scope is the local Docker Compose proof of concept. This stage sets measurable quality requirements for HMS and direct Spark authorization; it does not change policy, role permissions, credentials, configuration, or runtime state. Ranger/StarRocks authorization, JupyterHub credential delivery, FreeIPA cutover, and final replacement of `user_a`/`user_b` remain outside Unit 3.

**Known architecture limitation:** Apache Hive storage-based authorization uses filesystem permission checks, while Hadoop documents that S3A reports stub file/directory permissions and does not enforce access from those stubs. Metadata visibility is accepted. Verification must establish real Spark object read/write denial through matching RustFS role credentials.

## NFR Assessment Checklist

- [x] Review approved Unit 3 Functional Design and record the S3A/HMS authorization capability risk.
- [x] Inspect existing service topology and identity boundaries without changing runtime state.
- [x] Confirm supported identity/database/table scale and expected concurrent Spark clients: A.
- [x] Confirm response-time targets or select correctness-only behavior with bounded timeouts: A.
- [x] Confirm availability, fail-closed behavior, and recovery expectations for HMS, KDC/FreeIPA, and RustFS outages: A.
- [x] Confirm authorization cache and role-revocation propagation requirements: A.
- [x] Confirm credential protection, transport, and identity isolation requirements for human and ETL Spark contexts: A.
- [x] Confirm audit fields, retention, and sensitive-data exclusions: A.
- [x] Confirm preservation/backup and rollback evidence required before any future metadata/location change: A.
- [x] Confirm pinned-version compatibility policy and whether additional authorization services/dependencies are allowed: A.
- [x] Complete answers and ensure no conflict with the approved functional matrix or architecture gate.
- [x] Generate `construction/unit-3/nfr-requirements/nfr-requirements.md` and `tech-stack-decisions.md` for review before Unit 3 NFR Design.

## Assessment Boundaries

- **Scale/performance**: The PoC has three buckets and a small set of named human/service identities. No throughput or latency target is currently approved.
- **Availability/recovery**: HMS, identity services, and RustFS are dependencies. Failure must not trigger use of broader credentials or permit access by default.
- **Revocation/consistency**: FreeIPA membership and RustFS policies may change at different times. Define how quickly a removed role or revoked identity must stop authorizing new requests; characterize ticket and metadata caches.
- **Security**: Kerberos principal and RustFS S3 identity are independent. Human sessions must not receive the ETL writer's credentials. Logs must not expose passwords, keys, keytabs, ticket contents, or data.
- **Auditability**: Record enough context to explain allow/deny decisions by layer without exposing sensitive identity material or object contents.
- **Preservation/recovery**: Existing production data and database locations must remain intact. Any future implementation touching HMS metadata, database locations, or auth policy needs a reviewed pre-change state and isolated recovery plan.
- **Compatibility**: Keep the pinned Hive, Spark, Iceberg, Hadoop/S3A, RustFS, FreeIPA/Kerberos versions unless tests identify a required change and the user approves it.
- **Verification**: Functional allow/deny rules come from the approved design. NFRs add boundedness, revocation, resilience, evidence quality, and preservation checks.

## Questions

Choose an option for each question. Option A is recommended for this local proof of concept. Choose `X` and describe the requirement if none fits.

### Question 1 — Scale and concurrency

What scale should direct HMS/Spark authorization support?

A) Fixed local PoC: approved identities, three environments, current database/table inventory, and a small manually managed extension; no scale or throughput commitment. **(Recommended)**

B) Set identity/database counts, expected concurrent Spark sessions, growth, and test-load assumptions in `X`.

X) Other (describe scale and concurrency).

[Answer]:A

### Question 2 — Authorization response time

What performance target applies to HMS and RustFS authorization checks?

A) Correctness first; no end-to-end latency SLA. Apply finite connect/read/request timeouts, avoid unbounded retries, and retain sanitized elapsed-time diagnostics. **(Recommended)**

B) Specify maximum response time and concurrency/load profile in `X`.

X) Other (describe timing requirements).

[Answer]:A

### Question 3 — Dependency failure and availability

What should happen if HMS, Kerberos/FreeIPA, or RustFS is unavailable?

A) Single-host best effort with no HA/RTO guarantee. New operations fail closed; no service identity fallback or permissive stale authorization. Recovery is operator-led and must not alter existing data. **(Recommended)**

B) Define availability, RTO/RPO, retry, and recovery automation targets in `X`.

X) Other (describe availability and failure behavior).

[Answer]:A

### Question 4 — Role revocation and authorization caches

How quickly must group removal or credential revocation stop new access?

A) Do not claim immediate revocation without measurement. Bound ticket and metadata/policy cache lifetime; document the effective maximum revocation delay and test it. Stop/terminate affected interactive sessions in Unit 4. **(Recommended)**

B) Require a specific maximum revocation delay and active-session termination target in `X`.

X) Other (describe propagation expectations).

[Answer]:A

### Question 5 — Credential and network security

What minimum security posture applies to user and writer Spark requests?

A) Use each human's own Kerberos context and RustFS identity; keep the writer identity ETL-only. Protect credential files/cache with restrictive permissions and private runtime storage; keep endpoints internal; never put secrets in source, ordinary environment values, arguments, or logs. **(Recommended)**

B) Require TLS for all internal service and S3 traffic and define certificate lifecycle/trust in `X`.

X) Other (describe credential isolation and transport).

[Answer]:A

### Question 6 — Authorization audit and retention

What evidence should be retained for an HMS or RustFS decision?

A) Sanitized principal identifier, resource classification (environment/database/table), operation, enforcement layer, outcome, bounded reason, and timestamp. No secrets, ticket contents, S3 keys, object contents, or unrestricted request bodies. Keep current runtime/container logs; no retention SLA. **(Recommended)**

B) Define immutable audit destination, access roles, and retention duration in `X`.

X) Other (describe audit requirements).

[Answer]:A

### Question 7 — Pre-change preservation and recovery

What protection is required before future implementation changes to HMS metadata or location policy?

A) Require a reviewed inventory/export of affected database/table locations and authorization configuration, plus a disposable recovery rehearsal. Never automatically relocate/delete existing production objects; do not roll back over unknown state. **(Recommended)**

B) Define backup mechanism, recovery objectives, and rollback automation in `X`.

X) Other (describe preservation/recovery).

[Answer]:A

### Question 8 — Version and architecture changes

How should pinned-stack compatibility findings be handled?

A) Keep current service/dependency versions pinned. Any plugin, gateway, HiveServer2, service, or version change requires evidence and explicit architecture approval. The user accepts cross-environment metadata visibility; block implementation/cutover if the pinned stack cannot enforce the approved RustFS object scope. **(Recommended)**

B) Allow a specific named authorization component/version change; describe the allowed scope and compatibility evidence in `X`.

X) Other (describe change policy).

[Answer]:A

## Answers and completion

The user requested continuation without supplying alternate values. The plan's recommended answer A was selected for all eight questions: A/A/A/A/A/A/A/A. The NFR specification and technology decisions were generated for review. The user later accepted metadata visibility; actual Spark object authorization remains the hard functional acceptance condition.

## Approval Gate

The user selected the recommended defaults by requesting continuation. Review the generated NFR specification and technology decisions before Unit 3 NFR Design. This plan authorizes no tests, service changes, identity or policy changes, database/location changes, or production data changes.
