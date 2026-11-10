# Unit 1 Code Generation Plan — Core Runtime and Legacy Setup Removal

## Unit context

- **Unit:** Unit 1 — Runtime Composition and Legacy Removal.
- **Approved designs:** U1 Functional Design, NFR Requirements, NFR Design, and Infrastructure Design.
- **Workspace:** `/Users/carlosdiogo/code_repo/opensource-lakehouse-infra-v2`.
- **Core providers:** Keycloak, dedicated Keycloak PostgreSQL, Polaris, dedicated Polaris PostgreSQL, and RustFS.
- **Deferred services:** Airflow, JupyterHub, Jenkins, and StarRocks remain in a separate opt-in overlay and are unsupported pending migration.
- **Not in U1:** Keycloak realm/groups and OIDC issuer contract; Polaris catalog/principal/role bootstrap; RustFS buckets/policies; Spark smoke test; access matrix. These belong to U2–U4.

This plan authorizes only code generation after explicit plan approval. Do not start containers, build/pull images, run tests, create buckets/catalogs, or alter volumes during Code Generation. Build and Test owns runtime verification.

## Approved implementation contracts

- Core Compose project name is `lakehouse-local`; no fixed `container_name`; one private network; only Keycloak, Polaris, RustFS S3, and RustFS console are published on loopback; PostgreSQL and management ports stay unpublished.
- Keycloak and Polaris use separate PostgreSQL services, databases, credential files, and project-scoped named volumes. RustFS uses a new project-scoped named volume; old RustFS state remains unmounted and untouched.
- Version baseline: Keycloak 26.8.1; Polaris 1.8.0; PostgreSQL 17.11; RustFS 1.0.4. Pin immutable multi-architecture digests for Keycloak, Polaris, and PostgreSQL. RustFS remains pinned to the explicit `1.0.4` version tag; the user accepted tag-only pinning when registry digest metadata was unavailable. Do not reuse the old RustFS 1.0.0 digest.
- The new runtime keeps authoritative files in `.runtime/credentials/` with owner-only file/directory permissions. Runtime-readable copies for non-root images are staged under `.runtime/container-mounts/`, protected by a `0700` host directory and mounted read-only; the dedicated service-readable files use mode `0644`. The user approved removing existing credential/secret files in this project copy’s `.runtime/credentials/` and creating only those required by the new runtime. Preserve other `.runtime/` files, all Docker volumes, and all RustFS objects. Never print secret contents.
- The operator interface is `scripts/lakehouse.sh start|status|stop`; startup creates missing protected files without overwriting newly established secrets, waits for individual provider readiness up to 600 seconds by default, and stops without volume deletion.
- Polaris schema creation is an explicit idempotent one-shot prerequisite after Polaris PostgreSQL readiness. It creates only `polaris_schema`; no realm, catalog, namespace, user, role, bucket, or table is created by U1 provider startup.
- Maintain one Keycloak URL configuration boundary for later U2 resolution. Do not hard-code a split host/container issuer assumption in this unit.
- No tests are added or run during Code Generation. No code-quality tooling or application builds are run unless required by an explicitly approved later gate.

## Sequential generation steps

### Step 1 — Replace the default Compose runtime

- [x] Rewrite root `docker-compose.yml` to include only the five core services and explicitly invoked Polaris schema initializer.
- [x] Add the `lakehouse-local` project name, one private `core` network, loopback-only configurable host publications, health checks, readiness dependencies, `restart: on-failure:3` where appropriate, and new project-scoped volumes.
- [x] Pin approved image versions and record the image compatibility matrix. Immutable digests are used where resolved for Keycloak, Polaris, and PostgreSQL; the user explicitly accepted a version tag for RustFS 1.0.4. Build and Test will verify the selected registry images and record the RustFS digest/platform actually pulled.
- [x] Configure Keycloak with PostgreSQL, production `start` mode, local HTTP on the private/loopback boundary, and health support. No FreeIPA state is imported and `start-dev` is not used.
- [x] Configure Polaris relational JDBC persistence using its protected read-only properties file and its independent PostgreSQL database.
- [x] Add an idempotent schema initializer invoked explicitly by `scripts/lakehouse.sh start`; it waits for the Polaris DB and creates `polaris_schema` only.
- [x] Configure RustFS 1.0.4 with `RUSTFS_ACCESS_KEY_FILE` and `RUSTFS_SECRET_KEY_FILE`, persistent data volume, and loopback S3/console bindings.
- [x] Remove all legacy provider and default deferred-service declarations from the primary Compose file.

### Step 2 — Isolate deferred integrations

