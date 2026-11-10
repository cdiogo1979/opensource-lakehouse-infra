# Unit 1 Infrastructure Design Plan — Runtime Composition and Legacy Removal

## Unit context

U1 replaces the current mixed-purpose Compose stack with the runtime foundation for the new Keycloak + Polaris + RustFS journey. The current root `docker-compose.yml` starts or declares FreeIPA, KDC, Hive schema initialization and metastore, a Kerberos-based Spark service, JupyterHub, Airflow, Jenkins, StarRocks, and workload services. Its `scripts/start.sh` also requires a writer keytab and starts Hive/Kerberos services. The new default journey instead requires Keycloak and its supported persistent database, Polaris with dedicated PostgreSQL metadata, and RustFS. Bootstrap CLI and Spark run on demand in U4.

Approved design constraints already settle the local Docker Compose deployment, one private core network, loopback-only host publications, named persistent state, protected file-backed secrets, service-scoped health/readiness, a 10-minute readiness deadline, at most three process-exit retries, offline backup/restore guidance, and a separately invoked exact-name legacy-volume cleanup workflow. These are not reopened here.

Infrastructure Design will specify concrete Compose services/profiles, host port defaults, volume ownership, secret files, health checks, startup commands, pinned compatible images, and the treatment of deferred integrations. No service, volume, or object data is modified during this planning stage.

## Planning checklist

### Analyze current infrastructure and approved designs

- [x] Review the approved U1 Functional Design and NFR Design artifacts.
- [x] Review U1 NFR Requirements and approved Application Design boundaries.
- [x] Inspect the current Compose service graph, startup script, networks, volumes, and secret declarations.
- [x] Confirm messaging/queues are not applicable: the approved journey has no asynchronous broker or queue.
- [x] Confirm a separate monitoring stack is not required; Compose health checks and readiness reporting are sufficient.

### Plan approval gate

- [x] Collect and review Infrastructure Design answers; Questions 1–4 and 6–9 are clear and consistent with approved designs.
- [x] Resolve the secret-directory/removal ambiguity in Question 5 before approval.
- [ ] Obtain explicit approval of this plan before generating Infrastructure Design artifacts.

### Generate Infrastructure Design artifacts after plan approval

- [ ] Generate `aidlc-docs/current/construction/unit-1/infrastructure-design/infrastructure-design.md`.
- [ ] Generate `deployment-architecture.md` with the Compose service graph, profiles, networks, ports, volumes, and startup order.
- [ ] Validate pinned versions and interoperability using official component documentation.
- [ ] Identify exact legacy volume names through read-only inspection before describing cleanup; do not delete volumes in design.
- [ ] Present both artifacts for explicit Infrastructure Design approval.

## Infrastructure Design questions

Replace each `[Answer]:` with a selected option or a concrete alternative.

### Question 1 — Host platform support

The deployment target is local Docker Compose on one developer machine. Which host platforms should the infrastructure support?

A) Docker Compose V2 on Docker Desktop for macOS as the primary target, while keeping configuration portable to Linux Docker Engine where possible (Recommended based on this workspace and avoids unnecessary host-specific assumptions).

B) macOS Docker Desktop only; optimize the configuration for the developer’s Mac.

C) macOS, Linux, and Windows Docker Desktop are all required acceptance targets.

X) Other (specify host OS, CPU architecture, and Docker runtime).

[Answer]:A

### Question 2 — Default Compose file and deferred integrations

The current root Compose file mixes the new journey with deferred services and legacy dependencies. How should the Compose files be organized?

A) Keep the primary `docker-compose.yml` limited to the supported core runtime. Put Airflow, JupyterHub, Jenkins, and StarRocks declarations in a separate opt-in overlay; do not declare FreeIPA, Hive Metastore, or KDC in either active Compose file. Clearly mark deferred services unsupported until separately migrated (Recommended: default startup cannot pull in retired services by profile dependencies).

B) Keep all services in the primary file but place deferred integrations behind Compose profiles; remove their FreeIPA/Hive/Kerberos dependencies.

C) Remove deferred service declarations from Compose entirely and retain only their source/configuration directories for a later migration.

X) Other (describe Compose file and profile boundaries).

[Answer]:A

### Question 3 — Keycloak and Polaris database topology

Both identity and catalog metadata need persistence, and Polaris metadata must be isolated. How should PostgreSQL be deployed?

A) Use separate PostgreSQL services, databases, credentials, and named volumes for Keycloak and Polaris (Recommended: strongest service isolation and straightforward ownership, at the cost of another small local container).

B) Use one PostgreSQL service with separate databases, users, and logical backup/restore procedures for Keycloak and Polaris (less container overhead, shared process and failure boundary).

C) Other (specify database engine, service layout, and isolation boundary).

[Answer]:A

### Question 4 — Host-published endpoints

The host CLI and browser-based platform-admin flow need to reach selected provider endpoints. Which ports should be published?

A) Publish only the Keycloak endpoint, Polaris API, RustFS S3 API, and RustFS console on `127.0.0.1`, with configurable host-port overrides; keep all PostgreSQL ports unpublished (Recommended: supports local admin and CLI while preserving the private service boundary).

B) Publish only Keycloak and RustFS endpoints; run the CLI/bootstrap inside the Compose network so Polaris and PostgreSQL remain unpublished.

C) Publish all provider APIs on loopback, including PostgreSQL, for local debugging.

X) Other (list required host endpoints and port preferences).

[Answer]:A

### Question 5 — Local secret directory and delivery

The current `.gitignore` excludes `.runtime/`, and the old project used `.runtime/credentials/`. Which on-disk convention should the new runtime use?

