# NFR Design Patterns — FreeIPA Identity Foundation

## Context

FreeIPA becomes the sole LDAP/Kerberos authority for `LAKEHOUSE.LOCAL` after isolated validation and staged replacement of the current MIT KDC. The system is a local, single-host Docker Compose PoC with a fixed small identity set. It has no HA, latency SLA, automated backup service, or production recovery objective. The writer's Kerberos keytab is reissued, but its RustFS S3 key, production objects, and admin privilege mapping are preserved.

## Availability and Failure Containment

- Run one authoritative directory/KDC at a time. During isolated validation, FreeIPA and MIT must not serve the same principals as co-authoritative KDCs.
- Authentication and group lookup fail closed when FreeIPA is unavailable or the TLS connection cannot be validated. No local fallback account or stale group snapshot may grant broader access.
- Keep already-issued valid Kerberos tickets subject to their normal lifetime; block new authentication/ticket acquisition when FreeIPA is unavailable. Component-specific active-session handling remains with the owning unit.
- Treat FreeIPA as a hard dependency for new identity changes and reconciliation. Failed lookups or incomplete consumer synchronization produce a failed status, not a partial-success grant.
- No automatic failover is provided. Recovery is operator-directed: restore FreeIPA state or use the documented coordinated rollback to the MIT KDC and matching old keytabs.

## Readiness and Observability

- Separate container liveness from identity readiness. Liveness indicates the service process is operating; readiness verifies LDAP over validated TLS and Kerberos ticket acquisition for a designated required service principal.
- Readiness includes the critical principal/service checks required by the current cutover phase. A single successful LDAP bind is insufficient evidence that service keytabs or dependent services work.
- Report the identity state as `starting`, `ready`, `unavailable`, `cutover-blocked`, `accepted`, or `rolled-back`, with a sanitized cause category and affected principal/service name.
- Readiness failures prevent dependent identity-changing/provisioning actions from proceeding. They do not erase existing data or credentials.
- Diagnostics include timestamps, operation/correlation references, and result categories. They exclude passwords, keytab contents, ticket contents, S3 secrets, LDAP bind secrets, and raw credential-bearing command output.
- Use the existing Compose health/status and operator log surfaces; do not add a monitoring stack.

## TLS and Credential Protection

- All LDAP clients use TLS and validate the FreeIPA certificate chain and endpoint identity. Insecure LDAP or disabled certificate checks are not an acceptable fallback.
- Distribute the selected trust anchor to dependent clients as protected configuration; do not place private CA keys in client containers.
- Mount keytabs and bind credentials read-only to consumers where feasible. Use owner-only directories and files (`0700` and `0600`) on the host/runtime path where filesystem semantics permit.
- Keep service keytabs separate by principal and service. The writer keytab and RustFS S3 key remain separate inputs and separate rotation operations.
- Do not use platform `admin` for routine service principal provisioning. Use a protected scoped provisioning identity; exact privilege assignments are resolved in Infrastructure Design.
- Runtime failure, missing secret, invalid ownership, or invalid TLS trust prevents readiness and fails closed.

## Persistence and Backup

- Keep FreeIPA directory/Kerberos database state on persistent storage so normal container stop/start or recreation does not recreate the realm or reset principals.
- Before cutover, require an operator checkpoint containing a protected backup of FreeIPA state, the current MIT KDC database, and matching old keytabs/configuration.
- Use backup mechanisms supported by the selected FreeIPA distribution and preserve metadata/permissions. The exact commands and storage locations are decided in Infrastructure Design.
- Keep rollback material until all required principals and dependent services pass cutover verification and the operator records acceptance.
- Backup/restore errors block cutover. Do not delete, overwrite, or regenerate the existing MIT state as part of a retry.
- No scheduled backup, retention SLA, or automated disaster recovery is required.

## Cutover and Rollback Pattern

1. **Inventory**: enumerate every principal, keytab consumer, realm/DNS dependency, LDAP client, and service restart requirement.
2. **Isolated validation**: bring up FreeIPA without competing for production realm traffic; validate TLS, identity/group lookups, principal creation, keytab acquisition, and required client compatibility.
3. **Pre-cutover checkpoint**: create and verify protected backups of both FreeIPA state and MIT rollback state. Confirm the writer's RustFS S3 key reference and production object inventory are unchanged.
4. **Go/no-go**: proceed only when required service principals/keytabs and dependent-service checks are ready, the operator has a rollback path, and the maintenance/cutover procedure is explicit.
5. **Authority switch**: make MIT unavailable as the active authority, activate FreeIPA for the existing realm, install FreeIPA-issued keytabs to their assigned consumers, and restart/reload consumers in the documented order. Do not split clients between independent databases.
6. **Verification**: confirm LDAP TLS, Kerberos TGT/service-ticket acquisition, HMS/Spark/Airflow/StarRocks authentication as applicable, and readiness for required consumers. Capture sanitized evidence.
7. **Accept or rollback**: accept only if all critical checks pass. On any critical principal or service-authentication failure, stop forward rollout and restore the MIT authority together with its matching old keytabs/configuration.

No fixed time bound applies to this local PoC. Cutover remains blocked until all critical checks pass or rollback is completed.

## Version and Change Management

- Pin FreeIPA and LDAP/Kerberos client versions; do not use floating `latest` references.
- Record compatibility evidence for FreeIPA realm behavior, clients, and existing service integrations before selecting final versions.
- Any compatibility change to existing client images, realm settings, or service configuration is reviewed before implementation.
- A version update is a deliberate change with renewed compatibility verification, not an implicit image pull.

## Quality Attribute Assessment

| Attribute | Design response |
|---|---|
| Availability | Single-host, best effort; no HA. Fail closed and recover manually. |
| Reliability | Readiness and preflight checks gate provisioning and cutover. Coordinated rollback restores a matching authority/keytab set. |
| Security | Validated LDAP TLS, least privilege, per-principal read-only keytab mounts, restrictive permissions, and secret-safe diagnostics. |
| Performance | No latency/throughput SLA. Readiness probes must remain lightweight and bounded by their implementation timeouts. |
| Scalability | Fixed PoC identity set; no horizontal scaling requirement. |
| Maintainability | Pinned versions, explicit principal/consumer inventory, operator-readable state, and documented recovery. |

## Deferred Infrastructure Decisions

Exact image/version, hostname and DNS strategy, TLS certificate and trust distribution, port bindings, volume and secret paths, scoped FreeIPA provisioning privileges, supported backup command, readiness command, and consumer restart order are intentionally deferred to Infrastructure Design.
