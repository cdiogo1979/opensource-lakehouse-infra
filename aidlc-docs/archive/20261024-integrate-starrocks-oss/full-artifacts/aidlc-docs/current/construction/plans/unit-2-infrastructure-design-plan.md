# Unit 2 Infrastructure Design Plan — StarRocks Runtime

## Unit Context

Map the approved StarRocks FE/BE runtime and NFR components onto the existing local Docker Compose platform. The design will preserve all existing services, named volumes, credentials, Hive metadata, RustFS objects, and notebook state.

Approved infrastructure constraints:

- Local Docker Compose deployment; one FE and one BE, with fixed settings in Compose and no automatic scaling.
- New persistent named volumes for FE and BE state. Preserve them across restarts/recreates; no automatic repair or deletion.
- One startup preflight/init coordinator validates both state locations and gates FE/BE startup. Paired-empty first initialization is allowed; one-sided empty or invalid/incompatible state fails safely.
- Each FE/BE receives its own read-only keytab, memory-backed temporary Kerberos cache, and periodic in-container `kinit -kt` refresh task. TGT caches are not persisted.
- Reuse the existing internal `iceberg_net` and service DNS. Publish only approved FE SQL/UI endpoints on loopback; do not publish internal FE/BE or infrastructure ports.
- Use Compose stdout/stderr and logs; add no monitoring/logging service. No queue or asynchronous messaging component is part of the design.
- Select a compatible StarRocks release and pin FE/BE to the same immutable image digest after checking the current official release and image guidance against this stack. A moving `latest` tag is not an acceptable final pin.

## Infrastructure Design Tasks

- [x] Map FE, BE, per-node ticket refresh, readiness checks, persistent storage, and paired-state preflight to Compose services, images, mounts, and dependencies.
- [x] Resolve whether StarRocks joins the default Compose startup or uses an opt-in profile — answer A, opt-in `starrocks` profile.
- [x] Resolve how the in-container Kerberos refresh task is packaged and supervised alongside the StarRocks FE/BE processes — answer A, derived images from pinned official bases with Kerberos tools and cron.
- [x] Resolve how the paired-state coordinator is invoked and how it gates FE/BE startup while preserving both data volumes on failure — answer A, one-shot Compose service with successful-completion dependency; a startup wrapper forces a fresh check on each invocation.
- [x] Validate a candidate release/image digest and required ports/configuration against official StarRocks guidance and existing local configuration. Exact stack compatibility remains an integrated verification gate.
- [x] Record deployment, compute, storage, messaging, networking, monitoring, and shared-infrastructure applicability, including non-applicable categories and rationale.
- [x] Generate `construction/unit-2-starrocks-runtime/infrastructure-design/infrastructure-design.md` and `deployment-architecture.md`.
- [x] Validate consistency with approved Functional Design, NFR Requirements, and NFR Design; present artifacts for explicit approval.
- [x] Record approval and advance to Unit 2 Code Generation Planning — user approved Infrastructure Design with “approve and continue”.

## Questions

Fill each `[Answer]:` line with an option letter. Choose the last option, `Other`, and describe your choice if none of the listed options fits.

### Question 1 — Compose activation and shared resource use

How should StarRocks participate in normal Compose startup?

A) Put FE, BE, and the paired-state coordinator in an opt-in `starrocks` Compose profile. Start the rest of the existing platform normally, and explicitly enable this profile when using StarRocks.

B) Include FE, BE, and the coordinator in the default Compose startup so `docker compose up` starts the full platform.

C) Use a separate Compose file/project for StarRocks, with explicit connections to the existing platform network and services.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 2 — Per-node image customization and ticket refresh

The approved design requires a periodic refresh task inside each FE and BE container. Which packaging/supervision approach should Infrastructure Design use?

A) Build small FE and BE images from the same pinned official StarRocks release images, adding the Kerberos client and a cron scheduler; run periodic `kinit -kt` from cron and start the original StarRocks process using the image's supported startup command.

