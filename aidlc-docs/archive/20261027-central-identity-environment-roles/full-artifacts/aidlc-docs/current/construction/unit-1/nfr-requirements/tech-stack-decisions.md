# Technology Stack Decisions — FreeIPA Identity Foundation

## Approved Constraints

| Area | Decision | Rationale / boundary |
|---|---|---|
| Directory and KDC | Use a pinned FreeIPA image as the LDAP directory and Kerberos KDC for `LAKEHOUSE.LOCAL` after staged cutover. | User selected same-realm MIT KDC replacement. The two independent KDC databases are not co-authoritative. Exact image compatibility is confirmed during Infrastructure Design. |
| Existing MIT KDC | Retain its persistent state and matching old keytabs as protected rollback material until cutover acceptance. | Enables coordinated rollback without deleting existing state; it is not a second steady-state authority. |
| LDAP client transport | LDAP over TLS with certificate and trust-chain validation. | Prevents clear-text directory credentials and rejects untrusted endpoints. Certificate issuance and mount paths are Infrastructure Design decisions. |
| Identity/configuration | Extend existing Docker Compose and project scripts for this local PoC; do not add a separate orchestration framework. | Preserves the existing operating model and keeps scope contained. |
| Credential delivery | Use protected file-backed secret references/mounts for keytabs and bind credentials; apply owner-only file/directory permissions and read-only consumer mounts where possible. | Keeps secrets out of ordinary environment values, source, and logs. Exact secret storage and mount implementation is decided in Infrastructure Design. |
| Service principal provisioning | Provision FreeIPA service principals using a dedicated, protected identity with only required principal/keytab management privileges. Do not reuse the MIT `kadmin/provisioner` keytab or use an unrestricted admin credential for routine automation. | Separates authority and limits provisioning impact. Exact FreeIPA privilege model and workflow are decided in Infrastructure Design. |
| RustFS writer credential | Preserve the existing RustFS S3 access key and secret; reissue only its Kerberos keytab. | The S3 and Kerberos authentication mechanisms are independent. |
| Health/readiness | Implement a FreeIPA/consumer readiness signal and sanitized operator diagnostics using the existing local health/status mechanisms where feasible. | No additional monitoring stack is approved. Concrete check command and Compose healthcheck are decided in Infrastructure Design. |
| Backups | Use an operator-triggered protected backup of FreeIPA and MIT rollback state before cutover; no scheduled backup service. | Matches the approved local PoC and recovery answer. Exact FreeIPA backup/restore mechanism must use the selected image's supported tooling and is decided during Infrastructure Design. |
| Versioning | Pin FreeIPA and client versions; avoid floating image tags. | Reproducible local deployment and explicit compatibility review. Exact versions are chosen after image and client compatibility discovery. |

## Deferred Decisions

- Exact FreeIPA image and Kerberos/LDAP client versions and compatibility evidence.
- Compose network aliases, published localhost ports, volumes, certificate authority distribution, and TLS certificate lifecycle.
- FreeIPA bootstrap/admin provisioning flow and scoped service-principal management privileges.
- Supported backup/restore procedure and protected file locations.
- Principal/keytab rollout sequence and service restart order for cutover and rollback.
- Concrete LDAP/Kerberos readiness check and failure reporting mechanism.

These decisions belong in Unit 1 NFR Design and Infrastructure Design. They must preserve the approved NFR requirements and not introduce a co-authoritative KDC or rotate the writer's RustFS S3 key.

## Change Control

Any proposed floating version, external network exposure, automated backup service, HA architecture, new orchestration framework, or writer S3-key rotation requires review against the approved scope before implementation.