- [x] Create `docker-compose.deferred.yml` as an inventory-only boundary for Airflow, JupyterHub, Jenkins, and StarRocks. Inspection showed their existing definitions still depend on retired services/configuration; declaring them as runnable would present known-broken integrations as an opt-in deployment. They remain explicitly unsupported pending migration.
- [x] Keep the deferred inventory out of `scripts/lakehouse.sh` and default startup. Clearly mark the integrations unsupported pending migration.
- [x] Remove the old FreeIPA/Hive/Kerberos dependencies from supported startup; no unsupported replacement behavior is claimed.
- [x] Ensure no active Compose file declares FreeIPA, Hive Metastore/schema initialization, or KDC. Old experimental Compose files were removed.

### Step 3 — Add protected local configuration and one-shot schema setup

- [x] Add only non-secret source configuration and SQL needed by the approved provider setup; generated secret-bearing configs are created locally.
- [x] Generate missing runtime credentials atomically under `.runtime/credentials/` with owner-only permissions; do not log values or overwrite credentials after they are generated.
- [x] Inspect the approved credential directory scope: `.runtime/` is absent in this copy, so there were no existing credential files to remove. The generator creates only the required new files on first `start`.
- [x] Use file-backed secret delivery: PostgreSQL `POSTGRES_PASSWORD_FILE`, RustFS `_FILE` credentials, and read-only Keycloak/Polaris config files for database passwords.
- [x] Keep Polaris schema setup separate from its later Admin Tool realm/catalog bootstrap.

### Step 4 — Replace operator startup/status/stop behavior

- [x] Add `scripts/lakehouse.sh start`, `status`, and `stop`; remove the keytab requirement from supported default startup.
- [x] `start` validates Compose V2 and required local tools, ensures required protected files exist, starts only the primary Compose project, runs the schema initializer after DB readiness, and coordinates per-service readiness for at most 600 seconds by default.
- [x] `status` reports each provider and dependency state without printing secret contents.
- [x] `stop` stops the core services without deleting any volume or object.
- [x] Preserve healthy independent providers on dependency failure; no unhealthy-container restart watchdog was added.
- [x] Configure process-exit restart attempts to no more than three and return actionable redacted errors after exhaustion/timeout.

### Step 5 — Remove active legacy configuration and update operator documentation

- [x] Remove or rewrite active startup/configuration references that require FreeIPA, Hive, MIT Kerberos/KDC, or keytabs for the new default runtime. Preserve immutable AI-DLC archives and unrelated history. After explicit user approval, remove exactly `infra/freeipa`, `infra/hive`, and `infra/kerberos`; leave all other legacy directories untouched.
- [x] Update `README.md` with the core/deferred startup boundary, local endpoints, generated credential file paths (names only), status/stop behavior, persistence/backup notes, and the explicit absence of migration/data deletion.
- [x] Document deferred services as unsupported pending migration; do not claim Airflow/JupyterHub/Jenkins/StarRocks work with Keycloak/Polaris.
- [x] Document the Polaris `polaris_schema` prerequisite and keep catalog/product bootstrap for later units.

### Step 6 — Code summary and scope review

- [x] Add `aidlc-docs/current/construction/unit-1/code/code-summary.md` listing changed paths, decisions, design traceability, non-actions, and Build and Test gates.
- [x] Confirm by source inspection that default Compose contains five providers plus the non-default schema helper, and deferred inventory is not used by default startup.
- [x] At Code Generation completion, confirm no secret values were added to source files or output and no tests, containers, image builds, volumes, or object data were touched. Subsequent Build and Test activity is recorded separately.
- [x] Update this plan, execution plan, audit, and AI-DLC state as steps complete.

## Build and Test handoff

The following remain for Build and Test: Compose config validation; verify the immutable Keycloak, Polaris, and PostgreSQL references and record the RustFS 1.0.4 tag's resolved digest/platform; service startup/readiness and 600-second timeout behavior; loopback binding inspection; PostgreSQL persistence; Polaris schema initialization and readiness; RustFS health and persistence; secret-file permissions and redacted diagnostics; stop/recreate persistence; and confirmation that primary Compose has no active FreeIPA/Hive/Kerberos dependencies. U2–U4 verify identity/catalog authorization, buckets/policies, Spark interoperability, and the complete data-product journey.

## Approval gate

User approval was recorded on 2026-10-28. Implementation was authorized. On 2026-10-28 the user accepted the RustFS 1.0.4 version-pinned tag without a digest; Build and Test will verify and record the resolved image.

**Status:** APPROVED by the user on 2026-10-28 (“approved and continue”). Code generation is complete subject to Build and Test verification. The default runtime and operator path have been rewritten. The deferred integration boundary is implemented as inventory-only because legacy definitions are not runnable without migration. The user explicitly approved removal of `infra/freeipa`, `infra/hive`, and `infra/kerberos`; other legacy directories remain untouched. RustFS uses the user-accepted `1.0.4` version tag without immutable digest pinning.