A) Reuse `.runtime/credentials/`, enforce owner-only directory/file permissions, generate missing secrets without overwriting existing values, and mount file-backed Compose secrets read-only where supported (Recommended: familiar path and preserves the approved secret-handling pattern).

B) Use a new `.runtime/secrets/` directory with the same permissions and read-only delivery behavior.

C) Store credentials in an external secret manager and avoid local secret files.

X) Other (specify path, permissions, and generation behavior).

[Answer]: X , and remove all existing ones

Question 5 was clarified by Question 10. The selected convention is `.runtime/credentials/`; only existing secret/credential files in this project copy’s `.runtime/credentials/` are in scope for removal before generating files required by the new stack. Docker volumes and RustFS objects remain preserved. No files have been removed during planning.

### Question 10 — Clarify secret path and removal scope

For the new Keycloak/Polaris/RustFS runtime, where should newly generated local secret files live, and what does “remove all existing ones” refer to? This question concerns files in this `opensource-lakehouse-infra-v2` project copy only. It does not authorize deleting Docker volumes or RustFS objects.

A) Use `.runtime/credentials/`; remove existing credential/secret files in this project copy’s `.runtime/credentials/` before generating only the files required by the new stack. Preserve every Docker volume and object (Recommended if “all existing ones” means prior local secret files).

B) Use `.runtime/secrets/`; remove existing credential/secret files in this project copy’s `.runtime/` before generating only the files required by the new stack. Preserve every Docker volume and object.

C) Keep secrets in an external manager; do not generate local secret files. Specify the manager and delivery mechanism.

X) Other (specify the new secret path and exactly which existing files are in scope).

[Answer]: A — use `.runtime/credentials/`; remove only existing credential/secret files in this project copy’s `.runtime/credentials/` before generating only files required by the new stack. Preserve Docker volumes and RustFS objects.

### Question 6 — Image version and digest policy

The current Compose file pins RustFS by digest but has no Keycloak or Polaris image selection yet. How should versions be chosen?

A) Select mutually compatible stable releases from official images/documentation, pin explicit versions and immutable digests where available, and record the compatibility matrix; retain the current RustFS digest only if it passes compatibility/security review (Recommended: provides reproducibility without assuming the old pin is still suitable).

B) Preserve the existing RustFS digest without reevaluation and choose pinned versions for only the newly added services.

C) Use floating stable tags and update them during regular rebuilds.

X) Other (provide version/digest policy).

[Answer]:A

### Question 7 — Operator startup and status interface

The existing `scripts/start.sh` requires Kerberos credentials and starts the legacy stack. What should replace it for this journey?

A) Replace it with core `start`, `status`, and `stop` commands: create missing protected secret files, start only the default core providers, wait with per-service status for up to 10 minutes, and stop without deleting volumes (Recommended: one safe operator path matching the readiness design).

B) Remove wrapper scripts and document direct `docker compose` commands; readiness is checked with `docker compose ps` and logs.

C) Other (specify commands and whether startup should provision secret files).

[Answer]:A

### Question 8 — RustFS object-store volume for the new project

The current Compose file uses the project-scoped `object-store-data` volume. The new intent creates fresh buckets and does not migrate data; approved rules still prohibit deleting RustFS state. How should the new Compose project use RustFS persistence?

A) Use a new project-scoped RustFS named volume for the new journey and leave any existing RustFS volume untouched and unmounted; create only the new buckets in the new store (Recommended for a clean no-migration bootstrap while preserving old data).

B) Reuse the current RustFS volume after identifying its exact name; preserve all objects and create/validate only the required buckets.

C) Other (specify which existing volume is used and what data must remain accessible).

[Answer]:A

### Question 9 — Compose project and resource naming

The current file hard-codes several `container_name` values beginning with `iceberg-poc`, while volumes and networks use a mix of explicit and project-derived names. What naming strategy should the new stack use?

A) Set a stable Compose project name `lakehouse-local`, remove fixed `container_name` values, and let Compose prefix new network and volume names (Recommended: avoids collisions and gives predictable ownership for the cleanup allowlist).

B) Keep the existing `iceberg-poc` project/network naming to reuse current resources where names match.

C) Use the directory-derived Compose project name and leave resource names implicit.

X) Other (specify the project and resource naming scheme).

[Answer]:A

## Category applicability

| Category | U1 applicability and treatment |
|---|---|
| Deployment environment | Local Docker Compose is approved. Question 1 clarifies host OS and CPU portability. |
| Compute infrastructure | Local containers only; single workload and no fixed resource caps are approved. Questions 2, 3, and 7 refine provider topology and operation. |
| Storage infrastructure | Persistent stores and RustFS are required; no migration or automatic deletion is allowed. Questions 3, 5, and 8 refine storage topology and paths. |
| Messaging infrastructure | Not applicable: no broker, queue, or event-driven component appears in the approved runtime. |
| Networking infrastructure | One private core network and loopback-only host publication are approved. Question 4 identifies the host-reachable endpoints. |
| Monitoring infrastructure | Separate monitoring is not required. Compose health checks/readiness and redacted runtime diagnostics are approved. Question 7 selects the operator interface. |
| Shared infrastructure | One isolated Compose project; services and volumes are not shared with another project. Questions 2 and 9 define deferred-service and resource ownership boundaries. |

## Gate

All ten answers are complete and reviewed. The clarified secret convention uses `.runtime/credentials/` and scopes any removal to secret/credential files in this project copy’s `.runtime/credentials/`; Docker volumes and RustFS objects are preserved. The current Compose and startup configuration is legacy context only; no secret files, running containers, volumes, RustFS objects, or application configuration have been changed during planning.
