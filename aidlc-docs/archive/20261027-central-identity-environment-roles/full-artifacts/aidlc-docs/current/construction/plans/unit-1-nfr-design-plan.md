# Unit 1 NFR Design Plan — FreeIPA Identity Foundation

## Approved Baseline

The approved NFR Requirements define a small local Compose identity set, no authentication performance SLA, single-host best-effort availability, fail-closed dependent authentication, localhost-only published ports, validated LDAP TLS, protected keytabs/secrets, persistent FreeIPA state, operator-created protected pre-cutover backups, readiness reporting, pinned versions, and rollback on critical identity/service failures. FreeIPA replaces the MIT KDC in `LAKEHOUSE.LOCAL`; service keytabs are reissued while the writer's RustFS S3 key remains unchanged.

## Design Checklist

- [x] Trace each design pattern to approved `IPA-NFR-01` through `IPA-NFR-10`.
- [x] Define isolated FreeIPA validation, readiness probes, and fail-closed outage behavior.
- [x] Define TLS trust distribution and credential mount protection without selecting implementation paths prematurely.
- [x] Define persistence, pre-cutover backup, cutover evidence, and coordinated rollback patterns.
- [x] Define version pinning, sanitized observability, and local-only operating boundaries.
- [x] Assess scalability, availability, performance, reliability, security, and maintainability against the PoC scope.
- [x] Generate `construction/unit-1/nfr-design/nfr-design-patterns.md` and `logical-components.md`.
- [x] Present NFR Design for explicit approval before Unit 1 Infrastructure Design.

## Design Boundaries

- No HA, replication, external monitoring, scheduled backup service, or production SLO is introduced.
- Exact FreeIPA image/version, realm/DNS integration, certificates, ports, volume/mount paths, backup commands, and healthcheck command are implementation decisions for Infrastructure Design.
- No KDC, credential, service, bucket, or data state is modified in NFR Design.
- Build and Test will verify the implemented health checks, restart persistence, TLS validation, permissions, backup/restore procedure, and cutover/rollback behavior.

## Approval Gate

Review and approve the NFR Design artifacts before proceeding to Unit 1 Infrastructure Design.
