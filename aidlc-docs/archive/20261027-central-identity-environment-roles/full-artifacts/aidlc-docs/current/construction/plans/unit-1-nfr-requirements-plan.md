# Unit 1 NFR Requirements Plan — FreeIPA Identity Foundation

## Unit and Approved Functional Baseline

Unit 1 makes FreeIPA the LDAP directory and Kerberos authority for `LAKEHOUSE.LOCAL`, after isolated validation and staged replacement of the standalone MIT KDC. Service keytabs, including the writer keytab, are reissued under FreeIPA; the writer's RustFS S3 access key, production objects, and platform administrator privilege mapping are preserved. Group membership is authoritative in FreeIPA; RustFS and Ranger are independent consumers. The MIT KDC and matching old keytabs are retained only as protected rollback material until acceptance.

The approved scope is a local Docker Compose proof of concept. No production uptime, high availability, disaster recovery, user-count growth, or throughput target has been specified. This stage defines measurable quality requirements for identity service operation and the KDC cutover without expanding into RustFS policy, Jupyter runtime, Hive/Spark authorization, or Ranger/StarRocks implementation.

## NFR Assessment Checklist

- [x] Review Unit 1 Functional Design and trace its identity, keytab, directory-consumer, fail-closed, audit, and rollback behavior.
- [x] Confirm identity scale and performance expectations for the local PoC.
- [x] Confirm availability and recovery posture, including cutover rollback bounds.
- [x] Confirm network exposure, TLS validation, credential protection, and audit requirements.
- [x] Confirm FreeIPA state persistence and backup expectations before cutover.
- [x] Confirm health reporting and failure visibility for dependent service operators.
- [x] Confirm pinned-version and dependency-change expectations.
- [x] Check answers for ambiguity; answers A/A/A/A/A/A/A/A are consistent with the approved Functional Design.
- [x] Generate `construction/unit-1/nfr-requirements/nfr-requirements.md` and `tech-stack-decisions.md`.
- [x] Validate traceability and present NFR Requirements for approval before Unit 1 NFR Design.

## Assessment Boundaries

- **Scale and performance**: No numeric user, authentication-rate, or latency target exists. Establish a small fixed local PoC boundary unless the user supplies measured targets.
- **Availability and recovery**: FreeIPA is a critical identity dependency, but this Compose environment has no HA target. Define how operators detect an outage, keep access fail-closed, and restore or roll back the KDC transition.
- **Security**: LDAP clients use TLS with certificate validation; credentials and keytabs remain protected and secret-safe. Requirements must distinguish the writer Kerberos keytab from its preserved RustFS S3 key.
- **Persistence and backup**: FreeIPA directory/Kerberos state must survive ordinary container restarts. Decide whether a manual protected backup is required before cutover and how rollback material is retained.
- **Reliability**: Unknown users/groups, failed LDAP/Kerberos checks, incomplete consumer sync, or uncertain cutover state cannot grant access. Do not use independent same-realm MIT and FreeIPA KDCs as co-authorities.
- **Observability**: Operators need readiness and sanitized error status for LDAP/Kerberos authentication and cutover verification; no secret values, ticket contents, or keytab material in logs.
- **Maintainability**: Prefer pinned images and existing Compose/scripts; no new monitoring, backup, or orchestration service unless specifically approved.
- **Property-based testing**: Not applicable at NFR planning unless later implementation adds pure serialization or policy functions that warrant it.

## Questions

Choose an option for each question. The recommended options match the approved local PoC scope. If none fit, select `X` and describe the desired target.

### Question 1 — Supported identity scale

What scale should the FreeIPA foundation support?

A) The fixed local PoC: `developer-user`, `analyst-user`, `admin`, `write-service-account`, required component principals, and a small operator-managed set; no horizontal or growth target. **(Recommended)**

B) A growing configurable user and service-principal set; provide the expected initial count and growth rate in `X`.

X) Other (describe the identity counts and growth expectation).

[Answer]:A

### Question 2 — Authentication performance

What authentication latency requirement applies?

A) Functional correctness only; no hard login, LDAP lookup, or Kerberos ticket latency SLA for this local PoC. **(Recommended)**

B) Set a measured target for LDAP login and Kerberos ticket acquisition; provide percentile and load assumptions in `X`.

X) Other (describe the target).

[Answer]:A

### Question 3 — Availability and outage recovery

What availability posture applies to FreeIPA?

A) Single-host best effort with no HA/failover or RTO guarantee. Dependent authentication fails closed while FreeIPA is unavailable; the operator restores service using documented local recovery steps. **(Recommended)**

B) Define a recovery time, recovery point, or availability objective in `X`.

X) Other (describe the target).

[Answer]:A

### Question 4 — Exposure and credential protection

Which minimum security posture should apply?

A) Keep FreeIPA endpoints on the Compose network and publish only required administration/authentication ports to localhost; require validated TLS for LDAP clients; protect credential directories as owner-only and secret/keytab files as owner-read/write-only (`0700`/`0600`); redact credentials and tickets from logs. **(Recommended)**

B) Expose selected services beyond localhost; specify the network boundary, certificate trust, and additional controls in `X`.

X) Other (describe port exposure, TLS, file ownership/modes, and redaction requirements).

[Answer]:A

### Question 5 — State persistence and pre-cutover backup

What persistence/backup requirement applies to the FreeIPA state and old MIT rollback state?

A) Persist FreeIPA state across ordinary container recreation and require an operator-created, protected backup of FreeIPA state plus the existing MIT KDC database/keytabs before cutover. Keep the backup until acceptance; no automated backup service or retention SLA. **(Recommended)**

B) Add automated, scheduled, encrypted backups with an explicit retention and restore objective; define values in `X`.

X) Other (describe persistence, backup method, and retention).

[Answer]:A

### Question 6 — Readiness and failure visibility

How should identity availability and cutover failure be exposed?

A) Provide an LDAP/Kerberos readiness check and concise operator-readable status for each critical principal/consumer; distinguish blocked, accepted, and rolled-back cutover states; never print credential material. **(Recommended)**

B) Use sanitized startup and verification logs only, without a dedicated readiness signal.

X) Other (describe status and diagnostic requirements).

[Answer]:A

### Question 7 — Version and dependency policy

How should FreeIPA versions and supporting dependencies be managed?

A) Pin the FreeIPA image and relevant client versions; no floating `latest` tags. Any compatibility-driven version change to the existing realm/client stack is documented and reviewed before implementation. **(Recommended)**

B) Allow floating image tags and automatic upgrades in this local PoC.

X) Other (describe version pinning and upgrade policy).

[Answer]:A

### Question 8 — Cutover rollback bound

What should trigger rollback during KDC cutover?

A) Roll back if any critical required principal cannot obtain/validate its FreeIPA ticket or any dependent service cannot authenticate during the agreed verification window. No strict elapsed-time target; retain the old KDC and matching keytabs until all service checks pass. **(Recommended)**

B) Set a maximum cutover/verification window and require rollback once it expires; provide the duration in `X`.

X) Other (describe go/no-go criteria and time bound).

[Answer]:A

## Approval Gate

Answers A/A/A/A/A/A/A/A are complete, internally consistent, and recorded in the NFR artifacts. Review and approve those artifacts before Unit 1 NFR Design.
