# Unit 2 Code Generation Plan — StarRocks Runtime

## Unit Context

- **Unit:** Unit 2 — StarRocks Runtime.
- **Story:** US-05 — Run StarRocks in the local PoC.
- **Requirements:** FR-1 and FR-7; NFR-1 through NFR-6; Unit 2 runtime requirements under `aidlc-docs/current/construction/unit-2-starrocks-runtime/`.
- **Workspace:** Brownfield Compose project at `/Users/carlosdiogo/code_repo/hive-dremio-rustfs`.
- **Dependencies:** Unit 1 approved StarRocks credential contract; existing KDC, `iceberg_net`, and Compose project. The KDC is required at runtime. Unit 3 owns the Hive Iceberg catalog, SQL accounts/roles/grants, and sample data.
- **Approved design:** `aidlc-docs/current/construction/unit-2-starrocks-runtime/{functional-design,nfr-design,infrastructure-design}/`.
- **Completion boundary:** One FE and one BE start with persistent StarRocks-only state, read-only Unit 1 credential inputs, per-node Kerberos TGT refresh, paired-state startup validation, health/readiness, loopback-only host endpoints, and operator documentation. No catalog or SQL authorization bootstrap is part of this unit.

## Approved Runtime Contracts

- Use opt-in Compose profile `starrocks`; default Compose startup remains unchanged.
- FE and BE use StarRocks 4.1.6. Pin upstream multi-platform bases by digest:
  - FE `starrocks/fe-ubuntu:4.1.6@sha256:d07aa750be77625a09866a76dbfe0ee032baeb5e48fe0e952d30cb525329dc31`.
  - BE `starrocks/be-ubuntu:4.1.6@sha256:bf0f5ca7fd9fc4e568d4d0e593e362f229b376976b513a5a549b1b922d9ec23b`.
- Build derived images with Kerberos client tools and cron. Use supported StarRocks startup scripts. No `latest` tag or unrelated image/service changes.
- Use separate Compose named volumes for FE metadata and BE storage. Never remove or silently reset them in routine operations.
- Use a one-shot Compose preflight with read-only mounts of only the two StarRocks state volumes. It passes only for a clean paired-empty initial state or recognized paired existing state; it fails closed on one-sided empty/missing or unreadable/inconsistent state. It does not write marker files or modify StarRocks or shared data.
- The supported startup wrapper runs a fresh preflight on every invocation, then starts FE/BE. Preserve a failed preflight for inspection; remove only a previous successful preflight container. Compose `service_completed_successfully` dependencies also gate FE/BE startup.
- Mount `.runtime/credentials/keytabs/starrocks.keytab`, `infra/kerberos/krb5.conf`, and the file-backed `rustfs-starrocks-secret-key` read-only. Use principal `starrocks@${KERBEROS_REALM}` and access-key ID `starrocks`; never put credential values into tracked files or logs.
- Each node has a private restrictive memory-backed `/run/krb5` TGT cache and refreshes hourly with cron. KDC ticket maximum lifetime is 10 hours. Initial `kinit` failure blocks that node's startup; scheduled failures emit only a safe status and do not stop an otherwise healthy service while the current TGT remains valid.
- Reuse `iceberg_net`. FE UI port 8030 and SQL port 9030 bind only to `127.0.0.1`. FE/BE internal ports are not host-published.
- FE and BE use named persistent state paths `/opt/starrocks/fe/meta` and `/opt/starrocks/be/storage`. FE starts before BE; BE waits for FE SQL health and idempotently registers itself if absent.
- Runtime readiness requires FE SQL and both nodes alive; it does not claim Hive catalog, RustFS query, or SQL authorization readiness.
- Exact local-stack compatibility and the locally derived image digests remain for Build and Test; do not claim these are verified during Code Generation.

## Exact Application Files

