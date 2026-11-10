# NFR Requirements — FreeIPA Identity Foundation

## Scope and Assumptions

These requirements cover FreeIPA identity and Kerberos operation and the staged replacement of the MIT KDC in the local Docker Compose proof of concept. They do not define production availability, disaster recovery, external monitoring, or throughput targets. RustFS IAM, JupyterHub runtime credential delivery, Hive/Spark authorization, and Ranger/StarRocks authorization retain their separate unit boundaries.

The approved functional baseline is FreeIPA as the sole Kerberos/LDAP authority after cutover in `LAKEHOUSE.LOCAL`. Service keytabs are reissued; the writer's RustFS S3 access key, production data, and admin privilege mapping are preserved. The old MIT KDC and corresponding keytabs are protected rollback material until cutover acceptance.

## Quality Requirements

| ID | Category | Requirement | Verification evidence |
|---|---|---|---|
| IPA-NFR-01 | Capacity | Support the fixed local PoC identity set: `developer-user`, `analyst-user`, `admin`, `write-service-account`, required component principals, and a small operator-managed set. No horizontal scaling or identity-growth objective is required. | Provision and resolve every required identity and group in the local Compose environment. |
| IPA-NFR-02 | Performance | No hard LDAP login, lookup, or Kerberos ticket latency SLA or benchmark is required. Operations must complete correctly under the supported local PoC setup. | Functional authentication and ticket checks; report observed failures without claiming a performance SLA. |
| IPA-NFR-03 | Availability | FreeIPA is a single-host, best-effort service with no HA, failover, or RTO guarantee. When the directory/KDC is unavailable, dependent authentication and new identity changes fail closed; no fallback may silently broaden access. | Stop or isolate FreeIPA in a controlled verification environment and confirm dependent identity checks reject/withhold access rather than grant broader access. |
| IPA-NFR-04 | Network security | FreeIPA endpoints remain on the Compose network. Only required administration/authentication ports may be published, bound to localhost. LDAP clients validate the FreeIPA TLS certificate and trust chain. | Inspect Compose bindings and verify client TLS certificate validation; reject an untrusted or mismatched certificate. |
| IPA-NFR-05 | Credential protection | Credential directories use owner-only access (`0700`) and keytab/secret files use owner read/write only (`0600`) where host filesystem semantics permit. Credential material is mounted read-only into consumers where possible and never emitted in logs, command output, or generated artifacts. | Inspect effective ownership/modes and mounts; scan representative logs and diagnostics for secret/ticket contents. |
| IPA-NFR-06 | Persistence and recovery | FreeIPA state survives ordinary container stop/start and recreation using persistent storage. Before cutover, an operator creates protected backups of FreeIPA state and the MIT KDC database plus matching old keytabs. Retain these rollback materials until cutover is accepted. No automated backup schedule or retention SLA is required. | Restart/recreate FreeIPA and verify identities/principals remain; inspect backup checklist and verify protected rollback material exists before cutover. |
| IPA-NFR-07 | Readiness and observability | Provide an operator-readable readiness result covering LDAP availability, Kerberos ticket acquisition, and required principal/consumer checks. Cutover status distinguishes blocked, accepted, and rolled back. Errors identify a sanitized failure category and never expose passwords, keytabs, access keys, tickets, or bind credentials. | Exercise ready and failure cases; inspect status and logs for actionable sanitized output. |
| IPA-NFR-08 | Version management | Pin FreeIPA and relevant Kerberos/LDAP client image versions. Floating `latest` tags are prohibited. Any compatibility-driven change to the existing realm/client stack is documented and reviewed before implementation. | Inspect image and dependency references; confirm all versions are explicit and the compatibility rationale is recorded. |
| IPA-NFR-09 | Cutover reliability | Cutover is blocked until preflight verifies required principals, FreeIPA-issued keytabs, TLS/LDAP, and dependent service authentication. Roll back if a critical required principal cannot acquire/validate a ticket or a dependent service cannot authenticate during the agreed verification window. There is no fixed elapsed-time limit. | Maintain a cutover evidence checklist with each principal/service result and a recorded go/no-go or rollback decision. |
| IPA-NFR-10 | State integrity | The writer's RustFS S3 access key, existing production objects, and admin privilege mapping remain unchanged by FreeIPA/Kerberos migration. Old and new KDC databases for the same realm must never be co-authoritative. | Compare pre/post RustFS key references and production object inventory; verify only one KDC authority is active after each cutover/rollback decision. |

## Traceability

- Functional identity and group lifecycle: `construction/unit-1/functional-design/business-logic-model.md`, `business-rules.md`.
- Credential distinction and keytab rollover: IPA-NFR-05, IPA-NFR-06, IPA-NFR-09, IPA-NFR-10.
- Failure, readiness, and rollback behavior: IPA-NFR-03, IPA-NFR-06, IPA-NFR-07, IPA-NFR-09.
- Approved requirements: Identity source and integration requirements; Migration and safety constraints; Verification acceptance criteria.
- Approved NFR answers: A/A/A/A/A/A/A/A in `construction/plans/unit-1-nfr-requirements-plan.md`.

## Applicability

- High availability, disaster recovery objectives, automated backups, external alerting, and numeric authentication performance are out of scope for this local PoC.
- The security and failure-handling requirements above are explicit and remain mandatory despite the absence of an expanded security/resiliency baseline.
- Property-based testing is not mandated by NFR planning; reassess for applicable pure functions during implementation.
- No implementation, test, or runtime operation is authorized by this NFR requirements artifact.