B) Build small FE and BE images from the same pinned official StarRocks release images, adding only required Kerberos tooling; use a lightweight supervised shell refresh loop alongside the StarRocks process, without installing cron.

C) Build derived FE/BE images that use cron plus a small wrapper to supervise both cron and the original StarRocks process; keep each node's ticket cache private to its own container.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 3 — Paired-state preflight deployment

How should the single coordinator validate the FE/BE volumes before either StarRocks node starts?

A) Add a one-shot Compose coordinator service that mounts only the new FE and BE data volumes, validates both as a pair, exits nonzero on unsafe state, and gates FE/BE using Compose's successful-completion dependency. Keep initialization limited to a genuinely empty pair.

B) Run one host wrapper that starts a short-lived helper container to check both volumes and then starts FE/BE only after success.

C) Require the operator to run a one-shot preflight helper explicitly and, after it succeeds, start FE/BE with a separate Compose command.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

## Applicability Notes

- **Deployment Environment:** Cloud and production target selection do not apply; the approved target is this local Compose project. Question 1 resolves whether the StarRocks services are opt-in or part of default startup.
- **Compute:** The fixed one-FE/one-BE topology and operator-managed Compose settings are approved. Question 2 selects derived official images with Kerberos tools and cron. No fixed host resource budget or autoscaling is introduced; resource guidance will be measured and documented during integrated verification.
- **Storage:** New FE and BE named volumes are required and must remain independent of all existing data. Question 3 selects a read-only one-shot Compose preflight coordinator; the implementation must not mutate the state volumes or other volumes.
- **Messaging:** Not applicable. The approved design has no queue or asynchronous work broker.
- **Networking:** Reuse `iceberg_net` and existing service DNS. Host SQL/UI endpoints remain loopback-only; internal StarRocks, KDC, Hive Metastore, and RustFS ports remain unpublished. No load balancer or API gateway is needed for this local PoC.
- **Monitoring:** Not applicable as new infrastructure. Use container health/readiness and Compose logs as already approved; add no metrics, alerting, or log-collector service.
- **Shared Infrastructure:** Reuse the existing Compose project/network and required KDC, Hive Metastore, and RustFS dependencies. New FE/BE volumes and credentials are StarRocks-specific. Do not recreate, rename, or remove existing services, volumes, identities, or data.
- **Release and images:** Official release and image sources identify 4.1.6 and immutable FE/BE multi-platform index digests; these are the design candidate. FE and BE use the same release. Exact compatibility with the local stack remains an integrated verification gate, and no unpinned `latest` reference may remain in the final configuration.

## Review Boundary

This plan resolves infrastructure design questions only. Do not edit Compose runtime configuration, build images, start/stop services, modify data, or run tests until Infrastructure Design is approved and Code Generation is authorized.

## Answer Review and Research

- **Q1 A:** FE, BE, and preflight use the opt-in `starrocks` profile; default Compose startup remains unchanged.
- **Q2 A:** Build FE/BE images from the same-version official StarRocks bases with Kerberos client utilities and cron; run the supported StarRocks startup command.
- **Q3 A:** Use one one-shot Compose preflight service, read-only access to only the two StarRocks volumes, and `service_completed_successfully` dependencies. The documented startup wrapper reruns the preflight for each StarRocks start, then starts FE/BE only after success.
- **Release evidence:** StarRocks 4.1.6 is the latest 4.1 patch in the official release notes checked 2026-10-24. The matching official FE and BE 4.1.6 images expose multi-platform index digests. The official Hive Catalog guide requires `kinit -kt` on each FE/BE with periodic cron refresh and Java Kerberos configuration; the official Iceberg Compose guide documents separate FE/BE Ubuntu images and frontend endpoint ports.
- **Compatibility limitation:** Official documentation does not certify this exact Hive Metastore 3.1.3, KDC, Iceberg, and RustFS combination. The pinned candidate must pass the approved integrated compatibility gate before the integration is considered complete.