1. `docker-compose.yml` — add the opt-in `starrocks` profile, FE/BE/preflight services, pinned image build references, health checks, internal/loopback ports, read-only credentials/config, private tmpfs, new StarRocks volumes, and dependencies. Preserve all existing services, network, secrets, mounts, and volumes.
2. `infra/starrocks/fe/Dockerfile` and `infra/starrocks/be/Dockerfile` — derive from the exact pinned FE/BE 4.1.6 base digests; install the Kerberos client and cron with controlled package versions; preserve the upstream process user and supported binaries/start commands.
3. `infra/starrocks/fe/entrypoint.sh` and `infra/starrocks/be/entrypoint.sh` — set safe Kerberos environment, validate read-only credential/config paths, perform initial TGT acquisition without disclosing output, start cron, and `exec` the supported FE/BE startup command. Keep the FE/BE process as the container's main process.
4. `infra/starrocks/kerberos/refresh-ticket.sh` and `infra/starrocks/kerberos/starrocks-ticket-refresh` — implement hourly per-node `kinit -kt` refresh using the private cache; use a secret-free allowlisted status message and no raw command output.
5. `infra/starrocks/preflight/Dockerfile` and `infra/starrocks/preflight/check-paired-state.sh` — create a minimal local one-shot checker that mounts only the FE/BE data locations read-only, recognizes empty-pair and existing-pair states using release-verified markers, rejects unsafe states, and never changes volume contents.
6. `scripts/start-starrocks.sh` — inspect any prior preflight container outcome, preserve failed preflight diagnostics, remove only a previously successful preflight container, execute a fresh profile-scoped preflight, and start only StarRocks after success. Do not start/stop/recreate shared services or delete volumes.
7. `README.md` — add StarRocks profile startup, stop/restart, loopback endpoints, readiness scope, logs, first-start and paired-state behavior, ticket refresh, resource-measurement caveat, safe persistence/recovery, and the Unit 3 catalog boundary.
8. `aidlc-docs/current/construction/unit-2-starrocks-runtime/code/implementation-summary.md` — document changed application paths, credential/config contract, lifecycle, image base digests and derived image IDs/digests if available, story/requirement traceability, and verification deferred to Build and Test. Markdown documentation only under `aidlc-docs/`.

## Generation Steps

- [x] **Step 1 — Build derived runtime images (US-05, FR-1, NFR-4):** Added FE and BE Dockerfiles from the corresponding immutable 4.1.6 base digests. Kerberos and cron package versions are pinned; the official StarRocks startup path remains in use.
- [x] **Step 2 — Implement per-node Kerberos runtime (US-05, FR-5, NFR-1):** Added FE/BE entrypoints, read-only keytab and `krb5.conf` checks, initial `kinit -kt`, per-container tmpfs cache, JVM Kerberos configuration, hourly cron refresh, redacted status, and approved refresh-failure behavior.
- [x] **Step 3 — Implement paired-state preflight (US-05, FR-1, FR-7, NFR-3):** Added a preflight image/checker that permits paired-empty state or recognized FE `image/ROLE` + `image/VERSION` and BE `data/*/cluster_id` state; it fails closed on ambiguous/one-sided state and mounts both volumes read-only. Runtime verification of markers remains in Build and Test.
- [x] **Step 4 — Add opt-in Compose runtime (US-05, FR-1, FR-7, NFR-1, NFR-3, NFR-4):** Added only the `starrocks` profile services, local build contexts and digest args, two named volumes, existing internal network, dependencies, health checks, read-only credentials/config, private memory-backed caches, loopback FE UI/SQL bindings, and internal-only node ports. Catalog readiness remains outside runtime health.
- [x] **Step 5 — Implement safe startup wrapper (US-05, NFR-3, NFR-6):** Added `scripts/start-starrocks.sh` to build only StarRocks images, require the existing healthy KDC, perform a fresh read-only preflight, preserve failed preflight diagnostics, remove only a prior successful preflight container, then start FE before BE without operating shared services or removing volumes.
- [x] **Step 6 — Document operator workflow (US-05, NFR-3, NFR-5, NFR-6):** Updated README with opt-in startup, readiness limits, endpoints, refresh behavior, resource-measurement caveat, persistence, safe recovery, and Unit 3 boundary. Catalog functionality is explicitly deferred.
- [x] **Step 7 — Implementation summary and traceability (US-05):** Added `aidlc-docs/current/construction/unit-2-starrocks-runtime/code/implementation-summary.md` with changed paths, requirement mapping, credentials, base pins, runtime behavior, and compatibility checks deferred to Build and Test.
- [x] **Step 8 — Plan conformance review:** Reviewed generated paths against approved designs and US-05. No catalog/user/grant code, volume resets, unrelated service changes, secret values, floating image tags, or duplicate path copies were introduced. Image IDs/digests remain unavailable because image builds are deferred.
- [x] **Approval gate:** User explicitly approved the complete plan on 2026-10-24 before runtime code generation.

## Verification Boundary

Code Generation is complete under the approved plan. No tests, image builds, Compose validation, service lifecycle, or data operations were executed. Integrated Compose, Kerberos/HMS, RustFS/Iceberg, compatibility, and persistent-state verification remain in the separately approved Build and Test phase.

## Scope Exclusions

- Do not add the Hive Iceberg catalog, StarRocks SQL users/roles/grants, sample databases/tables, or query/write bootstrap; Unit 3 owns these.
- Do not change identity provisioning or rotate Unit 1 credentials.
- Do not modify the sibling Airflow/Jenkins project.
- Do not alter/delete existing Compose services, network, named volumes, Hive metadata, RustFS objects, KDC data, Spark/Jupyter state, or user workspaces.
- Do not add HA, additional FE/BE nodes, monitoring/logging infrastructure, queues, cloud deployment, Ranger, or a reset command.
