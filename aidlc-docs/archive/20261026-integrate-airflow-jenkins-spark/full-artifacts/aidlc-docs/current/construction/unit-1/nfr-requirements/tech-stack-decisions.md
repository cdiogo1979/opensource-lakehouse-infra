# Technology Stack Decisions — Unit 1 Spark Writer Runtime

## Selected Stack

| Concern | Decision | Rationale / constraint |
|---|---|---|
| Lifecycle orchestration | Existing Bash Spark entrypoint (`infra/spark/entrypoint.sh`) | User selected reuse of the current runtime boundary; avoids a new helper service or language runtime. |
| Kerberos operations | `kinit`/`klist` from Debian `krb5-user` in a local image derived from the pinned Spark base digest | The base image does not contain Kerberos client commands; the user approved this single-package image change on 2026-10-26. |
| Spark runtime | Existing Spark master/worker/history-server service and image | Preserve the single existing local Spark service; do not introduce another execution cluster. |
| Credential cache | Private service-local runtime cache | Keep separate from Airflow driver and notebook caches and outside persistent data/bundle paths. |
| RustFS credentials | Existing read-only file-backed writer credentials | S3 identity remains distinct from the Kerberos principal and TGT. |
| Readiness reporting | Docker health status plus sanitized service logs | Local PoC operator visibility; health is informational while Spark worker admission enforcement is handled at the Spark service boundary. |

## Dependency Policy

- Do not add a standalone credential sidecar/helper service or any runtime package beyond the user-approved Debian `krb5-user` addition.
- Build and Test must confirm Bash, `kinit`, and `klist` exist in the derived Spark image and handle output without leaking credentials.
- Do not add external monitoring, a new credential store, a new principal, or a new secret-rotation flow.
- Any container health check or Spark worker admission mechanism is an implementation of the approved requirement, not an additional monitoring platform.

## Deferred Decisions

- NFR Design specifies the concrete cache creation, file/volume mount modes, renewal process coordination, and Spark admission-control mechanism.
- Infrastructure Design verifies Compose mount ownership, startup order, service health semantics, Spark master advertisement, DNS, and executor connectivity.
- Build and Test verifies tool availability and ensures health status and Spark admission behavior match SWR-NFR-01 through SWR-NFR-06.
